from os import stat
import openpyxl
from . import Shared
from . import utils


class RiskManager(Shared):

    def __init__(self, umcd_f: str, umcr_f: str) -> None:
        super().__init__()
        self.loadDModel(umcd_f)
        self.loadRModel(umcr_f)
        
    def loadRModel(self, file_name: str) -> None:
        wb = openpyxl.load_workbook(file_name)
        sh = wb.active
        params = ["a", "b", "c", "d", "ModelType", "RefWeek"]
        self.r_model = {
            p: {
                param: utils.readSubRow(sh, 2 + j + len(params) * k, 5, self.real_horizon) if param != "RefWeek" else 
                utils.readRefWeekRow(sh, 2 + j + len(params) * k, 5, self.real_horizon) 
                for j, param in enumerate(params)
            } for k, p in enumerate(self.products)
        }
    
    def loadDModel(self, umcd_f: str):
        self.d_model = {a: {p: {} for p in ap} for a, ap in self.affiliate_products.items()}
        wb = openpyxl.load_workbook(umcd_f)
        sh = wb.active
        r = 2
        while sh.cell(r, 1).value:
            product = sh.cell(r, 1).value
            aff_code = sh.cell(r, 2).value
            aff = self.affiliate_code[aff_code]
            param = sh.cell(r, 4).value
            if param == "RefWeek":
                quantity = utils.readRefWeekRow(sh, r, 5, self.real_horizon)
            else:
                quantity = utils.readSubRow(sh, r, 5, self.real_horizon)
            self.d_model[aff][product][param] = quantity
            r += 1

    def getFuzzyDist(self, q, model, n, s0=0):
        params = ["a", "b", "c", "d"]
        Q = list(utils.accumu(q[:n]))
        dist = {param: [None] * n for param in params}
        for t in range(n):
            t0 = model["RefWeek"][t] - 1
            model_type = model["ModelType"][t] 
            for param in params:
                alpha_t = model[param][t]
                F_t = Q[t] - Q[t0-1] if t0-1 > 0 else Q[t]
                if model_type == "I1":
                    F_t /= t - t0 + 1
                dist[param][t] = Q[t] + alpha_t * F_t + s0
        for t in range(n):
            if t > 0:
                dist["a"][t] = max(dist["a"][t-1], dist["a"][t]) 
                dist["b"][t] = max(dist["b"][t-1], dist["b"][t]) 
            tr = n - 1 - t
            if tr < n - 1:
                dist["c"][tr] = min(dist["c"][tr], dist["c"][tr+1])
                dist["d"][tr] = min(dist["d"][tr], dist["d"][tr+1])
        return dist

    def getDpm(self, d, p) -> dict[str, dict[str, list[int]]]:
        n = self.real_horizon
        params = ["a", "b", "c", "d"]
        dist = {a: self.getFuzzyDist(d[a][p], self.d_model[a][p], n) for a in self.itProductAff(p)}
        return {param: [sum([dist[a][param][t] for a in dist]) for t in range(n)] for param in params}

    def getRpm(self, r, p, s0) ->  dict[str, list[int]]:
        n = self.real_horizon
        dist =  self.getFuzzyDist(r[p], self.r_model[p], n, s0)
        return dist
    
    @staticmethod
    def l4n(a: int, b: int, c: int, d: int, x: int) -> float:
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
        if c >= b:
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