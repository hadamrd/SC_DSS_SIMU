import json
import sales_forcast_generator
import model_data_generator
import supply_plan_excel_loader
from affiliate import Affiliate
from pa_cdc import PA_CDC
from factory import Factory
from cbn_cdc import CBN_CDC

class Model:
    def __init__(self, input_file) -> None:
        with open(input_file) as json_file:
            inputs = json.load(json_file)
            
        self.week = inputs["week"]
        self.horizon = inputs["horizon"]
        self.products = inputs["products"]
        self.prod_time = inputs["prod_time"]
        self.delivery_time = inputs["delivery_time"]
        self.target_stock = inputs["target_stock"]
        self.factory_capacity = inputs["factory_capacity"]
        self.initial_stocks = inputs["initial_stocks"]
        self.prev_prod_plan = inputs["prev_prod_plan"]
        self.sales_forcast = inputs["sales_forcast"]
        self.prev_supply_plan = inputs["prev_supply_plan"]
        
        self.affiliates = {name: Affiliate(name, self) for name in inputs["affiliates"]}
        self.cbn_cdc = CBN_CDC(self)
        self.factory = Factory(self)
        self.pa_cdc = PA_CDC(self)
        self.outputs = None
    
    def getSupplyDemand(self):
        return {name: a.supply_demand for name, a in self.affiliates.items()}
    
    def getInitialStock(self):
        intial_stock = {}
        for a, aff in self.affiliates.items():
            intial_stock[a] = {
                p: aff.initial_stock[p] + aff.imminent_supply[p][0] + (self.pa_cdc.supply_plan[a][p][0] if aff.delivery_time==0 else 0)\
                    - aff.sales_forcast[p][0] 
                for p in aff.products
            } 
        intial_stock["cdc"] = {p: self.pa_cdc.projected_stock[p][0] for p in self.products}
        return intial_stock

    def getSupplyPlan(self):
        supply_plan = {}
        for a, aff in self.affiliates.items():
            supply_plan[a] = {}
            for p in aff.products:
                supply_plan[a][p] = self.prev_supply_plan[a][p][1:aff.delivery_time+1] + self.pa_cdc.supply_plan[a][p][1:self.horizon-aff.delivery_time]
                supply_plan[a][p].append(supply_plan[a][p][-1])
        return supply_plan
    
    def getProdPlan(self):
        prod_plan = {}
        for p in self.products:
            prod_plan[p] = self.factory.prev_prod_plan[p][1:self.prod_time + 1] +\
                self.factory.prod_plan[p][1:self.horizon - self.prod_time]
            prod_plan[p].append(prod_plan[p][-1])
        return prod_plan
    
    def getProdDemand(self):
        return self.cbn_cdc.prod_demand
    
    def generateSalesForcast(self):
        return sales_forcast_generator.run(self.sales_forcast, self.horizon)
    
    def loadSupplyPlanFromExcel(self):
        self.pa_cdc.calculate_pa = False
        supply_plan_excel_file = f"simu_inputs/supply_plan_S{self.week}"
        platform_supply_plan = supply_plan_excel_loader.run(supply_plan_excel_file, self.horizon)
        self.prev_supply_plan = platform_supply_plan
        self.pa_cdc.supply_plan = platform_supply_plan
    
    def generateNextInput(self, file_path):
        if not file_path:
            file_path = f"simu_inputs/input_S{self.week+1}.json"
        model_data_generator.run(week=self.week+1,
                                sales_forcast=self.generateSalesForcast(),
                                prev_prod_plan=self.getProdPlan(),
                                prev_supply_plan=self.getSupplyPlan(),
                                initial_stocks=self.getInitialStock(),
                                file_name=file_path)
    
    def saveOutput(self, file_path):
        if not file_path:
            file_path = f"simu_outputs/output_S{self.week}.json"
        with open(file_path, 'w') as fp:
            json.dump(self.outputs, fp)

    def generatePlatformInput(self):
        pass
    
    def run(self):
        for affiliate in self.affiliates.values():
            affiliate.run()
        self.cbn_cdc.run()
        self.factory.run()
        self.pa_cdc.run()
        self.outputs = {
            "supply_plan": self.getSupplyPlan(),
            "prod_plan": self.getProdPlan(),
            "supply_demand": self.getSupplyDemand(),
            "prod_demand": self.getProdDemand()
         }

