import math
class PA_CDC:
    def __init__(self, model) -> None:
        self.model = model
        self.raw_need = {p: [None for _ in range(model.horizon)] for p in model.products}
        self.unavailability = {a: {p: [0] * model.horizon for p in model.products} for a in model.affiliates.keys()}
        self.possible_to_promise = {p: [None] * model.horizon for p in model.products}
        self.initial_stock = self.model.cbn_cdc.initial_stock
        self.projected_stock = {p: [None] * model.horizon for p in model.products}
        self.supply_plan = {a: {p: [None] * model.horizon for p in aff.products} for a, aff in model.affiliates.items()}
        self.product_supply_plan = {p: [None] * model.horizon for p in self.model.products}
    
    def getProdPlan(self) -> dict[str, list[int]]:
        if self.model.week % 4 == 1:
            return {p: [0] * self.model.prod_time + self.model.factory.prod_plan[p][:self.model.horizon - self.model.prod_time]\
                for p in self.model.products}
        else:
            return {p: [0] * self.model.prod_time + self.model.prev_prod_plan[p][self.model.prod_time:]\
                for p in self.model.products}
    
    def getPrevSupplyPlan(self) -> dict[str, dict[str, list[int]]]:
        horizon = self.model.horizon
        prev_supply_plan = {}
        for a, aff in self.model.affiliates.items():
            prev_supply_plan[a] = {p: self.model.prev_supply_plan[a][p][aff.delivery_time:] + [0] * (horizon-aff.delivery_time) for p in aff.products}
        return prev_supply_plan

    def getProductSupplyDemand(self) -> dict[str, list[int]]:
        return self.model.cbn_cdc.getProductSupplyDemand()
    
    def getTotalPrevSupplyPlan(self) -> dict[str, list[int]]:
        horizon = self.model.horizon
        return {p: [sum([self.prev_supply_plan[a][p][t] for a, aff in self.model.affiliates.items() if p in aff.products])
                for t in range(horizon)]
                    for p in self.model.products}
    
    def getSupplyDemand(self) -> dict[str, dict[str, list[int]]]:
        return self.model.cbn_cdc.getSupplyDemand()
    
    def getQueuedProd(self) -> dict[str, list[int]]:
        return self.model.cbn_cdc.getQueuedProd()
        
    def run(self):
        affiliates = self.model.affiliates
        self.queued_prod = self.getQueuedProd()
        self.prod_plan = self.getProdPlan()
        self.supply_demand = self.getSupplyDemand()
        self.product_supply_demand = self.getProductSupplyDemand()
        self.prev_supply_plan = self.getPrevSupplyPlan()
        self.total_prev_supply_plan = self.getTotalPrevSupplyPlan()
        self.supply_ratio = {a: {p: [None] * self.model.horizon for p in aff.products} for a, aff in self.model.affiliates.items()}

        for a, aff in affiliates.items():
            for p in aff.products:
                self.supply_plan[a][p][:self.model.fixed_horizon] = self.prev_supply_plan[a][p][:self.model.fixed_horizon]

        for p in self.model.products:
            self.raw_need[p][0] = self.product_supply_demand[p][0]
            self.possible_to_promise[p][0:self.model.fixed_horizon] = self.total_prev_supply_plan[p][0:self.model.fixed_horizon]
            self.product_supply_plan[p][0] = sum([self.supply_plan[a][p][0] for a, aff in affiliates.items() if p in aff.products])
            self.projected_stock[p][0] = self.initial_stock[p] + self.queued_prod[p][0] - self.product_supply_plan[p][0]
            for a, aff in affiliates.items():
                if p in aff.products:
                    self.supply_ratio[a][p][0] = self.supply_demand[a][p][0] / self.raw_need[p][0] if self.raw_need[p][0] != 0 else 0

            for t in range(1, self.model.horizon):
                self.raw_need[p][t] = self.product_supply_demand[p][t] 
                for a, aff in affiliates.items():
                    if p in aff.products: 
                        self.supply_ratio[a][p][t] = self.supply_demand[a][p][t] / self.raw_need[p][t] if self.raw_need[p][t] != 0 else 0

                if t >= self.model.fixed_horizon:
                    projected_available_quantity = self.prod_plan[p][t] + self.queued_prod[p][t] + self.projected_stock[p][t-1]
                    self.possible_to_promise[p][t] = max(min(self.raw_need[p][t], projected_available_quantity), 0)

                for a, aff in affiliates.items(): 
                    if p in aff.products:
                        if t >= self.model.fixed_horizon:
                            self.supply_plan[a][p][t] = max(math.floor(self.supply_ratio[a][p][t] * self.possible_to_promise[p][t]), 0)
                        
                self.product_supply_plan[p][t] = sum([self.supply_plan[a][p][t] for a, aff in affiliates.items() if p in aff.products])
                self.projected_stock[p][t] = self.projected_stock[p][t-1] + self.prod_plan[p][t] + self.queued_prod[p][t] - self.product_supply_plan[p][t]