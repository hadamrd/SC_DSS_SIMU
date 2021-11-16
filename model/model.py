import json
import openpyxl
from . import sales_forcast_generator
from . import model_data_generator
from . import supply_plan_excel_loader
from .affiliate import Affiliate
from .pa_cdc import PA_CDC
from .factory import Factory
from .cbn_cdc import CBN_CDC

class Model:
    def __init__(self, input_file) -> None:
        with open(input_file) as json_file:
            inputs = json.load(json_file)
            
        self.week = inputs["week"]
        self.horizon = inputs["horizon"]
        self.products = inputs["products"]
        self.prod_time = inputs["prod_time"]
        self.delivery_time = inputs["delivery_time"]
        self.target_stock = inputs["target_stock"]
        self.factory_capacity = inputs["factory_capacity"]
        self.initial_stock = inputs["initial_stock"]
        self.prev_prod_plan = inputs["prev_prod_plan"]
        self.sales_forcast = inputs["sales_forcast"]
        self.prev_supply_plan = inputs["prev_supply_plan"]
        
        self.affiliates = {name: Affiliate(name, self) for name in inputs["affiliates"]}
        self.cbn_cdc = CBN_CDC(self)
        self.factory = Factory(self)
        self.pa_cdc = PA_CDC(self)
        self.outputs = None
    
    def getSupplyDemand(self):
        return {name: a.supply_demand for name, a in self.affiliates.items()}
    
    def getNextInitialStock(self):
        initial_stock = {}
        for a, aff in self.affiliates.items():
            initial_stock[a] = {
                p: aff.initial_stock[p] + aff.imminent_supply[p][0] + (self.pa_cdc.supply_plan[a][p][0] if aff.delivery_time==0 else 0)\
                    - aff.sales_forcast[p][0] 
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
                next_supply_plan[a][p] = self.prev_supply_plan[a][p][1:aff.delivery_time+1] + self.supply_plan[a][p][1:self.horizon-aff.delivery_time]
                next_supply_plan[a][p].append(next_supply_plan[a][p][-1])
        return next_supply_plan
    
    def nextSupplyPlanFromPrev(self):
        next_supply_plan = {}
        for a, aff in self.affiliates.items():
            next_supply_plan[a] = {}
            for p in aff.products:
                next_supply_plan[a][p] = self.prev_supply_plan[a][p][1:aff.delivery_time+1] + self.prev_supply_plan[a][p][1:self.horizon-aff.delivery_time]
                next_supply_plan[a][p].append(next_supply_plan[a][p][-1])
        return next_supply_plan
    
    def getNextProdPlan(self):
        prod_plan = {}
        for p in self.products:
            prod_plan[p] = self.factory.prev_prod_plan[p][1:self.prod_time + 1] +\
                self.factory.prod_plan[p][1:self.horizon - self.prod_time]
            prod_plan[p].append(prod_plan[p][-1])
        return prod_plan
    
    def getProdDemand(self):
        return self.cbn_cdc.prod_demand
    
    def generateSalesForcast(self):
        return sales_forcast_generator.run(self.sales_forcast, self.horizon)
    
    def loadSupplyPlanFromExcel(self, file_path):
        self.calculate_supply_plan = False
        platform_supply_plan = supply_plan_excel_loader.run(file_path, self.horizon)
        self.supply_plan = platform_supply_plan
    
    def generateNextInput(self, file_path):
        model_data_generator.run(week=self.week+1,
                                sales_forcast=self.generateSalesForcast(),
                                prev_prod_plan=self.getNextProdPlan(),
                                prev_supply_plan=self.getNextSupplyPlan(),
                                initial_stock=self.getNextInitialStock(),
                                file_name=file_path)

    def generateCDCToAffiliateInput(self, file_path):
        wb = openpyxl.load_workbook("templates/template_platform_input.xlsx")
        sheet = wb.active
        sheet.cell(2, 2).value = f"W{self.week}/20"
        cdc_prod_plan = self.pa_cdc.getProdPlan()
        ohs_offset = 0
        # header week before
        sheet.cell(4, 8).value = f"W{self.week-1}/20"
        for t in range(self.horizon):
            # header weeks in horizon
            sheet.cell(4, 9 + t).value = f"W{self.week+t}/20"
        for p in self.products:
            product_block_start_row = 5 + ohs_offset
            # stock onhand 
            sheet.cell(product_block_start_row + 1, 8).value = self.cbn_cdc.initial_stock[p]
            for t in range(self.horizon):
                # programmed_reception Factory -> CDC (pdp + queued)
                sheet.cell(product_block_start_row, 9 + t).value = cdc_prod_plan[p][t] + self.cbn_cdc.queued_prod[p][t]
                j = 0
                for a in self.affiliates.values():
                    if p in a.products:
                        # BA Affiliate -> CDC
                        sheet.cell(product_block_start_row + 2 + j * 2, 9 + t).value = self.cbn_cdc.supply_demand[a.name][p][t]
                        # PA CDC -> affiliate 
                        sheet.cell(product_block_start_row + 2 + j * 2 + 1, 9 + t).value = self.prev_supply_plan[a.name][p][t + a.delivery_time] if t + a.delivery_time < self.horizon else 0
                        j += 1
            nbr_ff_p = sum([1 for aff in self.affiliates.values() if p in aff.products])
            ohs_offset += (2 * nbr_ff_p + 3)
            
        wb.save(file_path)
    
    def runAffiliatesToCDC(self):
        for affiliate in self.affiliates.values():
            affiliate.run()
        self.supply_demand = self.getSupplyDemand()
    
    def runCDCToFactory(self):
        self.cbn_cdc.run()
        self.factory.run()

