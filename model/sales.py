import datetime
import random
import openpyxl
from . import utils 

random.seed(datetime.datetime.now())

class Sales:

    def __init__(self, model) -> None:
        self.model = model
        wb = openpyxl.load_workbook(model.sales_uncertainty_model_file)
        self.uncertainty_model = {}
        for aff in self.model.affiliate_name:
            aff_code = self.model.getAffiliateCode(aff)
            sh = wb[aff_code]
            self.uncertainty_model[aff] = {}
            for k, param in enumerate(["a", "b", "c", "d", "ref_week"]):
                self.uncertainty_model[aff][param] = [sh.cell(row=2+k, column=t+2).value for t in range(self.model.horizon)]

    def randSalesForcast(self, a):
        ans = [self.randPv(a) for _ in range(self.model.horizon)]
        return ans

    def pickRandCPV(self, a, b, c, d):
        alpha = random.random()
        x1 = alpha * (b - a) + a
        x2 = d - alpha * (d - c)
        rd = random.choice([x1, x2])
        rd = round(rd / 10) * 10
        return rd

    def randPv(self, a: str):
        pv_range = self.model.affiliate_pv_range[a]
        return 10 * random.randint(0, pv_range//10)

    def getRandCPV(self, a: str, prev_pv: list):
        pv = prev_pv[1:] + [self.randPv(a)]
        cpv = list(utils.accumu(pv))
        acpv = [0 for _ in range(self.model.horizon)]
        a, b, c, d, rw = self.uncertainty_model[a].values()
        for t in range(self.model.horizon):
            F_t = cpv[t] - cpv[rw[t]-2] if rw[t]-2> 0 else cpv[t]
            min_1 = round(cpv[t] + a[t] * F_t)
            min_2 = round(cpv[t] + b[t] * F_t)
            max_2 = round(cpv[t] + c[t] * F_t)
            max_1 = round(cpv[t] + d[t] * F_t)
            rand_cpv = self.pickRandCPV(min_1, min_2, max_1, max_2)
            acpv[t] = max(rand_cpv, acpv[t-1] if t>0 else 0)
        return acpv
            
    def genRandSalesForcast(self, affiliate, prev_pv=None):
        horizon = self.model.horizon
        if prev_pv is None:
            return self.randSalesForcast(affiliate)
        rcpv = self.getRandCPV(affiliate, prev_pv)
        pv = [rcpv[0]] + [rcpv[t] - rcpv[t-1] for t in range(1, horizon)]
        return pv

if __name__=="__main__":
    pass 