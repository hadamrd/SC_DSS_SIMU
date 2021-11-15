import json
import math
import sales_forcast_generator
import initial_data_generator
import supply_plan_excel_loader

def runModel(input_file, load_supply_plan_from_excel=False):
    global inputs
    with open(input_file) as json_file:
        inputs = json.load(json_file)
    week = inputs["week"]
    output_file = f"simu_outputs/output_S{week}.json"
    next_input_file = f"simu_inputs/input_S{week+1}.json"
    
    affiliates = [Affiliate(name) for name in inputs["affiliates"]]
    cbn_cdc = CBN_CDC(affiliates)
    factory = Factory(cbn_cdc)
    pa_cdc = PA_CDC(factory, cbn_cdc, affiliates)
    
    if load_supply_plan_from_excel:
        pa_cdc.calculate_pa = False
        supply_plan_excel_file = f"simu_inputs/supply_plan_S{week}"
        platform_supply_plan = supply_plan_excel_loader.run(supply_plan_excel_file, inputs["horizon"])
        inputs["prev_supply_plan"] = platform_supply_plan
        pa_cdc.supply_plan = platform_supply_plan
        
    for affiliate in affiliates:
        affiliate.run()
        
    cbn_cdc.run()
    factory.run()
    pa_cdc.run()
    
    outputs = {
        "supply_plan": pa_cdc.getNextSupplyPlan(),
        "prod_plan": factory.getNextProdPlan(),
        "supply_demand": {a.name: a.supply_demand for a in affiliates},
        "prod_demand": cbn_cdc.prod_demand
    }
    
    sales_forcast = sales_forcast_generator.run(inputs["sales_forcast"], inputs["horizon"])
    
    with open(output_file, 'w') as fp:
        json.dump(outputs, fp)
    
    initial_data_generator.run(week=week+1,
                               sales_forcast=sales_forcast,
                               prev_prod_plan=outputs["prod_plan"],
                               prev_supply_plan=outputs["supply_plan"],
                               initial_stocks=pa_cdc.getNextInitialStock(),
                               file_name=next_input_file)

class Affiliate:
    def __init__(self, name) -> None:
        self.name = name
        self.products = inputs["sales_forcast"][self.name].keys()
        self.delivery_time = inputs["delivery_time"][self.name]
        self.initial_stock = {p: inputs["initial_stocks"][self.name][p] for p in self.products}
        self.sales_forcast = {p: inputs["sales_forcast"][self.name][p] for p in self.products}
        self.target_stock = {p: [inputs["target_stock"][self.name]] * inputs["horizon"] for p in self.products}
        self.projected_stock = {p: [None for _ in range(inputs["horizon"])]  for p in self.products}
        self.supply_demand = {p: [None for _ in range(inputs["horizon"])] for p in self.products}
        self.work_in_progress = {p: inputs["prev_supply_plan"][self.name][p][:self.delivery_time] +\
                                 [0 for _ in range(inputs["horizon"]-self.delivery_time)] for p in self.products}
        
    def run(self):
        for p in self.products:
            for t in range(inputs["horizon"]):
                if t == 0:
                    curr_stock_proj = self.initial_stock[p]
                else:
                    curr_stock_proj = self.projected_stock[p][t-1]
                self.supply_demand[p][t] = max(0, self.sales_forcast[p][t] + self.target_stock[p][t] - self.work_in_progress[p][t] - curr_stock_proj)
                self.projected_stock[p][t] = curr_stock_proj + self.work_in_progress[p][t] + self.supply_demand[p][t] - self.sales_forcast[p][t]

class CBN_CDC:
    def __init__(self, affiliates_obj: list[Affiliate]) -> None:
        self.affiliates = affiliates_obj
        self.initial_stock = inputs["initial_stocks"]["cdc"]
        self.stock_projection = {p: [None for _ in range(inputs["horizon"])] for p in inputs["products"]}
        self.target_stock = {p: [30000 for _ in range(inputs["horizon"])] for p in inputs["products"]}
        self.prod_demand = {p: [None for _ in range(inputs["horizon"])] for p in inputs["products"]}
        self.queued_prod = {p: inputs["prev_prod_plan"][p][:2] + [0 for _ in range(inputs["horizon"]-2)] for p in inputs["products"]}
        self.pdps = {p: [0, 0] + inputs["prev_prod_plan"][p][2:] for p in inputs["products"]}
    
    def run(self):
        self.supply_demand = {p: [sum([a.supply_demand[p][t + a.delivery_time] if t + a.delivery_time < inputs["horizon"] else 0
                                for a in self.affiliates if p in a.supply_demand]) 
                                for t in range(inputs["horizon"])]
                                for p in inputs["products"]}
        for p, pdp in self.pdps.items():
            for t in range(inputs["horizon"]):
                curr_proj_stock = self.initial_stock[p] if t == 0 else self.stock_projection[p][t-1]
                self.prod_demand[p][t] = max(pdp[t], self.supply_demand[p][t] + self.target_stock[p][t] - curr_proj_stock - self.queued_prod[p][t])
                self.stock_projection[p][t] = curr_proj_stock + self.prod_demand[p][t] + self.queued_prod[p][t] - self.supply_demand[p][t]                                     
     
class Factory:
    def __init__(self, cbn_cdc: CBN_CDC) -> None:
        self.cbn_cdc = cbn_cdc 
        self.packaging_load = [sum([inputs["prev_prod_plan"][p][t] for p in inputs["products"]]) for t in range(inputs["horizon"])] 
        self.packaging_capacity = inputs["factory_capacity"]
        self.prod_plan = {p: [0 for _ in range(inputs["horizon"]) ] for p in inputs["products"]}
        self.unavailability = {p: [0 for _ in range(inputs["horizon"])] for p in inputs["products"]}
        self.prod_time = 2
        
    def run(self):
        self.total_net_demand = [sum([self.cbn_cdc.prod_demand[p][t + self.prod_time] if t + self.prod_time < inputs["horizon"] else 0 for p in inputs["products"]]) for t in range(inputs["horizon"])]
        for p in inputs["products"]:
            self.prod_plan[p][0] = inputs["prev_prod_plan"][p][0 + self.prod_time]
            self.prod_plan[p][1] = inputs["prev_prod_plan"][p][1 + self.prod_time]
            self.unavailability[p][0] = self.cbn_cdc.prod_demand[p][0 + self.prod_time] -  self.prod_plan[p][0]
            self.unavailability[p][1] = self.unavailability[p][0] + self.cbn_cdc.prod_demand[p][1 + self.prod_time] -  self.prod_plan[p][1]

            for t in range(2, inputs["horizon"] - self.prod_time):
                raw_need = self.cbn_cdc.prod_demand[p][t + self.prod_time] + self.unavailability[p][t-1]
                if self.total_net_demand[t] > self.packaging_capacity[t]:
                    demand_ratio = self.cbn_cdc.prod_demand[p][t] / self.total_net_demand[t]
                    quantity_to_produce = demand_ratio * self.packaging_capacity[t]
                    self.prod_plan[p][t] = min(quantity_to_produce, max(raw_need, inputs["prev_prod_plan"][p][t + self.prod_time]))
                else:
                    self.prod_plan[p][t] = max(raw_need, inputs["prev_prod_plan"][p][t + self.prod_time])
                self.prod_plan[p][t] = math.floor(self.prod_plan[p][t])
                self.unavailability[p][t] = self.unavailability[p][t-1] + self.cbn_cdc.prod_demand[p][t + self.prod_time] -  self.prod_plan[p][t]

    def getNextProdPlan(self):
        prod_plan = {}
        for p in inputs["products"]:
            prod_plan[p] = inputs["prev_prod_plan"][p][1:self.prod_time+1] +\
                self.prod_plan[p][1:inputs["horizon"]-self.prod_time]
            prod_plan[p].append(prod_plan[p][-1])
        return prod_plan

class PA_CDC:
    def __init__(self, factory: Factory, cbn_cdc: CBN_CDC, affiliates_obj: list[Affiliate]) -> None:
        self.factory = factory
        self.cbn_cdc = cbn_cdc
        self.affiliates = {a.name: a for a in affiliates_obj}
        self.raw_need = {p: [None for _ in range(inputs["horizon"])] for p in inputs["products"]}
        self.unavailability = {a: {p: [0 for _ in range(inputs["horizon"])] for p in inputs["products"]} for a in inputs["affiliates"]}
        self.possible_to_promise = {p: [None for _ in range(inputs["horizon"])] for p in inputs["products"]}
        self.initial_stock = self.cbn_cdc.initial_stock
        self.projected_stock = {p: [None for _ in range(inputs["horizon"])] for p in inputs["products"]}
        self.supply_plan = {a: {p: [0 for _ in range(inputs["horizon"])] for p in aff.products} for a, aff in self.affiliates.items()}
        self.calculate_pa = True
        if inputs["week"] % 4 == 1:
            self.prod_plan = self.factory.prod_plan
        else:
            self.prod_plan = inputs["prev_prod_plan"] 
        
    def run(self):
        prod_t = self.factory.prod_time
        self.supply_demand = self.cbn_cdc.supply_demand
        total_prev_supply_plan = {p: [sum([inputs["prev_supply_plan"][a][p][t+aff.delivery_time] 
            if t+aff.delivery_time < inputs["horizon"] else 0
            for a, aff in self.affiliates.items() if p in aff.products])
                for t in range(inputs["horizon"])]
                    for p in inputs["products"]}
        
        for a in inputs["affiliates"]:
            affiliate =  self.affiliates[a]
            for p in affiliate.products:
                if self.calculate_pa:
                    self.supply_plan[a][p][0] = inputs["prev_supply_plan"][a][p][0 + affiliate.delivery_time]
                    self.supply_plan[a][p][1] = inputs["prev_supply_plan"][a][p][1 + affiliate.delivery_time]
                self.unavailability[a][p][0] = affiliate.supply_demand[p][0 + affiliate.delivery_time] - self.supply_plan[a][p][0]
        
        for p in inputs["products"]:
            self.raw_need[p][0] = self.supply_demand[p][0]
            self.possible_to_promise[p][0] = total_prev_supply_plan[p][0]
            total_supply_plan = sum([self.supply_plan[a][p][0] if p in aff.products else 0 for a, aff in self.affiliates.items()])
            self.projected_stock[p][0] = self.initial_stock[p] + self.cbn_cdc.queued_prod[p][0] - total_supply_plan

        for t in range(1, inputs["horizon"]):
            for p in inputs["products"]:
                total_unavailability = sum([self.unavailability[a][p][t-1] if p in self.affiliates[a].products else 0 for a in inputs["affiliates"]])
                self.raw_need[p][t] = self.supply_demand[p][t] + total_unavailability
                
            for p in inputs["products"]:
                planed_prod = self.prod_plan[p][t - prod_t] if t >= prod_t else 0
                total_supply_plan = sum([self.supply_plan[a][p][t] if p in aff.products else 0 for a, aff in self.affiliates.items()])
                self.projected_stock[p][t] = self.projected_stock[p][t-1] + planed_prod + self.cbn_cdc.queued_prod[p][t] - total_supply_plan
                if t < 2:
                    self.possible_to_promise[p][t] = total_prev_supply_plan[p][t]
                else:
                    self.possible_to_promise[p][t] = max(min(self.raw_need[p][t], planed_prod + self.cbn_cdc.queued_prod[p][t] + self.projected_stock[p][t-1]), 0)
            
            for a in inputs["affiliates"]:
                affiliate =  self.affiliates[a]
                for p in affiliate.products:
                    if t + affiliate.delivery_time < inputs["horizon"]:
                        aff_supply_demand = affiliate.supply_demand[p][t + affiliate.delivery_time]
                    else:
                        aff_supply_demand = 0
                    if self.calculate_pa and t >= 2:
                        if self.raw_need[p][t] > 0:
                            supply_ratio = (aff_supply_demand + self.unavailability[a][p][t-1]) / self.raw_need[p][t]
                            self.supply_plan[a][p][t] = max(round(supply_ratio * self.possible_to_promise[p][t]), 0)
                        else: 
                            self.supply_plan[a][p][t] = 0
                    self.unavailability[a][p][t] = self.unavailability[a][p][t-1] + aff_supply_demand - self.supply_plan[a][p][t] 
    
    def getNextInitialStock(self):
        ans = {}
        for a, aff in self.affiliates.items():
            ans[a] = {
                p: aff.initial_stock[p] + aff.work_in_progress[p][0] + (self.supply_plan[a][p][0] if aff.delivery_time==0 else 0) - aff.sales_forcast[p][0] 
                for p in aff.products
            } 
        ans["cdc"] = {p: self.projected_stock[p][0] for p in inputs["products"]}
        return ans

    def getNextSupplyPlan(self):
        supply_plan = {}
        for a, aff in self.affiliates.items():
            supply_plan[a] = {}
            for p in aff.products:
                supply_plan[aff.name][p] = inputs["prev_supply_plan"][aff.name][p][1:aff.delivery_time+1] +\
                    self.supply_plan[aff.name][p][1:inputs["horizon"]-aff.delivery_time]
                supply_plan[aff.name][p].append(supply_plan[aff.name][p][-1])
        return supply_plan
