import openpyxl
from . import Shared
from . import utils


class RiskManager(Shared):

    def __init__(self, umcd_f: str, umcr_f: str) -> None:
        super().__init__()
        self.loadDModel(umcd_f)
        self.loadRModel(umcr_f)

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
    
    def getDpm(self, d, p) -> dict[str, dict[str, list[int]]]:
        n = self.real_horizon
        params = ["a", "b", "c", "d"]
        dist = {a: {param: [0] * n for param in params + ["ref_week", "model_type"]} for a in d}
        for a in self.itProductAff(p):
            Q = list(utils.accumu(d[a][p]))

            for t in range(n):
                rw_t = self.d_model[a][p]["RefWeek"][t]
                model_type = self.d_model[a][p]["ModelType"][t] 
                for param in params:
                    alpha_t = self.d_model[a][p][param][t]
                    F_t = Q[t] - Q[rw_t-2] if rw_t-2 > 0 else Q[t]
                    if model_type == "I1":
                        F_t /= t - (rw_t-1) + 1
                    dist[a][param][t] = Q[t] + alpha_t * F_t

            for t in range(n):
                if t > 0:
                    dist[a]["a"][t] = max(dist[a]["a"][t-1], dist[a]["a"][t]) 
                    dist[a]["b"][t] = max(dist[a]["b"][t-1], dist[a]["b"][t]) 

                tr = n - 1 - t
                if tr < n - 1:
                    dist[a]["c"][tr] = min(dist[a]["c"][tr], dist[a]["c"][tr+1])
                    dist[a]["d"][tr] = max(dist[a]["d"][tr], dist[a]["d"][tr+1])
        return dist
        
    def loadRModel(self, file_name: str) -> None:
        wb = openpyxl.load_workbook(file_name)
        sh = wb.active
        params = ["a", "b", "c", "d", "model_type", "ref_week"]
        self.r_model = {
            p: {
                param: utils.readSubRow(sh, 2 + j + len(params) * k, 5, self.real_horizon) if param != "ref_week" else 
                utils.readRefWeekRow(sh, 2 + j + len(params) * k, 5, self.real_horizon) 
                for j, param in enumerate(params)
            } for k, p in enumerate(self.products)
        }
    
    def getRpm(self, reception:list, p: str) ->  dict[str, list[int]]:
        params = ["a", "b", "c", "d"]
        Q = list(utils.accumu(reception))
        dist = {param: [None] * self.real_horizon for param in params}
        for t in range(self.real_horizon):
            rw_t = self.r_model[p]["ref_week"][t]
            model_type = self.r_model[p]["model_type"][t]
            F_t = Q[t] - Q[rw_t-2] if rw_t-2>0 else Q[t]
            for param in params:
                alpha_t = self.r_model[p][param][t]
                if model_type == "I2":
                    dist[param][t] = round(Q[t] + alpha_t * F_t)
                elif model_type == "I1":
                    dist[param][t] = round(Q[t] + alpha_t * F_t / (t - (rw_t-1) + 1))
        return dist
    
    @staticmethod
    def l4n(a: int, b: int, c: int, d: int, x: int) -> float:
        if a > d:
            return 1
        if x == c or x == b:
            return 0
        elif c >= b:
            return utils.affineY(c, d, x) + 1 - utils.affineY(a, b, x)
        elif c < b:
            x_star = ((b - a) * c + b * (d - c)) / (b - a + d - c)
            if x <= x_star :
                return 1 - utils.affineY(a, b, x)
            elif x > x_star:
                return utils.affineY(c, d, x)

    @staticmethod
    def getL4Necessity(rpm: dict[str, list[int]], dpm: dict[str, list[int]], x: list, s0: int) -> list[float]:
        l4_necessity = [RiskManager.l4n(a, b, c + s0, d + s0, xt) for a, b, c, d, xt in zip(dpm["a"], dpm["b"], rpm["c"], rpm["d"], x)]
        return l4_necessity
