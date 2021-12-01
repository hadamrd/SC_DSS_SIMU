import json
import os
from . import metrics
from . import utils
from . import Model, History
from .filter import SmoothingFilter


class Simulation:
    count = 1
    def __init__(self, name) -> None:
        self.model           = Model()
        self.sim_history     = History()
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
            if smoothing_filter:
                pa_in_filter = self.model.pa_cdc.product_supply_plan.copy()
                self.model.cdc_supply_plan = smoothing_filter.run(self.model)
            snapshot = self.model.getSnapShot()
            if smoothing_filter:
                snapshot["pa_in_filter"] = pa_in_filter
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