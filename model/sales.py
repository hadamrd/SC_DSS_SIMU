import datetime
import random
import openpyxl
from . import Shared
from . import utils 
import os
import json 
from .shared import PvRandStrat
class SalesManager(Shared):

    def __init__(self, umcpv_f: str) -> None:
        super().__init__()
        self.uncertainty_model: dict = {}
        self.loadModel(umcpv_f)
    
    def loadModel(self, umcpv_f):
        wb = openpyxl.load_workbook(umcpv_f)
        self.uncertainty_model = {}
        for a in self.affiliate_name:
            aff_code = self.getAffiliateCode(a)
            sh = wb[aff_code]
            self.uncertainty_model[a] = {}
            for k, param in enumerate(["a", "b", "c", "d", "ref_week"]):
                self.uncertainty_model[a][param] = [sh.cell(row=2+k, column=t+2).value for t in range(self.horizon)]

    def randSalesForcast(self, a):
        ans = [self.randPv(a) for _ in range(self.horizon)]
        return ans

    def pickRandCPV(self, a, b, c, d):
        alpha = random.random()
        x1 = a + alpha * (b - a)
        x2 = d - alpha * (d - c)
        if self.pv_rand_strat == PvRandStrat.minmax:
            rd = x1 if random.random() < self.proba_pv_inf else x2
        elif self.pv_rand_strat == PvRandStrat.uniform:
            rd = x1 + (x2 - x1) * random.random()
        rd = round(rd / 10) * 10
        return rd

    def randPv(self, a: str):
        pv_range = self.affiliate_pv_range[a]
        return 10 * random.randint(0, pv_range//10)
    
    def getPvPm(self, pv, model):
        cpv = list(utils.accumu(pv))
        a, b, c, d, rw = model.values()
        A, B, C, D = [[None] * self.horizon] * 4
        for t in range(self.horizon):
            F_t = cpv[t] - cpv[rw[t]-2] if rw[t]-2> 0 else cpv[t]
            A[t] = round(cpv[t] + a[t] * F_t)
            B[t] = round(cpv[t] + b[t] * F_t)
            C[t] = round(cpv[t] + c[t] * F_t)
            D[t] = round(cpv[t] + d[t] * F_t)
        return A, B, C, D
            
    def genRandSalesForcast(self, umcpv, pv_ref):
        random.seed(datetime.datetime.now())
        acpv = [0 for _ in range(self.horizon)]
        A, B, C, D = self.getPvPm(pv_ref, umcpv)
        for t in range(self.horizon):
            rand_cpv = self.pickRandCPV(A[t], B[t], C[t], D[t])
            acpv[t] = max(rand_cpv, acpv[t-1] if t>0 else 0)
        pv_ref = utils.diff(acpv)
        return pv_ref
    
    def generateSalesHistory(self, initial_sales_f, start_week, end_week, dst_folder):
        print("Generating sales history ... ", end="")
        if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)
        utils.replicateFile(initial_sales_f, os.path.join(dst_folder, f"sales_S{start_week}.json"))
        with open(initial_sales_f) as fp:
            pv_ref: dict[str, dict[str, list[int]]] = json.load(fp)
        sales = pv_ref.copy()
        for w in range(start_week + 1, end_week + 1):     
            if self.pv_dependency:
                pv_ref = sales 
            for a, p in self.itParams():
                pv_ref[a][p] = pv_ref[a][p][1:] + [self.randPv(a)]
                sales[a][p] = self.genRandSalesForcast(self.uncertainty_model[a], pv_ref[a][p])
            dst_file = os.path.join(dst_folder, f"sales_S{w}.json")
            with open(dst_file, "w") as fp:
                json.dump(sales, fp)
        print("Finished")

    

     