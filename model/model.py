import json
from .sales import Sales
from .affiliate import Affiliate
from .pa_cdc import PA_CDC
from .factory import Factory
from .cbn_cdc import CBN_CDC
from . import platform_interface 
class Model:
    def __init__(self, input_file) -> None:
        with open(input_file) as json_file:
            inputs = json.load(json_file)
        self.affiliate_name = inputs["affiliates"]
        self.affiliate_code = inputs["affiliate_code"]
        self.horizon = inputs["horizon"]
        self.products = inputs["products"]
        self.prod_time = inputs["prod_time"]
        self.delivery_time = inputs["delivery_time"]
        self.target_stock = inputs["target_stock"]
        self.factory_capacity = inputs["factory_capacity"]
        self.affiliate_product = inputs["affiliate_product"]
        self.affiliate_pv_range = inputs["affiliate_pv_range"]
        self.sales_uncertainty_model_file = inputs["sales_uncertainty_model_file"]
        self.sales_module = Sales(self)
    
    def getCDCReception(self):
        cdc_prod_plan = self.pa_cdc.getProdPlan()
        cdc_queued_prod = self.pa_cdc.getQueuedProd()
        return {p: [cdc_prod_plan[p][t] + cdc_queued_prod[p][t] for t in range(self.horizon)] for p in self.products}
        

    def loadWeekInput(self, input_file):
        with open(input_file) as json_file:
            inputs = json.load(json_file)
        self.week = inputs["week"]
        self.initial_stock = inputs["initial_stock"]
        self.prev_prod_plan = inputs["prev_prod_plan"]
        self.sales_forcast = inputs["sales_forcast"]
        self.prev_supply_plan = inputs["prev_supply_plan"]
        
        self.affiliates = {name: Affiliate(name, self) for name in self.affiliate_name}
        self.cbn_cdc = CBN_CDC(self)
        self.factory = Factory(self)
        self.pa_cdc = PA_CDC(self)
    
    def getAffiliateSupplyDemand(self):
        return {name: a.supply_demand for name, a in self.affiliates.items()}
    
    def getNextInitialStock(self):
        initial_stock = {}
        for a, aff in self.affiliates.items():
            initial_stock[a] = {
                p: aff.initial_stock[p] + aff.imminent_supply[p][0] +\
                    (self.cdc_supply_plan[a][p][0] if aff.delivery_time==0 else 0) - aff.sales_forcast[p][0] 
                for p in aff.products
            } 
        initial_stock["cdc"]= {}
        for p in self.products:
            total_supply_plan = sum([self.prev_supply_plan[a][p][0 + aff.delivery_time] if p in aff.products else 0 for a, aff in self.affiliates.items()])
            initial_stock["cdc"][p] = self.cbn_cdc.initial_stock[p] + self.cbn_cdc.queued_prod[p][0] - total_supply_plan
        return initial_stock

    def getNextSupplyPlan(self):
        next_supply_plan = {}
        for a, aff in self.affiliates.items():
            next_supply_plan[a] = {}
            for p in aff.products:
                next_supply_plan[a][p] = self.prev_supply_plan[a][p][1:aff.delivery_time+1] +\
                    self.cdc_supply_plan[a][p][1:self.horizon-aff.delivery_time] +\
                        [self.cdc_supply_plan[a][p][self.horizon-aff.delivery_time-1]]
        return next_supply_plan

    def getNextProdPlan(self):
        prod_plan = {}
        for p in self.products:
            prod_plan[p] = self.prev_prod_plan[p][1:self.prod_time+1] + self.factory.prod_plan[p][1:self.horizon - self.prod_time]
            prod_plan[p].append(prod_plan[p][-1])
        return prod_plan
    
    def getCDCProdDemand(self):
        return self.cbn_cdc.prod_demand
    
    def generateNextWeekSalesForcast(self):
        return {
            a: {
                p: self.sales_module.genRandSalesForcast(a, self.sales_forcast[a][p]) for p in aff_products
            } for a, aff_products in self.affiliate_product.items()
        }

    def getAffiliateCode(self, aff_name):
        for code, name in self.affiliate_code.items():
            if name == aff_name:
                return code

    def loadPlatformOutput(self, file_path):
        self.cdc_supply_plan = platform_interface.loadSupplyPlan(file_path, self.affiliate_code, self.horizon, self.week)
    
    def generateNextWeekInput(self, file_path):
        data = {}
        data["prev_supply_plan"] = self.getNextSupplyPlan()
        data["prev_prod_plan"] = self.getNextProdPlan()
        data["sales_forcast"] = self.generateNextWeekSalesForcast()
        data["initial_stock"] = self.getNextInitialStock()
        data["week"] = self.week + 1
        with open(file_path, 'w') as fp:
            json.dump(data, fp)

    def runAffiliatesToCDC(self):
        for affiliate in self.affiliates.values():
            affiliate.run()
        self.affiliate_supply_demand = self.getAffiliateSupplyDemand()
    
    def runCDCToFactory(self):
        self.cbn_cdc.run()
        self.factory.run()
    
    def runCDCToAffiliates(self):
        self.pa_cdc.run()
        self.cdc_supply_plan = self.pa_cdc.supply_plan
    
    def runWeek(self):
        self.runAffiliatesToCDC()
        self.runCDCToFactory()
        self.runCDCToAffiliates()

    def getCurrState(self):
        pa = self.pa_cdc.product_supply_plan
        initial_stock = self.pa_cdc.initial_stock
        reception = self.getCDCReception()
        demand = self.pa_cdc.getSupplyDemand()
        snap = {
            "pa": pa,
            "reception": reception,
            "demand": demand,
            "initial_stock": initial_stock
        }
        return snap

    def saveCurrState(self, file_name):
        with open(file_name, 'w') as fp:
            json.dump(self.getCurrState, fp)

    def saveSnapShot(self, file_name):
        snap = {
            "supply_plan": self.getNextSupplyPlan(),
            "prod_plan": self.getNextProdPlan(),
            "supply_demand": self.getAffiliateSupplyDemand(),
            "prod_demand": self.getCDCProdDemand()
        }
        with open(file_name, 'w') as fp:
            json.dump(snap, fp)

    def getPlatformInput(self, file_path):
        platform_interface.generateInput(file_path, self)
        
    def saveCDCSupplyPlan(self, file_path):
        with open(file_path, 'w') as fp:
            json.dump(self.cdc_supply_plan, fp)