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
        self.pv = None
        self.pdp = None
        self.ba = None
        self.pa = None
        self.bp = None
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
        cum_hist.pv  = {a: {p: self.getQuantityCumHistory(self.pv[a][p]) for p in self.affiliate_products[a]} for a in self.affiliate_name}
        cum_hist.ba  = {a: {p: self.getQuantityCumHistory(self.ba[a][p]) for p in self.affiliate_products[a]} for a in self.affiliate_name}
        cum_hist.pa  = {a: {p: self.getQuantityCumHistory(self.pa[a][p]) for p in self.affiliate_products[a]} for a in self.affiliate_name}
        cum_hist.pdp = {p: self.getQuantityCumHistory(self.pdp[p]) for p in self.products}
        cum_hist.bp  = {p: self.getQuantityCumHistory(self.bp[p]) for p in self.products}
        return cum_hist

    def init(self, start_week, end_week):
        self.start_week = start_week
        self.end_week = end_week
        self.nbr_weeks = self.end_week - self.start_week + 1
        self.pv  = {a: {p: [None] * self.nbr_weeks for p in self.affiliate_products[a]} for a in self.affiliate_name}
        self.ba  = {a: {p: [None] * self.nbr_weeks for p in self.affiliate_products[a]} for a in self.affiliate_name}
        self.pa  = {a: {p: [None] * self.nbr_weeks for p in self.affiliate_products[a]} for a in self.affiliate_name}
        self.unavailability = {a: {p: [None] * self.nbr_weeks for p in self.affiliate_products[a]} for a in self.affiliate_name}
        self.pdp = {p: [None] * self.nbr_weeks for p in self.products}
        self.bp  = {p: [None] * self.nbr_weeks for p in self.products}
        self.s0  = {p: [None] * self.nbr_weeks for p in self.products}
        self.pa_product  = {p: [None] * self.nbr_weeks for p in self.products}

    def fillData(self, snapshot: dict):
        w = snapshot["week"] - self.start_week
        for p in self.products:
            for a in self.affiliate_name:
                if p in self.affiliate_products[a]:
                    self.ba[a][p][w] = snapshot["demand"][a][p]
                    self.pv[a][p][w] = snapshot["sales_forcast"][a][p]
                    self.pa[a][p][w] = snapshot["pa"][a][p]
                    self.unavailability[a][p][w] = snapshot["unavailabiliy"][a][p]
            self.pdp[p][w] = snapshot["reception"][p]
            self.bp[p][w] = snapshot["prod_demand"][p]
            self.s0[p][w] = snapshot["initial_stock"][p]
            self.pa_product[p][w] = snapshot["pa_product"][p]

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
                    wb["PV"].cell(row=3+w, column=3+t+w).value = sum([self.pv[a][p][w][t] for a in self.itProductAff(p)])
                    wb["BA"].cell(row=3+w, column=3+t+w).value = sum([self.ba[a][p][w][t] for a in self.itProductAff(p)])
                    wb["BP"].cell(row=3+w, column=3+t+w).value = self.bp[p][w][t]
                    wb["PDP"].cell(row=3+w, column=3+t+w).value = self.pdp[p][w][t]
                    wb["PA"].cell(row=3+w, column=3+t+w).value = self.pa_product[p][w][t]
            wb.save(dst_file)

        wb = openpyxl.load_workbook(self.history_template_f)
        wb.remove_sheet(wb["PDP"])
        wb.remove_sheet(wb["BP"])
        for a in self.affiliate_name:
            for p in self.affiliate_products[a]:
                dst_file = os.path.join(results_folder, f"{prefix}_{a}_{p}_history.xlsx")
                for w in range(self.nbr_weeks):
                    for t in range(self.horizon):
                        wb["PV"].cell(row=3+w, column=3+t+w).value = self.pv[a][p][w][t]
                        wb["BA"].cell(row=3+w, column=3+t+w).value = self.ba[a][p][w][t]
                        wb["PA"].cell(row=3+w, column=3+t+w).value = self.pa[a][p][w][t]
                wb.save(dst_file)
