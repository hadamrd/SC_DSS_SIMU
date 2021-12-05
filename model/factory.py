import math
from . import Shared

class Factory(Shared):
    def __init__(self) -> None:
        super().__init__()
        self.factory_capacity: list[int] = self.settings["factory_capacity"]
        self.production = {p: [0] * self.horizon for p in self.products}
        self.dept = {p: [0] * self.horizon for p in self.products}
        self.raw_demand = {p: [0] * self.horizon for p in self.products}
    
    def dispatchProduction(self, raw_demand, p, t):
        if raw_demand[p][t] < 0:
            return 0
        tot_raw_demand = sum([raw_demand[p][t] for p in self.products if raw_demand[p][t] > 0])
        if tot_raw_demand > self.factory_capacity[t]:
            return round(self.factory_capacity[t] * raw_demand[p][t] / tot_raw_demand)
        else:
            return raw_demand[p][t]

    def run(self, demand, prev_production):
        for t in range(self.horizon):
            for p in self.products:
                self.raw_demand[p][t] = demand[p][t] + (self.dept[p][t-1] if t>0 else 0)
            for p in self.products:
                if t < self.fixed_horizon:
                    self.production[p][t] = prev_production[p][t]
                else:
                    self.production[p][t] = self.dispatchProduction(self.raw_demand, p, t)
                self.dept[p][t] = self.raw_demand[p][t] - self.production[p][t]
        return self.production

