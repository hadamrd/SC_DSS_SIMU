from . import Shared
from . import RiskManager, Model
from . import utils
import math

class SmoothingFilter(Shared):

    def __init__(self, risk_manager: RiskManager) -> None:
        super().__init__()
        self.risk_manager = risk_manager

    def validateOutput(self, x_in: list[int], x_out: list[int]):
        n = len(x_out)
        if n != len(x_in):
            raise Exception(f"Solution size {len(x_out)} != input size {len(x_in)}!")
        for t in range(1, n):
            if x_out[t] < x_out[t-1]:
                raise Exception(f"x_out[{t}] = {x_out[t]} < x_out[{t-1}] = {x_out[t-1]}!")
        if x_out[n-1] != x_in[n-1]:
            raise Exception("Didn't conserve same total quantity!")

    def filter(self, rpm: dict[str, list[int]], dpm: dict[str, list[int]], s0: int, x_in: list[int]):
        n = len(x_in)
        x = x_in.copy()
        l4n_in = RiskManager.getL4Necessity(rpm, dpm, x_in, s0)
        l4n = l4n_in.copy()
        to_solve = set([i for i in range(max(self.fixed_horizon-1,0), n-1) if l4n_in[i] >= self.l4n_threshold])
        unsolvable = set()
        while to_solve:
            for t in to_solve:
                if l4n[t] < self.l4n_threshold:
                    continue
                c, d = rpm["c"][t] + s0, rpm["d"][t] + s0 
                a, b = dpm["a"][t], dpm["b"][t]
                if d < a:
                    unsolvable.add(t) 
                    continue 
                if c >= b:
                    if x[t] < b:
                        x_star = round(b - self.l4n_threshold * (b - a)) + 1
                        x[t] = min(x_star, x[t+1])
                        if x[t] == x[t+1] and t + 1 not in to_solve:
                            unsolvable.add(t)
                    elif x[t] > c:
                        x_star = round(c + self.l4n_threshold * (d - c)) - 1
                        x[t] = max(x_star, x[t-1])
                        if x[t] == x[t-1] and t - 1 not in to_solve:
                            unsolvable.add(t)
                else:
                    x_star = ((b - a) * c + b * (d - c)) / (b - a + d - c)
                    if RiskManager.l4n(a, b, c, d, x_star) >= self.l4n_threshold:
                        unsolvable.add(t)
                    if x[t] > x_star:
                        x[t] = max(x_star, x[t-1])
                        if x[t] == x[t-1] and t - 1 not in to_solve:
                            unsolvable.add(t)
                    else:
                        x[t] = min(x_star, x[t+1])
                        if x[t] == x[t+1] and t + 1 not in to_solve:
                            unsolvable.add(t)
            l4n = RiskManager.getL4Necessity(rpm, dpm, x, s0)
            to_solve = set([i for i in range(max(self.fixed_horizon-1,0), n-1) if l4n[i] >= self.l4n_threshold]) - unsolvable
        return x

    def dispatchWithNetSupply(self, pa, supply_ratio, x, a, p):
        n = len(x)
        res = pa[:self.fixed_horizon] + [None for _ in range(self.fixed_horizon, n)]
        for t in range(self.fixed_horizon, n):
            res[t] = max(math.floor((x[t] * supply_ratio[a][p][t])), 0)
            if res[t] < 0:
                print("decumulated x: ", x)
                print("supply_ratio: ", supply_ratio[a][p])
                raise Exception("Got a negative x")
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
                    print("B aff / B tot: ", [daffpm[a]["b"][t] / sum([daffpm[a]["b"][t] for a in daffpm]) for t in range(n)])
                    raise Exception("dispatched plan is uncorrect xt-1 > xt") 
        return res

    def run(self, model: Model) -> dict[str, dict[str, list[int]]]:
        data = model.getCurrState()
        pa = data["pa"]
        pa_aff = model.pa_cdc.supply_plan
        reception = data["reception"]
        demand = data["demand"]
        initial_stock = data["initial_stock"]
        supply_ratio = model.pa_cdc.supply_ratio
        n = self.real_horizon
        decum_x_tot_out = {}
        decum_x_out = {a: {p: None for p in model.affiliate_products[a]} for a in model.affiliate_name}

        for product in self.products:
            # get product inputs
            x_in = list(utils.accumu(pa[product][:n]))
            cum_reception = list(utils.accumu(reception[product][:n]))
            s0 = initial_stock[product]
            # calculate possibility models
            rpm = self.risk_manager.getRpm(cum_reception, product)
            aff_dpm = self.risk_manager.getDpm(demand, product)
            # get dpm / product, sum over afiiliate
            params = ["a", "b", "c", "d"]
            dpm = {param: [sum([aff_dpm[a][param][t] for a in aff_dpm]) for t in range(n)] for param in params}
            # smoothing
            x_out_product = self.filter(rpm, dpm, s0, x_in)
            self.validateOutput(x_in, x_out_product)
            # decumlate
            decum_x_tot_out[product] = utils.diff(x_out_product) + pa[product][n:]
            # print("x_out: ", x_out[product])
            # print("decum x_out: ", decum_product_x)

        for a, p in self.itParams():
            # print("Processing product: ", product)
            # affs = [a for a in model.affiliate_name if product in model.affiliate_product[a]]
            # print(f"affiliates that consume {product} are : {affs}")
            decum_x_out[a][p] = self.dispatchWithNetSupply(pa_aff[a][p], supply_ratio, decum_x_tot_out[p], a, p)

        return decum_x_out



