class CBN_CDC:
    def __init__(self, model) -> None:
        self.model = model
        self.initial_stock = model.initial_stock["cdc"]
        self.projected_stock = {p: [None] * model.horizon for p in model.products}
        self.target_stock = {p: [model.target_stock["cdc"]] * model.horizon for p in model.products}
        self.prod_demand = {p: [None] * model.horizon for p in model.products}
    
    def getPrevProdPlan(self):
        return {p: [0] * self.model.prod_time + self.model.prev_prod_plan[p][self.model.prod_time:] for p in self.model.products}
    
    def getQeuedProd(self):
        return {p: self.model.prev_prod_plan[p][:self.model.prod_time] + [0] * (self.model.horizon - self.model.prod_time)
                for p in self.model.products}
    
    def getSupplyDemand(self):
        return {a: {
            p: aff.supply_demand[p][aff.delivery_time:] + [0] * aff.delivery_time for p in aff.products
        } for a, aff in self.model.affiliates.items()}
    
    def getProductsSupplyDemand(self):
        return {p: [sum([self.supply_demand[a.name][p][t] for a in self.model.affiliates.values() if p in a.products]) 
                                for t in range(self.model.horizon)
                                ] for p in self.model.products}
        
    def run(self):
        self.queued_prod = self.getQeuedProd()
        self.prev_prod_plan = self.getPrevProdPlan()
        self.supply_demand = self.getSupplyDemand()
        self.product_supply_demand = self.getProductsSupplyDemand()
        for p in self.model.products:
            for t in range(self.model.horizon):
                prev_proj_stock = self.initial_stock[p] if t == 0 else self.projected_stock[p][t-1]
                self.prod_demand[p][t] = max(self.prev_prod_plan[p][t], self.product_supply_demand[p][t] + self.target_stock[p][t] - prev_proj_stock - self.queued_prod[p][t])
                self.projected_stock[p][t] = prev_proj_stock + self.prod_demand[p][t] + self.queued_prod[p][t] - self.product_supply_demand[p][t]                                     
     