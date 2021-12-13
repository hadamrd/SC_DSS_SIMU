from os import stat
import openpyxl
from . import Shared
from . import utils
import math
import json 

class RiskManager(Shared):

    def __init__(self) -> None:
        super().__init__()
        if self.demand_UCMF.endswith(".json"):
            self.loadDModel(self.demand_UCMF)
        elif self.demand_UCMF.endswith(".xlsx"):
            self.d_model = self.loadAffModelFromExcel(self.demand_UCMF, size=self.real_horizon)
        if self.demand_UCMF.endswith(".json"):
            self.loadRModel(self.reception_UCMF)
        elif self.demand_UCMF.endswith(".xlsx"):
            self.loadProductModelFromExcel(self.demand_UCMF)

    def getRiskMetrics(self, dpm, rpm, xc) -> dict[str, list[float]]:
        res = {
            "robustness": {p: None for p in self.products},
            "frequency": {p: None for p in self.products},
            "severity": {p: None for p in self.products},
            "adaptability": {p: None for p in self.products}
        }
        for p in self.products:
            l4p = self.getL4Possibility(rpm[p], dpm[p], xc[p])
            l4n = self.getL4Necessity(rpm[p], dpm[p], xc[p])
            res["robustness"][p]    = self.getRobustness(l4p)
            res["frequency"][p]     = self.getFrequency(l4p)
            res["severity"][p]      = self.getSeverity(l4n)
            res["adaptability"][p]  = 1 - l4n[-1]
        return res

    def getDitributions(self, cdemand_ref, creception_ref, initial_stock, k=0):
        rpm = {p: None for p in self.products}
        dpm = {p: None for p in self.products}
        for p in self.products:
            s0 = initial_stock[p]
            rpm[p] = self.getRpm(creception_ref, p, s0, k)
            dpm[p] = self.getDpm(cdemand_ref, p, k)
        return dpm, rpm

    def loadRModel(self, file_name):
        with open(file_name,) as fp:
            self.r_model = json.load(fp)
    
    def loadDModel(self, file_name):
        with open(file_name,) as fp:
            self.d_model = json.load(fp)

    def getFuzzyDist(self, cq, model, n, s0=0, k=0):
        params = ["a", "b", "c", "d"]
        dist = {param: [None] * n for param in params}
        for t in range(n):
            t0 = model["RefWeek"][t] - 1
            model_type = model["ModelType"][t] 
            for param in params:
                alpha_t = model[param][t]
                F_t = cq[t+k] - cq[k+t0-1] if k+t0-1 > 0 else cq[t+k]
                if model_type == "I1":
                    F_t /= t - t0 + 1
                dist[param][t] = round(cq[t+k] + alpha_t * F_t + s0)
        for t in range(n):
            if t > 0:
                dist["a"][t] = max(dist["a"][t-1], dist["a"][t]) 
                dist["b"][t] = max(dist["b"][t-1], dist["b"][t]) 
            tr = n - 1 - t
            if tr < n - 1:
                dist["c"][tr] = min(dist["c"][tr], dist["c"][tr+1])
                dist["d"][tr] = min(dist["d"][tr], dist["d"][tr+1])
            dist["b"][t] = max(dist["a"][t], dist["b"][t]) 
            dist["c"][t] = max(dist["b"][t], dist["c"][t])  
            dist["d"][t] = max(dist["c"][t], dist["d"][t])
        return dist

    def getDpm(self, cd, p, k=0) -> dict[str, dict[str, list[int]]]:
        n = self.real_horizon
        params = ["a", "b", "c", "d"]
        dist = {a: self.getFuzzyDist(cd[a][p], self.d_model[a][p], n, s0=0, k=k) for a in self.itProductAff(p)}
        dist = {param: [sum([dist[a][param][t] for a in dist]) for t in range(n)] for param in params}       
        for t in range(n):
            if t > 0:
                dist["a"][t] = max(dist["a"][t-1], dist["a"][t]) 
                dist["b"][t] = max(dist["b"][t-1], dist["b"][t]) 
            tr = n - 1 - t
            if tr < n - 1:
                dist["c"][tr] = min(dist["c"][tr], dist["c"][tr+1])
                dist["d"][tr] = min(dist["d"][tr], dist["d"][tr+1])
            dist["b"][t] = max(dist["a"][t], dist["b"][t]) 
            dist["c"][t] = max(dist["b"][t], dist["c"][t])  
            dist["d"][t] = max(dist["c"][t], dist["d"][t])
        return dist

    def getRpm(self, cr, p, s0, k=0) ->  dict[str, list[int]]:
        n = self.real_horizon
        dist =  self.getFuzzyDist(cr[p], self.r_model[p], n, s0=s0, k=k)
        return dist
    
    @staticmethod
    def l4n(a: int, b: int, c: int, d: int, x: int) -> float:
        if a > d:
            return 1
        if x == c or x == b:
            return 0
        if c >= b:
            return utils.affineY(c, d, x) + 1 - utils.affineY(a, b, x)
        if c < b:
            x_star = ((b - a) * c + b * (d - c)) / (b - a + d - c)
            if x <= x_star :
                return 1 - utils.affineY(a, b, x)
            elif x > x_star:
                return utils.affineY(c, d, x)

    @staticmethod
    def l4p(a: int, b: int, c: int, d: int, x: int) -> float:
        if c > b:
            return 1
        if x == d or x == a:
            return 0
        if d <= a:
            return utils.affineY(a, b, x) + 1 - utils.affineY(c, d, x)
        if d > a:
            x_star = ((b - a) * d + a * (d - c)) / (b - a + d - c)
            if x <= x_star :
                return 1 - utils.affineY(c, d, x)
            elif x > x_star:
                return utils.affineY(a, b, x)
    
    @staticmethod
    def getMinL4n(a, b, c, d):
        if d < a:
            return 1
        if b <= c:
            return 0
        x_star = ((b - a) * c + b * (d - c)) / (b - a + d - c)
        return RiskManager.l4n(a, b, c, d, x_star)

    @staticmethod
    def getL4nAlphaBound(alpha, a, b, c, d):
        x1 = math.floor(b - (b - a) * alpha + 1) if a != b else a
        x2 = math.ceil(alpha * d + (1 - alpha) * c  - 1) if c != d else c
        return x1, x2

    @staticmethod
    def getL4Possibility(rpm: dict[str, list[int]], dpm: dict[str, list[int]], x: list) -> list[float]:
        l4_possibility = [RiskManager.l4p(a, b, c, d, xt) for a, b, c, d, xt in zip(dpm["a"], dpm["b"], rpm["c"], rpm["d"], x)]
        return l4_possibility

    @staticmethod
    def getL4Necessity(rpm: dict[str, list[int]], dpm: dict[str, list[int]], x: list) -> list[float]:
        l4_necessity = [RiskManager.l4n(a, b, c, d, xt) for a, b, c, d, xt in zip(dpm["a"], dpm["b"], rpm["c"], rpm["d"], x)]
        return l4_necessity
    
    def getRobustness(self, l4p: list[float]) -> float:
        return min([1 - v for v in l4p[self.fixed_horizon-1:]])

    def getFrequency(self, l4p: list[float]) -> int:
        return sum([v > 0 for v in l4p[self.fixed_horizon-1:]]) / len(l4p[self.fixed_horizon-1:])

    def getSeverity(self, l4n: list[float]) -> int:
        return max(l4n[self.fixed_horizon-1:])