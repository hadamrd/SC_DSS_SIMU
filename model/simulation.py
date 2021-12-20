import json
import os
import sys
from . import RiskManager
from . import Shared
from . import utils
from . import Model, History
from .filter import SmoothingFilter
import copy
import time
import logging 


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

    def getInitInput(self, ini_sales, r_model):
        logging.debug("Generating initial input ...")
        stock_ini = {a: {p: self.settings["affiliate"][a]["initial_stock"][p] for p in self.itAffProducts(a)} for a in self.itAffiliates()}
        stock_ini["cdc"] = {p: self.settings["cdc"]["initial_stock"][p] for p in self.products}
        r0 = sum([self.getAffPvRange(a) for a in self.itAffiliates()])
        crecep_ini = {}
        cqpm = {param: [0 for _ in range(self.real_horizon)] for param in ["a", "b", "c", "d"]}
        for p in self.products:
            logging.debug(f"Generating initial reception(pdp) for product {p}")
            crecep_ini_ = utils.genRandCQ(self.horizon, r0)
            crecep_ini[p] = utils.genRandCQFromUCM(cqpm, r_model[p], crecep_ini_, 0)
            crecep_ini[p] += (self.horizon-self.real_horizon)*[crecep_ini[p][self.real_horizon-1]]
            utils.validateCQ(crecep_ini[p])

        recep_ini = {p: utils.diff(crecep_ini[p]) for p in self.products}
        
        prev_supply = {a: 
            {p: [0] * int(aff["delivery_time"]) + ini_sales[a][p][int(aff["delivery_time"]):] for p in self.itAffProducts(a)}     
            for a, aff in self.settings["affiliate"].items()
        }

        input = {
            "prev_production": recep_ini,
            "crecep_ini": crecep_ini,
            "prev_supply": prev_supply,
            "initial_stock": stock_ini,
            "week": 0,
        }
        return input
    
    def flushLogs(self):
        for p in self.products:
            log_f: str = os.path.join(self.history_folder, f"log_{p}.log")
            if os.path.exists(log_f):
                open(log_f.format(p), 'w').close()
    
    def log_state(self, k, dpm, rpm, cppv, cproduct_supply, cproduct_supply_out, cpdemand, creception, cpdemande_ref, creception_ref, prev_cpsupplly):      
        n = self.real_horizon          
        nchars = 16 + 7 * n
        format_row = "{:>16}" + "{:>7}" * n
        original_stdout = sys.stdout # Save a reference to the original standard output
        product_dept = self.sumOverAffiliate(self.model.cdc_dept)
        for p in self.products:
            log_f: str = os.path.join(self.history_folder, f"log_{p}.log")
            with open(log_f.format(p), 'a') as fp:
                sys.stdout = fp
                print("*" * nchars)
                print("Week :", k, ", Product: ", p, ", Cumulated Plans", "\n")
                print("Initial stock: ", self.model.cdc.initial_stock[p])
                print(format_row.format("week", *[f"W{t}" for t in range(k, k + n)]))
                print("-" * nchars)
                print(format_row.format("sales", *cppv[p][:n]))
                print(format_row.format("demand", *cpdemand[p][:n]))
                print(format_row.format("prev x", *prev_cpsupplly[p][:n]))
                print(format_row.format("demand ref", *cpdemande_ref[p][k:k+n]))
                print("-" * nchars)
                print(format_row.format("reception", *creception[p][:n]))
                print(format_row.format("reception ref", *creception_ref[p][k:k+n]))
                print(format_row.format("dept", *product_dept[p][:n]))
                print("-" * nchars)
                print(format_row.format("A demand ref", *dpm[p]["a"][:n]))
                print(format_row.format("B demand ref", *dpm[p]["b"][:n]))
                print(format_row.format("X in", *cproduct_supply[p][:n]))
                print(format_row.format("X out", *cproduct_supply_out[p][:n]))
                print(format_row.format("C reception ref", *rpm[p]["c"][:n]))
                print(format_row.format("D reception ref", *rpm[p]["d"][:n]))
                print("=" * nchars)
                print(format_row.format("NL4 in", *[round(_, 2) for _ in self.risk_manager.getL4Necessity(rpm[p], dpm[p], cproduct_supply[p][:n])]))
                print(format_row.format("NL4 out", *[round(_, 2) for _ in self.risk_manager.getL4Necessity(rpm[p], dpm[p], cproduct_supply_out[p][:n])]))
        sys.stdout = original_stdout

    def generateHistory(self, start_week: int, end_week: int, ini_input, smoothing_filter: SmoothingFilter=None):
        nweeks = end_week - start_week + 1
        self.flushLogs()

        # Init plans
        cppv = self.getEmptyProductQ(value=0)
        creception = self.getEmptyProductQ(value=0)
        cpdemand = self.getEmptyProductQ(value=0)
        creception_ref = self.getEmptyProductQ(value=0, size=self.horizon + nweeks)
        cdemand_ref = self.getEmptyAffQ(value=0, size=self.horizon + nweeks)
        cpsupply = self.getEmptyProductQ(value=0)
        prev_cpsupplly = self.getEmptyProductQ(value=0)

        self.model.loadWeekInput(input_dict=ini_input)
        aff_demand = self.model.getAffiliatesDemand(self.sales_history[0], ini_input["prev_supply"], 0)
        demand_ini = self.model.getCDCDemand(aff_demand)
        ppv = self.sumOverAffiliate(self.sales_history[0])
        for p in self.products:
            for a in self.itProductAff(p):
                cdemand_ref[a][p][:self.horizon] = list(utils.accumu(demand_ini[a][p]))
            creception_ref[p][:self.horizon] = ini_input["crecep_ini"][p]
            
        rpm = {p: {param: [0 for _ in range(self.real_horizon)] for param in ["a", "b", "c", "d"]} for p in self.products}
        dpm = {a: {p: {param: [0 for _ in range(self.real_horizon)] for param in ["a", "b", "c", "d"]} for p in self.itAffProducts(a)} for a in self.itAffiliates()}
        cpr = {p: 0 for p in self.products}
        
        # start main loop
        for w in range(start_week, end_week + 1):
            print(".", end="", flush=True)
            k = w - start_week
            next_input_f = os.path.join(self.inputs_folder, f"input_S{k+1}.json")
            # snapshot_f = os.path.join(self.history_folder, f"snapshot_S{k}.json")

            self.model.loadWeekInput(input_dict=ini_input)
            self.model.runWeek(self.sales_history[k])
            
            # get model cdc outputs
            reception = self.model.cdc_reception
            demand = self.model.cdc_demand
            pdemand = self.model.cdc_product_demand
            ppv = self.model.getCDCProductSalesForcast()            
            supply = self.model.cdc_supply
            product_supply = self.model.cdc_product_supply
            stock_ini = self.model.cdc.initial_stock
            prev_supply = self.model.getCDCPrevSupply()
            prev_psupply = self.sumOverAffiliate(prev_supply)
            
            # get outputs cumulated plans
            cpr = {p: cpsupply[p][0] for p in self.products }
            prev_cpsupplly = {p: list(utils.accumu(prev_psupply[p], cpr[p])) for p in self.products}
            cpsupply = {p: list(utils.accumu(product_supply[p], cpr[p])) for p in self.products}
            cpdemand = {p: list(utils.accumu(pdemand[p], cpdemand[p][0])) for p in self.products}
            creception = {p: list(utils.accumu(reception[p], creception[p][0])) for p in self.products}
            cppv = {p: list(utils.accumu(ppv[p], cppv[p][0])) for p in self.products}
            for p in self.products:
                for a in self.itProductAff(p):
                    cdemand_ref[a][p][k+self.horizon] = cdemand_ref[a][p][k+self.horizon-1] + demand[a][p][self.horizon-1] 
                creception_ref[p][k+self.horizon] = creception_ref[p][k+self.horizon-1] + reception[p][self.horizon-1]
            
            # calculate distributions
            dpm, rpm = self.risk_manager.getDitributions(dpm, rpm, cdemand_ref, creception_ref, stock_ini, k)
            pdpm = {p: {param: [sum([dpm[a][p][param][t] for a in self.itProductAff(p)]) for t in range(self.real_horizon)] for param in ['a', 'b', 'c', 'd']} for p in self.products}

            # Create data snapshot
            snapshot = self.model.getSnapShot()
            snapshot["cproduct_supply"] = cpsupply
            snapshot["demand"] = demand
            snapshot["reception"] = reception
            snapshot["supply"] = supply

            # gather metrics
            snapshot["metrics"]["in"] = self.risk_manager.getRiskMetrics(pdpm, rpm, cpsupply)
            n = self.real_horizon
            cpsupply_out = self.getEmptyProductQ(0)
            
            # In case there is a filter apply it
            if smoothing_filter:
                cpsupply_out = {p: smoothing_filter.smooth(rpm[p], pdpm[p], cpsupply[p][:n]) for p in self.products}
                psupply_out = {p: utils.diff(cpsupply_out[p], cpr[p]) + product_supply[p][n:] for p in self.products}
                cpsupply_out = {p: cpsupply_out[p] + list(utils.accumu(product_supply[p][n:], cpsupply_out[p][n-1])) for p in self.products}
                supply_out = self.dispatch(psupply_out, demand, supply)
                self.model.setCDCSupply(supply_out, psupply_out)
                snapshot["cproduct_supply"] = cpsupply_out
                snapshot["product_supply"] = psupply_out
                snapshot["supply"] = supply_out
                snapshot["metrics"]["out"] = self.risk_manager.getRiskMetrics(pdpm, rpm, cpsupply_out)
                
            cpdemande_ref = self.sumOverAffiliate(cdemand_ref, horizon=self.horizon + nweeks)
                
            # log simulation state 
            self.log_state(k, pdpm, rpm, cppv, cpsupply, cpsupply_out, cpdemand, creception, cpdemande_ref, creception_ref, prev_cpsupplly)

            # utils.saveToFile(snapshot, snapshot_f)

            # add data to history 
            self.sim_history.fillData(snapshot)

            # generate next week inputs
            ini_input = self.model.generateNextWeekInput(next_input_f)

    def run(self, sales_history, start_week, end_week, ini_input, pa_filter=None):
        self.history_folder  = f"{self.name}/history"
        self.inputs_folder   = f"{self.name}/inputs"
        self.results_folder  = f"{self.name}/results"
        self.sales_history   = sales_history
        self.sim_history.init(start_week, end_week, pa_filter)

        if not os.path.exists(self.name):
            os.mkdir(self.name)
        if not os.path.exists(self.history_folder):
            os.mkdir(self.history_folder)
        if not os.path.exists(self.inputs_folder):
            os.mkdir(self.inputs_folder)

        st = time.perf_counter()
        print("Generating simu history", end=" ", flush=True)
        self.generateHistory(
            start_week,
            end_week,
            ini_input,
            smoothing_filter=pa_filter
        )
        print("Finished in :", time.perf_counter() - st)

        st = time.perf_counter()
        print("Exporting history to excel files", end=" ", flush=True)
        self.sim_history.exportToExcel(
            prefix=Simulation.count,
            results_folder=self.results_folder
        )
        print(" Finished in :", time.perf_counter() - st)

        Simulation.count += 1