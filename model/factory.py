import math

class Factory:
    def __init__(self, model) -> None:
        self.model = model
        self.packaging_load = [sum([model.prev_prod_plan[p][t] for p in model.products]) for t in range(model.horizon)] 
        self.capacity = model.factory_capacity
        self.prod_plan = {p: [0] * model.horizon for p in model.products}
        self.unavailability = {p: [0] * model.horizon for p in model.products}
        self.prev_prod_plan = {p: model.prev_prod_plan[p][model.prod_time:] + [0] * model.prod_time for p in model.products}
    
    def getProdDemand(self):
        return {p: self.model.cbn_cdc.prod_demand[p][self.model.prod_time:] + [0] * self.model.prod_time for p in self.model.products}
    
    def run(self):
        self.prod_demand = self.getProdDemand()
        fh = self.model.fixed_horizon
        h = self.model.horizon 

        for p in self.model.products:
            self.prod_plan[p][:fh] = self.prev_prod_plan[p][:fh]
            self.unavailability[p][0] = self.prod_demand[p][0] - self.prod_plan[p][0]

            for t in range(1, fh):
                self.unavailability[p][t] = self.unavailability[p][t-1] + self.prod_demand[p][t] - self.prod_plan[p][t]

            for t in range(fh, h):
                raw_need = max(self.prod_demand[p][t] + self.unavailability[p][t-1], 0)
                total_raw_need = sum([self.prod_demand[p][t] + self.unavailability[p][t-1] for p in self.model.products])

                if total_raw_need > self.capacity[t]:
                    demand_ratio = raw_need / total_raw_need
                    quantity_to_produce = demand_ratio * self.capacity[t]
                    self.prod_plan[p][t] = max(min(quantity_to_produce, raw_need), 0)

                else:
                    self.prod_plan[p][t] = raw_need

                self.prod_plan[p][t] = math.floor(self.prod_plan[p][t])
                self.unavailability[p][t] = self.unavailability[p][t-1] + self.prod_demand[p][t] - self.prod_plan[p][t]
            
