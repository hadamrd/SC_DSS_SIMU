import json
import os
import sys
from . import RiskManager
from . import Shared
from . import utils
from . import Model, History
from .filter import SmoothingFilter
import copy


class Simulation(Shared):
    count = 1
    def __init__(self, name) -> None:
        super().__init__()
        self.model           = Model()
        self.sim_history     = History()
        self.risk_manager    = RiskManager()
        self.name            = name    
        self.history_folder  = None
        self.inputs_folder   = None
        self.results_folder  = None
        self.metric_result_f = None
        self.sales_folder    = None

    def flushLogs(self):
        for p in self.products:
            log_f: str = os.path.join(self.history_folder, f"log_{p}.log")
            if os.path.exists(log_f):
                open(log_f.format(p), 'w').close()
    
    def log_state(self, k, dpm, rpm, cproduct_supply, cproduct_supply_out, cdemand, creception, cdemande_ref, creception_ref):      
        n = self.real_horizon          
        nchars = 16 + 7 * n
        format_row = "{:>16}" + "{:>7}" * n
        original_stdout = sys.stdout # Save a reference to the original standard output
        product_sales_forcast = self.model.getProductSalesForcast()
        cproduct_demand = self.sumOverAffiliate(cdemand)
        product_dept = self.sumOverAffiliate(self.model.cdc_dept)
        capacity = self.model.cdc.capacity
        cproduct_demande_ref = self.sumOverAffiliate(cdemande_ref)
        for p in self.products:
            log_f: str = os.path.join(self.history_folder, f"log_{p}.log")
            with open(log_f.format(p), 'a') as fp:
                sys.stdout = fp
                print("*" * nchars)
                print("Week :", k, ", Product: ", p, ", Cumulated Plans", "\n")
                print("Initial stock: ", self.model.cdc.initial_stock[p])
                print(format_row.format("week", *[f"W{t}" for t in range(k, k + n)]))
                print("-" * nchars)
                print(format_row.format("sales", *list(utils.accumu(product_sales_forcast[p]))[:n]))
                print(format_row.format("demand", *cproduct_demand[p][:n]))
                print(format_row.format("demand ref", *cproduct_demande_ref[p][:n]))
                print("-" * nchars)
                print(format_row.format("capacity", *list(utils.accumu(capacity[p]))[:n]))
                print(format_row.format("reception", *creception[p][:n]))
                print(format_row.format("reception ref", *creception_ref[p][:n]))
                print(format_row.format("dept", *product_dept[p][:n]))
                print("-" * nchars)
                print(format_row.format("A demand ref", *dpm[p]["a"][:n]))
                print(format_row.format("B demand ref", *dpm[p]["b"][:n]))
                print(format_row.format("X in", *cproduct_supply[p][:n]))
                print(format_row.format("X out", *cproduct_supply_out[p][:n]))
                print(format_row.format("C reception ref", *rpm[p]["c"][:n]))
                print(format_row.format("D reception ref", *rpm[p]["d"][:n]))
                print("=" * nchars)
                print(format_row.format("NL4 in", *[round(_, 4) for _ in self.risk_manager.getL4Necessity(rpm[p], dpm[p], cproduct_supply[p][:n])[:]]))
                print(format_row.format("NL4 out", *[round(_, 4) for _ in self.risk_manager.getL4Necessity(rpm[p], dpm[p], cproduct_supply_out[p][:n])[:]]))
        sys.stdout = original_stdout

    def generateHistory(self, start_week: int, end_week: int, smoothing_filter: SmoothingFilter=None):
        self.flushLogs()

        with open(os.path.join(self.inputs_folder, f"input_S{start_week}.json")) as fp:
            input = json.load(fp)

        creception = self.getEmptyProductQ(0)
        cdemand = self.getEmptyAffQ(0)
        
        creception_ref = self.getEmptyProductQ(0)
        cdemand_ref = self.getEmptyAffQ(0)
        
        for k in range(start_week, end_week + 1):
            next_input_f = os.path.join(self.inputs_folder, f"input_S{k+1}.json")
            # snapshot_f = os.path.join(self.history_folder, f"snapshot_S{k}.json")

            sales_f = os.path.join(self.sales_folder, f"sales_S{k}.json")
            self.model.loadWeekInput(input_dict=input)
            self.model.loadSalesForcast(sales_f)
            self.model.runWeek()
            
            # get model cdc outputs
            reception = self.model.cdc_reception
            demand = self.model.cdc_demand

            supply = copy.deepcopy(self.model.cdc_supply)
            product_supply = self.model.cdc_product_supply.copy()
            initial_stock = self.model.getCDCInitialStock()

            # calculate ref plans
            if k == start_week:
                reception_ref = reception.copy()
                demand_ref = copy.deepcopy(demand)
            else:
                for p in self.products:
                    reception_ref[p] = reception_ref[p][1:] + [reception[p][self.horizon-1]]
                for a, p in self.itParams():
                    demand_ref[a][p] = demand_ref[a][p][1:] + [demand[a][p][self.horizon-1]]

            cdemand = {a: {p: list(utils.accumu(demand[a][p], cdemand[a][p][0])) for p in  self.affiliate_products[a]} for a in self.affiliate_name}
            creception = {p: list(utils.accumu(reception[p], creception[p][0])) for p in self.products}

            cdemand_ref = {a: {p: list(utils.accumu(demand_ref[a][p], cdemand_ref[a][p][0])) for p in  self.affiliate_products[a]} for a in self.affiliate_name}
            creception_ref = {p: list(utils.accumu(reception[p], creception_ref[p][0])) for p in self.products}

            # calculate distributions and metrics
            dpm, rpm = self.risk_manager.getDitributions(cdemand, creception, cdemand_ref, creception_ref, initial_stock)

            # # cumulate supply plan
            cproduct_supply = {p: list(utils.accumu(product_supply[p])) for p in self.products}
            
            # # Create data snapshot
            snapshot = self.model.getSnapShot()
            snapshot["cproduct_supply"] = cproduct_supply
            snapshot["demand"] = demand
            snapshot["reception"] = reception
            snapshot["supply"] = supply

            # gather metrics
            snapshot["metrics"]["in"] = self.risk_manager.getRiskMetrics(dpm, rpm, cproduct_supply)
            n = self.real_horizon

            # In case there is a filter to apply
            if smoothing_filter:
                cproduct_supply_out = {p: smoothing_filter.smooth(rpm[p], dpm[p], cproduct_supply[p][:n]) for p in self.products}
                product_supply_out = {p: utils.diff(cproduct_supply_out[p]) + product_supply[p][n:] for p in self.products}
                cproduct_supply_out = {p: cproduct_supply_out[p] + list(utils.accumu(product_supply[p][n:], cproduct_supply_out[p][n-1])) for p in self.products}
                supply_out = self.dispatch(product_supply_out, demand, supply)
                self.model.setCDCSupply(supply_out, product_supply_out)
                snapshot["cproduct_supply"] = cproduct_supply_out
                snapshot["product_supply"] = product_supply_out
                snapshot["supply"] = supply_out
                snapshot["metrics"]["out"] = self.risk_manager.getRiskMetrics(dpm, rpm, cproduct_supply_out)

                # log simulation state 
                self.log_state(k, dpm, rpm, cproduct_supply, cproduct_supply_out, cdemand, creception, cdemand_ref, creception_ref)

            # utils.saveToFile(snapshot, snapshot_f)

            # add data to history 
            self.sim_history.fillData(snapshot)

            # generate next week inputs
            input = self.model.generateNextWeekInput(next_input_f)

    def run(self, initial_input_f, start_week, end_week, sales_folder, pa_filter=None):
        self.history_folder  = f"{self.name}/history"
        self.inputs_folder   = f"{self.name}/inputs"
        self.results_folder  = f"{self.name}/results"
        self.sales_folder    = sales_folder
        self.sim_history.init(start_week, end_week, pa_filter)

        if not os.path.exists(self.name):
            os.mkdir(self.name)
        if not os.path.exists(self.history_folder):
            os.mkdir(self.history_folder)
        if not os.path.exists(self.inputs_folder):
            os.mkdir(self.inputs_folder)
            
        utils.replicateFile(initial_input_f, os.path.join(self.inputs_folder, "input_S2.json"))

        print("Generating simu history ... ", end="")
        self.generateHistory(
            start_week,
            end_week,
            smoothing_filter=pa_filter
        )
        print("Finished")

        print("Exporting history to excel files ... ", end="")
        self.sim_history.exportToExcel(
            prefix=Simulation.count,
            results_folder=self.results_folder
        )
        print("Finished")

        Simulation.count += 1