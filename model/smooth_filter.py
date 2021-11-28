from math import prod
from .risk_manager import RiskManager
from .model import Model
from . import utils
from model import risk_manager


class SmoothFilter:

    def __init__(self, alpha, fixed_horizon) -> None:
        self.alpha = alpha
        self.fix_hor = fixed_horizon

    def validateOutput(self, x_in, x_out):
        n = len(x_out)
        if n != len(x_in):
            raise Exception(f"Solution size {len(x_out)} != input size {len(x_in)}!")
        for t in range(1, n):
            if x_out[t] < x_out[t-1]:
                raise Exception(f"x_out[{t}] = {x_out[t]} < x_out[{t-1}] = {x_out[t-1]}!")
        if x_out[n-1] != x_in[n-1]:
            raise Exception("Didn't conserve same total quantity!")

    def filter(self, risk_m: RiskManager, rpm: dict, dpm: dict, s0: int, x_in: list):
        n = risk_m.horizon
        x = x_in.copy()
        l4n_in = risk_m.getL4Necessity(rpm, dpm, x_in, s0)
        l4n = l4n_in.copy()
        to_solve = set([i for i in range(self.fix_hor, n-1) if l4n_in[i] >= self.alpha])
        unsolvable = set()
        solved = set()
        n_iter = 0
        max_iter = 200
        while solved | unsolvable != to_solve and n_iter < max_iter:
            for t in to_solve - unsolvable:
                if l4n[t] < self.alpha:
                    continue
                c, d = rpm["c"][t] + s0, rpm["d"][t] + s0 
                a, b = dpm["a"][t], dpm["b"][t]
                if d < a:
                    unsolvable.add(t) 
                    continue 
                if c >= b:
                    if x[t] < b:
                        x[t] = min(b, x[t+1])
                        if t == n-2 and x[t] == x[-1] and l4n_in[-1] >= self.alpha:
                            unsolvable.add(t)
                    elif x[t] > c:
                        x[t] = max(c, x[t-1])
                else:
                    x_star = ((b - a) * c + b * (d - c)) / (b - a + d - c)
                    if risk_m._l4n(c, d, a, b, x_star) >= self.alpha:
                        unsolvable.add(t)
                    if x[t] > x_star:
                        x[t] = max(x_star, x[t-1])
                    else:
                        x[t] = min(x_star, x[t+1])
            l4n = risk_m.getL4Necessity(rpm, dpm, x, s0)
            solved = set([i for i in range(n) if l4n[i] < self.alpha <= l4n_in[i]])
            n_iter += 1
        return x

    def dispatchWithBruteSupply(self, supply_ratio, x, a, p):
        n = len(x)
        res = [None for _ in range(n)]
        for t in range(n):
            res[t] = round(x[t] * supply_ratio[a][p][t])
        return res

    def dispatchWithRiskModel(self, daffpm, x):
        n = len(x)
        res = {a: [None for _ in range(n)] for a in daffpm}
        for a in daffpm:
            for t in range(1, n):
                if x[t] < x[t-1]:
                    raise Exception("The plan x is uncorrect xt-1 > xt", x)
            for t in range(n):
                tot_dem = sum([daffpm[a]["b"][t] for a in daffpm])
                res[a][t] = round(x[t] * daffpm[a]["b"][t] / tot_dem) if tot_dem != 0 else 0
            for t in range(1, n):
                if res[a][t] < res[a][t-1]:
                    print("affiliate: ", a)
                    print("X aff: ", res[a])
                    print("B aff: ", daffpm[a]["b"])
                    print("B aff / B tot: ", [daffpm[a]["b"][t]/sum([daffpm[a]["b"][t] for a in daffpm]) for t in range(n)])
                    raise Exception("dispatched plan is uncorrect xt-1 > xt") 
        return res

    def run(self, risk_manager: RiskManager, model: Model) -> dict[str, dict[str, list[int]]]:
        data = model.getCurrState()
        pa = data["pa"]
        reception = data["reception"]
        supply = data["demand"]
        initial_stock = data["initial_stock"]
        supply_ratio = model.pa_cdc.supply_ratio
        n = risk_manager.horizon
        decum_x_out = {}
        decum_x_out = {a: {p: None for p in model.affiliate_product[a]} for a in model.affiliate_name}

        for product in pa:
            # get product inputs
            x_in = list(utils.accumu(pa[product]))[:n]
            r = list(utils.accumu(reception[product]))[:n]
            s0 = initial_stock[product]
            # calculate possibility models
            rpm = risk_manager.getRpm(r, product)
            aff_dpm = risk_manager.getDpm(supply, product)
            # get dpm / product, sum over afiiliate
            params = ["a", "b", "c", "d"]
            dpm = {param: [sum([aff_dpm[a][param][t] for a in aff_dpm]) for t in range(n)] for param in params}
            # smoothing
            x_out_product = self.filter(risk_manager, rpm, dpm, s0, x_in)
            self.validateOutput(x_in, x_out_product)
            # decumlate
            decum_x_out[product] = utils.diff(x_out_product) + pa[product][n:]
            # print("x_out: ", x_out[product])
            # print("decum x_out: ", decum_product_x)

        for a in supply:
            for p in supply[a]:
                # print("Processing product: ", product)
                # affs = [a for a in model.affiliate_name if product in model.affiliate_product[a]]
                # print(f"affiliates that consume {product} are : {affs}")
                decum_x_out[a][p] = self.dispatchWithBruteSupply(supply_ratio, decum_x_out[p], a, p)

        return decum_x_out

if __name__ == "__main__":
    pass


