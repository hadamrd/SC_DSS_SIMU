import math
class Factory:
    def __init__(self, model) -> None:
        self.model = model
        self.packaging_load = [sum([model.prev_prod_plan[p][t] for p in model.products]) for t in range(model.horizon)] 
        self.packaging_capacity = model.factory_capacity
        self.prod_plan = {p: [0] * model.horizon for p in model.products}
        self.unavailability = {p: [0] * model.horizon for p in model.products}
        self.prev_prod_plan = {p: model.prev_prod_plan[p][model.prod_time:] + [0] * model.prod_time for p in model.products}
    
    def getProdDemand(self):
        return {p: self.model.cbn_cdc.prod_demand[p][self.model.prod_time:] + [0] * self.model.prod_time for p in self.model.products}
    
    def getTotalNetDemand(self):
        return [sum([self.prod_demand[p][t] for p in self.model.products]) for t in range(self.model.horizon)]
    
    def run(self):
        self.prod_demand = self.getProdDemand()
        self.total_net_demand = self.getTotalNetDemand()
        
        for p in self.model.products:
            self.prod_plan[p][0] = self.prev_prod_plan[p][0]
            self.prod_plan[p][1] = self.prev_prod_plan[p][1]
            self.unavailability[p][0] = self.prod_demand[p][0] - self.prod_plan[p][0]
            self.unavailability[p][1] = self.unavailability[p][0] + self.prod_demand[p][1] - self.prod_plan[p][1]

            for t in range(2, self.model.horizon):
                raw_need = self.prod_demand[p][t] + self.unavailability[p][t - 1]
                if self.total_net_demand[t] > self.packaging_capacity[t]:
                    demand_ratio = self.prod_demand[p][t] / self.total_net_demand[t]
                    quantity_to_produce = demand_ratio * self.packaging_capacity[t]
                    self.prod_plan[p][t] = min(quantity_to_produce, max(raw_need, self.prev_prod_plan[p][t]))
                else:
                    self.prod_plan[p][t] = max(raw_need, self.prev_prod_plan[p][t])
                self.prod_plan[p][t] = math.floor(self.prod_plan[p][t])
                self.unavailability[p][t] = self.unavailability[p][t - 1] + self.prod_demand[p][t] - self.prod_plan[p][t]
            
