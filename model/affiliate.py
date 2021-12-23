from os import name
from . import Shared
import logging
class Affiliate(Shared):
    
    def __init__(self, name) -> None:
        super().__init__()
        self.name = name
        self.products = self.itAffProducts(name)
        self.initial_stock = self.getEmptyProductQ()
        self.delivery_time = self.getAffDeliveryTime(name)
        self.target_stock = {p: [self.getAffTargetStock(name)] * self.horizon for p in self.products}
        
    def getDemand(self, sales_forcast, prev_supply):
        self.demand = self.getEmptyProductQ()
        for p in self.products:
            stock_proj = self.initial_stock[p]
            for t in range(self.horizon):
                imminent_supply = prev_supply[p][t] if t < self.delivery_time else 0
                # self.demand[p][t] = max(0, sales_forcast[p][t] + self.target_stock[p][t] - imminent_supply - stock_proj)
                self.demand[p][t] = sales_forcast[p][t]
                # logging.debug(f"t: {t}, p: {p}, sales: {sales_forcast[p][t]}, imminent: {imminent_supply}, stock_proj: {stock_proj} ==> BA = {self.demand[p][t]}")
                # stock_proj = stock_proj + imminent_supply + self.demand[p][t] - sales_forcast[p][t]
                # if stock_proj < 0:
                #     raise Exception("can't have negative stock")
        return self.demand
