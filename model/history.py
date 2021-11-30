import openpyxl
import json 
import os
import re
from . import utils, Shared


class History(Shared):
    def __init__(self) -> None:
        super().__init__()
        self.start_week = None
        self.end_week = None
        self.sales_forcast = None
        self.prod_plan = None
        self.supply_demand = None
        self.supply_plan = None
        self.prod_demand = None
        self.pa_product = None
        self.ba_product = None
        self.pv_product = None
        self.l4n_in = None
        self.l4n_out = None
        self.unavailability = None


    def getQuantityCumHistory(self, q_history):
        nbr_weeks = len(q_history)
        Q_history = [None] * nbr_weeks
        for w in range(nbr_weeks):
            Qr = Q_history[w-1][0] if w != 0 else 0
            Q_history[w] = list(utils.accumu(q_history[w], Qr))
        return Q_history

    def sumCumHistOverAff(self, cumHist):
        return {p: [[
            sum([
                cumHist[a][p][w][t] for a in self.itProductAff(p)
                ]) for t in range(self.horizon)]
                for w in range(self.nbr_weeks)]
                for p in self.products}

    def getCumHistory(self):
        cum_hist = History()
        cum_hist.sales_forcast  = {a: {p: self.getQuantityCumHistory(self.sales_forcast[a][p]) for p in self.affiliate_products[a]} for a in self.affiliate_name}
        cum_hist.supply_demand  = {a: {p: self.getQuantityCumHistory(self.supply_demand[a][p]) for p in self.affiliate_products[a]} for a in self.affiliate_name}
        cum_hist.supply_plan    = {a: {p: self.getQuantityCumHistory(self.supply_plan[a][p]) for p in self.affiliate_products[a]} for a in self.affiliate_name}
        cum_hist.prod_plan      = {p: self.getQuantityCumHistory(self.prod_plan[p]) for p in self.products}
        cum_hist.prod_demand    = {p: self.getQuantityCumHistory(self.prod_demand[p]) for p in self.products}
        return cum_hist

    def init(self, start_week, end_week):
        self.start_week = start_week
        self.end_week = end_week
        self.nbr_weeks = self.end_week - self.start_week + 1
        self.sales_forcast  = {a: {p: [None] * self.nbr_weeks for p in self.affiliate_products[a]} for a in self.affiliate_name}
        self.supply_demand  = {a: {p: [None] * self.nbr_weeks for p in self.affiliate_products[a]} for a in self.affiliate_name}
        self.supply_plan    = {a: {p: [None] * self.nbr_weeks for p in self.affiliate_products[a]} for a in self.affiliate_name}
        self.unavailability = {a: {p: [None] * self.nbr_weeks for p in self.affiliate_products[a]} for a in self.affiliate_name}
        self.prod_plan      = {p: [None] * self.nbr_weeks for p in self.products}
        self.prod_demand    = {p: [None] * self.nbr_weeks for p in self.products}
        self.l4n_in = {p: [None] * self.nbr_weeks for p in self.products}
        self.g_risk_in = {p: [None] * self.nbr_weeks for p in self.products}
        self.l4n_out = {p: [None] * self.nbr_weeks for p in self.products}
        self.g_risk_out = {p: [None] * self.nbr_weeks for p in self.products}

    def fillData(self, snapshot):
        w = snapshot["week"] - self.start_week
        for p in self.products:
            for a in self.affiliate_name:
                if p in self.affiliate_products[a]:
                    self.supply_demand[a][p][w] = snapshot["supply_demand"][a][p]
                    self.sales_forcast[a][p][w] = snapshot["sales_forcast"][a][p]
                    self.supply_plan[a][p][w] = snapshot["supply_plan"][a][p]
                    self.unavailability[a][p][w] = snapshot["unavailabiliy"][a][p]
            self.prod_plan[p][w] = snapshot["prod_plan"][p]
            self.prod_demand[p][w] = snapshot["prod_demand"][p]
            if "l4n_in" in snapshot:
                self.l4n_in[p][w] = snapshot["l4n_in"][p]
                self.g_risk_in[p][w] = max(snapshot["l4n_in"][p][self.fixed_horizon-1:])
            if "l4n_out" in snapshot:
                self.l4n_out[p][w] = snapshot["l4n_out"][p]
                self.g_risk_out[p][w] = max(snapshot["l4n_out"][p][self.fixed_horizon-1:])


    def load(self, history_folder):
        for file_name in os.listdir(history_folder):
            if file_name.startswith("snapshot_S"):
                week = int(re.match(".*S(\d+).*", file_name).group(1))
                start_week = min(week, self.start_week) if self.start_week is not None else week
                end_week = max(week, self.end_week) if self.end_week is not None else week
        self.init(start_week, end_week)
        for file_name in os.listdir(history_folder):
            if file_name.startswith("snapshot_S"):
                with open(os.path.join(history_folder, file_name)) as fp:
                    snapshot = json.load(fp)
                self.fillData(snapshot)

    def exportToExcel(self, prefix, results_folder):
        if not os.path.exists(results_folder):
            os.mkdir(results_folder)

        wb = openpyxl.load_workbook(self.history_template_f)
        for p in self.products:
            dst_file = os.path.join(results_folder, f"{prefix}_{p}_history.xlsx")
            for w in range(self.nbr_weeks):
                for t in range(self.horizon):
                    wb["PV"].cell(row=3+w, column=3+t+w).value = sum([self.sales_forcast[a][p][w][t] for a in self.itProductAff(p)])
                    wb["BA"].cell(row=3+w, column=3+t+w).value = sum([self.supply_demand[a][p][w][t] for a in self.itProductAff(p)])
                    wb["BP"].cell(row=3+w, column=3+t+w).value = self.prod_demand[p][w][t]
                    wb["PDP"].cell(row=3+w, column=3+t+w).value = self.prod_plan[p][w][t]
                    wb["PA"].cell(row=3+w, column=3+t+w).value = sum([self.supply_plan[a][p][w][t] for a in self.itProductAff(p)])
            wb.save(dst_file)

        wb = openpyxl.load_workbook(self.history_template_f)
        wb.remove_sheet(wb["PDP"])
        wb.remove_sheet(wb["BP"])
        for a in self.affiliate_name:
            for p in self.affiliate_products[a]:
                dst_file = os.path.join(results_folder, f"{prefix}_{a}_{p}_history.xlsx")
                for w in range(self.nbr_weeks):
                    for t in range(self.horizon):
                        wb["PV"].cell(row=3+w, column=3+t+w).value = self.sales_forcast[a][p][w][t]
                        wb["BA"].cell(row=3+w, column=3+t+w).value = self.supply_demand[a][p][w][t]
                        wb["PA"].cell(row=3+w, column=3+t+w).value = self.supply_plan[a][p][w][t]
                wb.save(dst_file)
