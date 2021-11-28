import openpyxl
import json 
import os
import re 
from model import utils
import metrics

class History:
    def __init__(self, simu_params_f) -> None:
        with open(simu_params_f) as fp:
            self.model_params = json.load(fp)
        self.products = self.model_params["products"]
        self.affiliates = self.model_params["affiliates"]
        self.horizon = self.model_params["horizon"]
        self.start_week = None
        self.end_week = None

    def getCumHistory(self, q_history):
        nbr_weeks = len(q_history)
        Q_history = [None] * nbr_weeks
        for w in range(nbr_weeks):
            Qr = Q_history[w-1][0] if w != 0 else 0
            Q_history[w] = list(utils.accumu(q_history[w], Qr))
        return Q_history
    
    def load(self, history_folder):
        for file_name in os.listdir(history_folder):
            if file_name.startswith("snapshot_S"):
                week = int(re.match(".*S(\d+).*", file_name).group(1))
                self.start_week = min(week, self.start_week) if self.start_week is not None else week
                self.end_week = max(week, self.end_week) if self.end_week is not None else week
        self.nbr_weeks = self.end_week - self.start_week + 1
        
        self.product_sales = [None] * self.nbr_weeks
        self.prod_plan =  [None] * self.nbr_weeks
        self.supply_demand =  [None] * self.nbr_weeks
        self.supply_plan =  [None] * self.nbr_weeks
        self.prod_demand =  [None] * self.nbr_weeks

        for file_name in os.listdir(history_folder):
            if file_name.startswith("snapshot_S"):
                with open(os.path.join(history_folder, file_name)) as fp:
                    snapshot = json.load(fp)
                week = int(re.match(".*S(\d+).*", file_name).group(1))
                self.supply_demand[week-self.start_week] = snapshot["supply_demand"]
                self.prod_plan[week-self.start_week] = snapshot["prod_plan"]
                self.supply_plan[week-self.start_week] = snapshot["supply_plan"]
                self.prod_demand[week-self.start_week] = snapshot["prod_demand"]
                self.product_sales[week-self.start_week] = snapshot["sales_forcast"]
    
    def exportToExcel(self, prefix, results_folder, template_file):
        if not os.path.exists(results_folder):
            os.mkdir(results_folder)

        wb = openpyxl.load_workbook(template_file)
        for p in self.products:
            for w in range(self.nbr_weeks):
                for t in range(self.horizon):
                    wb["PV"].cell(row=3+w, column=3+t+w).value = sum([self.product_sales[w][a][p][t] for a in self.affiliates if p in self.model_params["affiliate_product"][a]])
                    wb["BA"].cell(row=3+w, column=3+t+w).value = sum([self.supply_demand[w][a][p][t] for a in self.affiliates if p in self.model_params["affiliate_product"][a]])
                    wb["BP"].cell(row=3+w, column=3+t+w).value = self.prod_demand[w][p][t]
                    wb["PDP"].cell(row=3+w, column=3+t+w).value = self.prod_plan[w][p][t]
                    wb["PA"].cell(row=3+w, column=3+t+w).value = sum([self.supply_plan[w][a][p][t] for a in self.affiliates if p in self.model_params["affiliate_product"][a]])
            wb.save(os.path.join(results_folder, f"{prefix}_{p}_results.xlsx"))

        wb = openpyxl.load_workbook(template_file)
        wb.remove_sheet(wb["PDP"])
        wb.remove_sheet(wb["BP"])
        for a in self.affiliates:
            for p in self.model_params["affiliate_product"][a]:
                for w in range(self.nbr_weeks):
                    for t in range(self.horizon):
                        wb["PV"].cell(row=3+w, column=3+t+w).value = self.product_sales[w][a][p][t]
                        wb["BA"].cell(row=3+w, column=3+t+w).value = self.supply_demand[w][a][p][t]
                        wb["PA"].cell(row=3+w, column=3+t+w).value = self.supply_plan[w][a][p][t]
                wb.save(os.path.join(results_folder, f"{prefix}_{a}_{p}_results.xlsx"))


def main():
    horizon = 20
    simulation_folder = "simu_result"
    hist = History("simu_inputs/global_input.json")
    hist.load(history_folder=f"{simulation_folder}/history_with_strat")

    product = "P1"
    affiliate = "france"
    pa_hist = [[hist.supply_plan[w][affiliate][product][t] for t in range(horizon)] for w in range(hist.nbr_weeks)]
    PA_hist = hist.getCumHistory(pa_hist)
    m = metrics.GI(PA_hist)
    print(m)

if __name__ == "__main__":
    main()
