class Affiliate:
    def __init__(self, name: str, model) -> None:
        self.name = name
        self.model = model
        self.products = model.sales_forcast[self.name].keys()
        self.delivery_time = model.delivery_time[self.name]
        self.initial_stock = {p: model.initial_stock[self.name][p] for p in self.products}
        self.sales_forcast = {p: model.sales_forcast[self.name][p] for p in self.products}
        self.target_stock = {p: [model.target_stock[self.name]] * model.horizon for p in self.products}
        self.projected_stock = {p: [None for _ in range(model.horizon)]  for p in self.products}
        self.supply_demand = {p: [None for _ in range(model.horizon)] for p in self.products}
        self.imminent_supply = {p: model.prev_supply_plan[self.name][p][:self.delivery_time] +\
                                 [0] * (model.horizon-self.delivery_time) for p in self.products}
        
    def run(self):
        for p in self.products:
            for t in range(self.model.horizon):
                prev_stock_proj = self.initial_stock[p] if t == 0 else self.projected_stock[p][t-1]
                self.supply_demand[p][t] = max(0, self.sales_forcast[p][t] + self.target_stock[p][t] - self.imminent_supply[p][t] - prev_stock_proj)
                self.projected_stock[p][t] = prev_stock_proj + self.imminent_supply[p][t] + self.supply_demand[p][t] - self.sales_forcast[p][t]
