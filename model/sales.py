import datetime
import random
import openpyxl
from . import Shared
from . import utils 
import os
import json 

class SalesManager(Shared):

    def __init__(self, umcpv_f: str) -> None:
        super().__init__()
        self.pv_ref: list[int] = None
        self.dependency = True
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
        x1 = alpha * (b - a) + a
        x2 = d - alpha * (d - c)
        rd = x1 if random.random() < self.proba_pv_inf else x2
        rd = random.choice([x1, x2])
        rd = round(rd / 10) * 10
        return rd

    def randPv(self, a: str):
        pv_range = self.affiliate_pv_range[a]
        return 10 * random.randint(0, pv_range//10)

    def getRandCPV(self, a: str, p:str, prev_pv: list=None):
        if not prev_pv:
            self.pv_ref[a][p] = self.pv_ref[a][p][1:] + [self.randPv(a)]
            pv = self.pv_ref[a][p]
        else:
            pv = prev_pv[a][p][1:] + [self.randPv(a)]
        cpv = list(utils.accumu(pv))
        acpv = [0 for _ in range(self.horizon)]
        a, b, c, d, rw = self.uncertainty_model[a].values()
        for t in range(self.horizon):
            F_t = cpv[t] - cpv[rw[t]-2] if rw[t]-2> 0 else cpv[t]
            min_1 = round(cpv[t] + a[t] * F_t)
            min_2 = round(cpv[t] + b[t] * F_t)
            max_2 = round(cpv[t] + c[t] * F_t)
            max_1 = round(cpv[t] + d[t] * F_t)
            rand_cpv = self.pickRandCPV(min_1, min_2, max_1, max_2)
            acpv[t] = max(rand_cpv, acpv[t-1] if t>0 else 0)
        return acpv
            
    def genRandSalesForcast(self, affiliate, product, prev_pv=None):
        random.seed(datetime.datetime.now())
        rcpv = self.getRandCPV(affiliate, product, prev_pv)
        pv = utils.diff(rcpv)
        return pv
    
    def generateSalesHistory(self, initial_sales_f, start_week, end_week, dst_folder, dependency=True):
        print("Generating sales history ... ", end="")
        if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)
        utils.replicateFile(initial_sales_f, os.path.join(dst_folder, f"sales_S{start_week}.json"))
        with open(initial_sales_f) as fp:
            self.pv_ref: int = json.load(fp)

        sales = self.pv_ref.copy()     
        for w in range(start_week + 1, end_week + 1):
            sales =  {
                a: {
                    p: self.genRandSalesForcast(a, p, sales if dependency else None) for p in aff_products
                } for a, aff_products in self.affiliate_products.items()
            }
            dst_file = os.path.join(dst_folder, f"sales_S{w}.json")
            with open(dst_file, "w") as fp:
                json.dump(sales, fp)
        print("Finished")

    

     