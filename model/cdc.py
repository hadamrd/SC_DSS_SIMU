
from . import Shared

class CDC(Shared):
    
    def __init__(self) -> None:
        super().__init__()
        self.target_stock = {p: [self.settings["cdc"]["target_stock"]] * self.horizon for p in self.products}
        self.dept = self.getEmptyAffQ(None)
        self.initial_stock = None
        self.projected_stock = self.getEmptyProductQ(None)
        self.product_supply = self.getEmptyProductQ(None)
        self.capacity = self.getEmptyProductQ(None)
        self.raw_demand = self.getEmptyAffQ(None)
        self.supply = self.getEmptyAffQ(None)
        self.prod_demand = self.getEmptyProductQ(None)
        self.reception = self.getEmptyProductQ(None)
    
    def getProdDemand(self, prev_production, product_demand):
        self.bp = self.getEmptyProductQ(0)
        for p in self.products:
            proj_stock = self.initial_stock[p]
            for t in range(self.horizon):
                imminent_production = prev_production[p][t] if t < self.prod_time else 0
                self.bp[p][t] = max(0, product_demand[p][t] + self.target_stock[p][t] - proj_stock - imminent_production)
                proj_stock += self.bp[p][t] + imminent_production - product_demand[p][t]
        return self.bp

    def getAffSupply(self, prev_supply, demand, reception):
        for p in self.products:
            for t in range(self.horizon):
                self.capacity[p][t] = (self.projected_stock[p][t-1] if t>0 else self.initial_stock[p]) + reception[p][t]
                for a in self.itProductAff(p):
                    self.raw_demand[a][p][t] = demand[a][p][t] + (self.dept[a][p][t-1] if t>0 else 0)
                for a in self.itProductAff(p):
                    if t < self.fixed_horizon:
                        self.supply[a][p][t] = prev_supply[a][p][t]
                    else:
                        self.supply[a][p][t] = self.dipatchSupply(self.capacity, self.raw_demand, a, p, t)
                    self.dept[a][p][t] = self.raw_demand[a][p][t] - self.supply[a][p][t]
                self.product_supply[p][t] = sum([self.supply[a][p][t] for a in self.itProductAff(p)])
                self.projected_stock[p][t] = self.capacity[p][t] - self.product_supply[p][t]
                # if self.projected_stock[p][t] < 0:
                #     raise Exception("Negative stock impossible")
        return self.supply, self.product_supply, self.dept
