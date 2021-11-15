from model import Model

class CBN_CDC:
    def __init__(self, model: Model) -> None:
        self.model = model
        self.initial_stock = model.initial_stocks["cdc"]
        self.projected_stock = {p: [None] * model.horizon for p in model.products}
        self.target_stock = {p: [model.target_stock["cdc"]] * model.horizon for p in model.products}
        self.prod_demand = {p: [None] * model.horizon for p in model.products}
        self.queued_prod = {p: model.prev_prod_plan[p][:2] + [0] * (model.horizon - 2) for p in model.products}
        self.prev_prod_plan = {p: [0, 0] + model.prev_prod_plan[p][2:] for p in model.products}
    
    def run(self):
        self.supply_demand = {a: {
            p: aff.supply_demand[p][aff.delivery_time:] + [0] * aff.delivery_time for p in aff.products
        } for a, aff in self.model.affiliates.items()}
        self.total_supply_demand = {p: [sum([self.supply_demand[a.name][p][t] for a in self.model.affiliates.values() if p in a.products]) 
                                for t in range(self.model.horizon)
                                ] for p in self.model.products}
        for p in self.model.products:
            for t in range(self.model.horizon):
                prev_proj_stock = self.initial_stock[p] if t == 0 else self.projected_stock[p][t-1]
                self.prod_demand[p][t] = max(self.prev_prod_plan[p][t], self.total_supply_demand[p][t] + self.target_stock[p][t] - prev_proj_stock - self.queued_prod[p][t])
                self.projected_stock[p][t] = prev_proj_stock + self.prod_demand[p][t] + self.queued_prod[p][t] - self.total_supply_demand[p][t]                                     
     