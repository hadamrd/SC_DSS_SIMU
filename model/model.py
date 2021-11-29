import json
import openpyxl
from . import Shared, Affiliate, PA_CDC, Factory, CBN_CDC

class Model(Shared):
    def __init__(self) -> None:
        super().__init__()     
        self.week = None
        self.initial_stock = None
        self.prev_prod_plan = None
        self.prev_supply_plan = None
        self.sales_forcast = None
    
    def getCDCReception(self):
        cdc_prod_plan = self.pa_cdc.getProdPlan()
        cdc_queued_prod = self.pa_cdc.getQueuedProd()
        return {p: [cdc_prod_plan[p][t] + cdc_queued_prod[p][t] for t in range(self.horizon)] for p in self.products}

    def loadSalesForcast(self, file_p):
        with open(file_p) as fp:
            self.sales_forcast = json.load(fp)

    def loadWeekInput(self, input_file=None, input_dict=None):
        if input_file:
            with open(input_file) as json_file:
                input_dict = json.load(json_file)
        if input_dict is None:
            raise Exception("No input file or dict given!")
        self.week: int = input_dict["week"]
        self.initial_stock: dict[str: int] = input_dict["initial_stock"]
        self.prev_prod_plan: dict[str, list[int]] = input_dict["prev_prod_plan"]
        self.prev_supply_plan: dict[str, dict[str, list[int]]] = input_dict["prev_supply_plan"]
    
    def getAffiliateSupplyDemand(self):
        return {name: a.supply_demand for name, a in self.affiliates.items()}
    
    def getNextInitialStock(self):
        initial_stock = {}
        for a, aff in self.affiliates.items():
            initial_stock[a] = {
                p: aff.initial_stock[p] + self.prev_supply_plan[a][p][0] +\
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
            prod_plan[p] += [prod_plan[p][-1]]
        return prod_plan
    
    def getCDCProdDemand(self):
        return self.cbn_cdc.prod_demand

    def generateNextWeekInput(self, file_path):
        data = {}
        data["prev_supply_plan"] = self.getNextSupplyPlan()
        data["prev_prod_plan"] = self.getNextProdPlan()
        data["initial_stock"] = self.getNextInitialStock()
        data["week"] = self.week + 1
        with open(file_path, 'w') as fp:
            json.dump(data, fp)
        return data

    def runAffiliatesToCDC(self):
        self.affiliates = {name: Affiliate(name, self) for name in self.affiliate_name}
        for affiliate in self.affiliates.values():
            affiliate.run()
        self.affiliate_supply_demand = self.getAffiliateSupplyDemand()
    
    def runCDCToFactory(self):
        self.cbn_cdc = CBN_CDC(self)
        self.factory = Factory(self)
        self.cbn_cdc.run()
        self.factory.run()
    
    def runCDCToAffiliates(self):
        self.pa_cdc = PA_CDC(self)
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
        state = {
            "pa": pa,
            "reception": reception,
            "demand": demand,
            "initial_stock": initial_stock
        }
        return state

    def saveCurrState(self, file_name):
        with open(file_name, 'w') as fp:
            json.dump(self.getCurrState, fp)

    def saveSnapShot(self, file_name):
        snap = {
            "week": self.week,
            "supply_plan": self.getNextSupplyPlan(),
            "prod_plan": self.getNextProdPlan(),
            "supply_demand": self.getAffiliateSupplyDemand(),
            "prod_demand": self.getCDCProdDemand(),
            "sales_forcast": self.sales_forcast,
            "unavailabiliy": self.pa_cdc.unavailability
        }
        with open(file_name, 'w') as fp:
            json.dump(snap, fp)
        return snap
        
    def saveCDCSupplyPlan(self, file_path):
        with open(file_path, 'w') as fp:
            json.dump(self.cdc_supply_plan, fp)

    def exportDataToExcel(self, dst_f):
        wb = openpyxl.load_workbook("templates/template_platform_input.xlsx")
        sheet = wb.active
        sheet.cell(2, 2).value = f"W{self.week}/20"
        cdc_prod_plan = self.pa_cdc.getProdPlan()
        cdc_supply_demand = self.pa_cdc.getSupplyDemand()
        cdc_queued_prod = self.pa_cdc.getQueuedProd()
        cdc_initial_stock = self.cbn_cdc.initial_stock
        cdc_prev_supply_plan = self.cdc_supply_plan
        offset = 0
        # header week before
        sheet.cell(4, 8).value = f"W{self.week-1}/20"
        for t in range(self.horizon):
            # header weeks
            sheet.cell(4, 9 + t).value = f"W{self.week+t}/20"
        for p in self.products:
            product_block_start_row = 5 + offset
            # stock initial 
            sheet.cell(product_block_start_row + 1, 8).value = cdc_initial_stock[p]
            for t in range(self.horizon):
                # programmed_reception Factory -> CDC (pdp + queued)
                sheet.cell(product_block_start_row, 9 + t).value = cdc_prod_plan[p][t] + cdc_queued_prod[p][t]
                j = 0
                for a in self.affiliates.values():
                    if p in a.products:
                        # BA Affiliate -> CDC
                        sheet.cell(product_block_start_row + 2 + j * 2, 9 + t).value = cdc_supply_demand[a.name][p][t]
                        # PA CDC -> affiliate 
                        sheet.cell(product_block_start_row + 2 + j * 2 + 1, 9 + t).value = cdc_prev_supply_plan[a.name][p][t]
                        j += 1
            nbr_ff_p = sum([1 for aff in self.affiliates.values() if p in aff.products])
            offset += (2 * nbr_ff_p + 3)
        wb.save(dst_f)

    def loadSupplyPlanFromExcel(self, srf_f):
        supply_demand = {}
        wb = openpyxl.load_workbook(srf_f)
        sheet = wb.active
        i = 0
        while sheet.cell(2 + i, 1).value:
            quantity = int(sheet.cell(2 + i, 2).value)
            affiliate = self.affiliate_code[sheet.cell(2 + i, 3).value]
            week = int(sheet.cell(2 + i, 6).value.split("/")[0][1:])
            product = sheet.cell(2 + i, 12).value
            if affiliate not in supply_demand:
                supply_demand[affiliate] = {}
            if product not in supply_demand[affiliate]:
                supply_demand[affiliate][product] = [None for _ in range(self.horizon)]
            supply_demand[affiliate][product][week-self.week] = quantity
            i += 1
        return supply_demand