from os import stat
import openpyxl
from . import Shared
from . import utils
import math
import json 
import logging 


class RiskManager(Shared):

    def __init__(self) -> None:
        super().__init__()
        if self.demand_UCMF.endswith(".json"):
            self.loadDModel(self.demand_UCMF)
        elif self.demand_UCMF.endswith(".xlsx"):
            self.d_model = self.loadAffModelFromExcel(self.demand_UCMF, size=self.real_horizon)
        if self.reception_UCMF.endswith(".json"):
            self.loadRModel(self.reception_UCMF)
        elif self.reception_UCMF.endswith(".xlsx"):
            self.r_model = self.loadProductModelFromExcel(self.reception_UCMF, size=self.real_horizon)

    def getRiskMetrics(self, dpm, rpm, xc) -> dict[str, list[float]]:
        res = {
            "robustness": {p: None for p in self.products},
            "frequency": {p: None for p in self.products},
            "severity": {p: None for p in self.products},
            "adaptability": {p: None for p in self.products}
        }
        n = self.real_horizon
        for p in self.products:
            l4p = self.getL4Possibility(rpm[p], dpm[p], xc[p][:n])
            l4n = self.getL4Necessity(rpm[p], dpm[p], xc[p][:n])
            res["robustness"][p]    = self.getRobustness(l4p[:n])
            res["frequency"][p]     = self.getFrequency(l4p[:n])
            res["severity"][p]      = self.getSeverity(l4n[:n])
            res["adaptability"][p]  = 1 - l4n[-1]
        return res

    def getDitributions(self, prev_dpm, prev_rpm, cdemand_ref, creception_ref, initial_stock, k=0):
        n = self.real_horizon
        rpm = self.getEmptyProductQ()
        dpm = self.getEmptyAffQ()
        for p in self.products:
            s0 = initial_stock[p]
            rpm[p] = utils.getFuzzyDist(prev_rpm[p], creception_ref[p], self.r_model[p], n, s0=s0, k=k)
            for a in self.itProductAff(p):
                dpm[a][p] = utils.getFuzzyDist(prev_dpm[a][p], cdemand_ref[a][p], self.d_model[a][p], n, s0=0, k=k)
        return dpm, rpm

    def loadRModel(self, file_name):
        with open(file_name,) as fp:
            self.r_model = json.load(fp)
    
    def loadDModel(self, file_name):
        with open(file_name,) as fp:
            self.d_model = json.load(fp)
    
    @staticmethod
    def l4n(a: int, b: int, c: int, d: int, x: int) -> float:
        if d < c:
            raise Exception("d cant be smaller than c")
        if a >= d:
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
        return min([1 - v for v in l4p[self.fixed_horizon:self.real_horizon]])

    def getFrequency(self, l4p: list[float]) -> int:
        return sum([v > 0 for v in l4p[self.fixed_horizon:self.real_horizon]]) / len(l4p[self.fixed_horizon:self.real_horizon])

    def getSeverity(self, l4n: list[float]) -> int:
        return max(l4n[self.fixed_horizon:self.real_horizon])