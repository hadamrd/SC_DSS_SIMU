import json
import os

from . import RiskManager
from . import Shared
from . import utils
from . import Model, History
from .filter import SmoothingFilter


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

    def generateHistory(self, start_week: int, end_week: int, smoothing_filter: SmoothingFilter=None):
        with open(os.path.join(self.inputs_folder, f"input_S{start_week}.json")) as fp:
            input = json.load(fp)

        for k in range(start_week, end_week + 1):
            next_input_f = os.path.join(self.inputs_folder, f"input_S{k+1}.json")

            # snapshot_f = os.path.join(self.history_folder, f"snapshot_S{k}.json")
            sales_f = os.path.join(self.sales_folder, f"sales_S{k}.json")
            self.model.loadWeekInput(input_dict=input)
            self.model.loadSalesForcast(sales_f)
            self.model.runWeek()
            
            # get model cdc outputs
            reception = self.model.getCDCReception()
            demand = self.model.getCDCSupplyDemand()
            pa_aff = self.model.getCDCAffSupplyPlan()
            pa_product = self.model.getCDCProductSupplyPlan()
            initial_stock = self.model.getCDCInitialStock()

            # calculate ref plans
            if k == start_week:
                reception_ref = reception
                demand_ref = demand
            else:
                for p in self.products:
                    reception_ref[p] = reception_ref[p][1:] + [reception[p][self.horizon-1]]
                for a, p in self.itParams():
                    demand_ref[a][p] = demand_ref[a][p][1:] + [demand[a][p][self.horizon-1]]
            
            # calculate distributions and metrics
            dpm, rpm = self.risk_manager.getDitributions(demand, reception, demand_ref, reception_ref, initial_stock)
            cpa_product   = {p: list(utils.accumu(pa_product[p])) for p in self.products}
            snapshot = self.model.getSnapShot()
            snapshot["cpa_product"] = cpa_product
            snapshot["reception"] = reception
            snapshot["metrics"]["in"] = self.risk_manager.getRiskMetrics(dpm, rpm, cpa_product)
            n = self.real_horizon
            fh = self.fixed_horizon

            # In case their is a filter to apply
            if smoothing_filter:
                cpa_product_out    = {p: smoothing_filter.smooth(rpm[p], dpm[p], cpa_product[p][:n]) + cpa_product[p][n:] for p in self.products}
                pa_product_out     = {p: utils.diff(cpa_product_out[p]) for p in self.products}
                pa_aff_out         = self.dispatch(pa_product_out, demand, pa_aff)
                self.model.setCDCSupplyPlan(pa_aff_out, pa_product_out)
                snapshot["cpa_product"] = cpa_product_out
                snapshot["pa_product"]  = pa_product_out
                snapshot["pa_aff"]      = pa_aff_out
                snapshot["metrics"]["out"] = self.risk_manager.getRiskMetrics(dpm, rpm, cpa_product_out)

                # print distributions
                for p in self.products:
                    print("*********************************************************************")
                    print("Week :", k, ", Product: ", p)
                    print("Demand: ")
                    print("A demand: ", [round(_) for _ in dpm[p]["a"][fh-1:n]])
                    print("B demand: ", [round(_) for _ in dpm[p]["b"][fh-1:n]])
                    print("X  in   : ", cpa_product[p][:n])
                    print("Unavail : ", [sum([self.model.pa_cdc.unavailability[a][p][t] for a in self.itProductAff(p)]) for t in range(fh-1, n)])
                    print("C recept: ", [round(_) for _ in rpm[p]["c"][fh-1:n]])
                    print("D recept: ", [round(_) for _ in rpm[p]["d"][fh-1:n]])
                    print("---------------------------------------------------------------------")
                    print("NL4 in  : ", self.risk_manager.getL4Necessity(rpm[p], dpm[p], cpa_product[p][:n])[fh-1:])
                    print("NL4 out : ", self.risk_manager.getL4Necessity(rpm[p], dpm[p], cpa_product_out[p][:n])[fh-1:])
                    print("X out   : ", cpa_product_out[p][fh-1:n])

            # utils.saveToFile(snapshot, snapshot_f)
            self.sim_history.fillData(snapshot)
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