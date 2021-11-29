import os
from . import metrics
from . import utils
from . import Model, History
from .filter import SmoothingFilter


class Simulation:
    count = 1
    def __init__(self) -> None:
        self.model           = Model()
        self.sim_history     = History()        
        self.history_folder  = None
        self.inputs_folder   = None
        self.results_folder  = None
        self.metric_result_f = None
        self.sales_folder    = None

    def generateHistory(self, start_week: int, end_week: int, smoothing_filter: SmoothingFilter=None):
        for k in range(start_week, end_week + 1):
            input_f = os.path.join(self.inputs_folder, f"input_S{k}.json")
            next_input_f = os.path.join(self.inputs_folder, f"input_S{k+1}.json")
            snapshot_f = os.path.join(self.history_folder, f"snapshot_S{k}.json")
            sales_f = os.path.join(self.sales_folder, f"sales_S{k}.json")
            self.model.loadWeekInput(input_f)
            self.model.loadSalesForcast(sales_f)
            self.model.runWeek()
            if smoothing_filter:
                self.model.cdc_supply_plan = smoothing_filter.run(self.model)
            self.model.saveSnapShot(snapshot_f)
            self.model.generateNextWeekInput(next_input_f)    

    def run(self, initial_input_f, start_week, end_week, sales_folder, output_folder, pa_filter=None):
        self.history_folder  = f"{output_folder}/history"
        self.inputs_folder   = f"{output_folder}/inputs"
        self.results_folder  = f"{output_folder}/results"
        self.metric_result_f = f"{self.results_folder}/metrics.xlsx"
        self.sales_folder    = sales_folder

        if not os.path.exists(output_folder):
            os.mkdir(output_folder)
        if not os.path.exists(self.history_folder):
            os.mkdir(self.history_folder)
        if not os.path.exists(self.inputs_folder):
            os.mkdir(self.inputs_folder)
            
        utils.replicateFile(initial_input_f, os.path.join(self.inputs_folder, "input_S2.json"))

        self.generateHistory(
            start_week,
            end_week,
            smoothing_filter=pa_filter
        )

        self.sim_history.load(history_folder=self.history_folder)

        self.sim_history.exportToExcel(
            prefix=Simulation.count,
            results_folder=self.results_folder
        )

        metrics.generateMetricsResult(
            hist=self.sim_history,
            dst_file=self.metric_result_f
        )
        Simulation.count += 1
