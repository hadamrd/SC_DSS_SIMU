
from . import Shared
import math

class CDC(Shared):
    def __init__(self) -> None:
        super().__init__()
        self.target_stock = {p: [self.target_stock["cdc"]] * self.horizon for p in self.products}
        self.dept = {a: {p: [None] * self.horizon for p in self.affiliate_products[a]} for a in self.affiliate_name}
        self.initial_stock = {p: [None] * self.horizon for p in self.products}
        self.projected_stock = {p: [None] * self.horizon for p in self.products}
        self.product_supply = {p: [None] * self.horizon for p in self.products}
        self.capacity = {p: [None] * self.horizon for p in self.products}
        self.raw_demand = {a: {p: [None] * self.horizon for p in self.affiliate_products[a]} for a in self.affiliate_name}
        self.supply = {a: {p: [None] * self.horizon for p in self.affiliate_products[a]} for a in self.affiliate_name}
        self.prod_demand = {p: [None] * self.horizon for p in self.products}
        self.reception = {p: [None] * self.horizon for p in self.products}
    
    def dipatchSupply(self, capacity, raw_demand, a, p, t):
        if raw_demand[a][p][t] < 0:
            return 0
        tot_raw_demand = sum([raw_demand[a][p][t] for a in self.itProductAff(p) if raw_demand[a][p][t] > 0])
        if capacity[p][t] < tot_raw_demand:
            return math.floor(capacity[p][t] * raw_demand[a][p][t] / tot_raw_demand)
        else:
            return raw_demand[a][p][t]
    
    def getProdDemand(self, prev_production, product_demand):
        bp = {p: [0] * self.horizon for p in self.products}
        for p in self.products:
            proj_stock = self.initial_stock[p]
            for t in range(self.horizon):
                pip = prev_production[p][t] if t < self.prod_time else 0
                bp[p][t] = max(0, product_demand[p][t] + self.target_stock[p][t] - proj_stock - pip)
                proj_stock += bp[p][t] + pip - product_demand[p][t]
        return bp

    def run(self, prev_supply, demand, reception):
        # calculate supply plan
        for p in self.products:
            proj_stock = self.initial_stock[p]
            for t in range(self.horizon):
                self.capacity[p][t] = proj_stock + reception[p][t]
                for a in self.itProductAff(p):
                    self.raw_demand[a][p][t] = demand[a][p][t] + (self.dept[a][p][t-1] if t>0 else 0)
                for a in self.itProductAff(p):    
                    if t < self.fixed_horizon:
                        self.supply[a][p][t] = self.dipatchSupply(self.capacity, prev_supply, a, p, t)
                    else:
                        self.supply[a][p][t] = self.dipatchSupply(self.capacity, self.raw_demand, a, p, t)
                    if self.supply[a][p][t] < 0:
                        raise Exception("negative supply impossible", "t: ", t,  "capacity: ", self.capacity[p][t], "reception: ", reception[p][t], "proj_stock: ", proj_stock)
                    self.dept[a][p][t] = self.raw_demand[a][p][t] - self.supply[a][p][t]
                self.product_supply[p][t] = sum([self.supply[a][p][t] for a in self.itProductAff(p)])
                if self.capacity[p][t] < self.product_supply[p][t]:
                    raise Exception("Can't supply more than available capacity", "capacity: ", self.capacity[p][t], self.product_supply[p][t])
                proj_stock = self.capacity[p][t] - self.product_supply[p][t]
        return self.supply, self.product_supply, self.dept
                    