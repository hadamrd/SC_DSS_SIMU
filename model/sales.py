import datetime
import random
import openpyxl
from . import Shared
from . import utils 
import os
import json 
from .shared import PvRandStrat
import copy


random.seed(datetime.datetime.now())
class SalesManager(Shared):

    def __init__(self) -> None:
        super().__init__()
        self.uncertainty_model: dict = {}
        self.loadModel(self.sales_UCMF)
    
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
        rd = round(rd)
        return rd

    def randPv(self, a: str):
        pv_range = self.affiliate_pv_range[a]
        return random.randint(0, pv_range)
    
    def getPvPm(self, pv, model):
        cpv = list(utils.accumu(pv))
        a, b, c, d, rw = model.values()
        t0 = [rw-1 for rw in rw]
        f = [cpv[t] - cpv[t0-1] if t0-1> 0 else cpv[t] for t,t0 in zip(range(self.horizon), t0)]
        A = [cpv + f*a for cpv,f,a in zip(cpv,f,a)]
        B = [cpv + f*b for cpv,f,b in zip(cpv,f,b)]
        C = [cpv + f*c for cpv,f,c in zip(cpv,f,c)]
        D = [cpv + f*d for cpv,f,d in zip(cpv,f,d)]
        return A, B, C, D
            
    def genRandSalesForcast(self, umcpv, pv_ref):
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
            init_pv: dict[str, dict[str, list[int]]] = json.load(fp)
        pv_ref = sales = init_pv
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

    

     