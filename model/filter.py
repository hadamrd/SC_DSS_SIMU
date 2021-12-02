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

    def findBest(self, x, x_star, t, domain: set, unsolvable: set):
        if x[t] < x_star:
            x[t] = min(x_star, x[t+1])
            if x[t] == x[t+1] and t + 1 not in domain:
                unsolvable.add(t)
        else:
            x[t] = max(x_star, x[t-1])
            if x[t] == x[t-1] and t - 1 not in domain:
                unsolvable.add(t)
        return x[t]
    
    def filter(self, rpm: dict[str, list[int]], dpm: dict[str, list[int]], s0: int, x_in: list[int]):
        n = len(x_in)
        x = x_in.copy()
        l4n_in = self.risk_manager.getL4Necessity(rpm, dpm, x_in, s0)
        l4n = l4n_in.copy()
        to_solve = set([i for i in range(max(self.fixed_horizon-1,0), n-1) if l4n_in[i] >= self.l4n_threshold])
        unsolvable = set()
        # print("in: ", l4n_in[self.fixed_horizon-1:])c
        c = 0
        while to_solve:
            c+=1
            for t in to_solve:
                if l4n[t] < self.l4n_threshold:
                    continue
                c, d = rpm["c"][t] + s0, rpm["d"][t] + s0 
                a, b = dpm["a"][t], dpm["b"][t]
                if d < a:
                    unsolvable.add(t) 
                    continue 
                x_star = round(((b - a) * c + b * (d - c)) / (b - a + d - c))
                nl4_star = self.risk_manager.l4n(a, b, c, d, x_star)
                if nl4_star < self.l4n_threshold:
                    alpha = math.ceil(b - self.l4n_threshold * (b - a))
                    beta = math.floor(c + self.l4n_threshold * (d - c))
                    print("alpha: ", alpha , "beta: ", beta, "x*: ", x_star, "x_t: ", x[t])
                    if x[t] <= alpha:
                        x[t] = min(alpha + 1, x[t+1])
                        if x[t] == x[t+1] and t + 1 not in to_solve:
                            unsolvable.add(t)
                            continue
                    elif x[t] >= beta:
                        x[t] = max(beta - 1, x[t-1])
                        if x[t] == x[t-1] and t - 1 not in to_solve:
                            unsolvable.add(t)
                            continue
                    unsolvable.add(t)
                else:
                    unsolvable.add(t)
                    x[t] = self.findBest(x, x_star, t, to_solve, unsolvable)
            l4n = self.risk_manager.getL4Necessity(rpm, dpm, x, s0)
            to_solve = set([i for i in range(max(self.fixed_horizon-1,0), n-1) if l4n[i] >= self.l4n_threshold]) - unsolvable
        # print("out: ", [round(v, 3) for v in l4n[self.fixed_horizon-1:]])
        # print("**************************** fin algo ***********************************")
        if self.risk_manager.getSeverity(l4n) > self.risk_manager.getSeverity(l4n_in):
            raise Exception("Incorrect solution")
        return x

    def dispatchWithNetSupply(self, pa, supply_ratio, x, a, p):
        n = len(x)
        res = pa[:self.fixed_horizon] + [None for _ in range(self.fixed_horizon, n)]
        for t in range(self.fixed_horizon, n):
            res[t] = max(round(((x[t]+1) * supply_ratio[a][p][t])), 0)
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
        data = model.getSnapShot()
        pa = data["pa_product"]
        pa_aff = model.cdc_supply_plan
        reception = data["reception"]
        demand = data["demand"]
        initial_stock = data["initial_stock"]
        supply_ratio = model.pa_cdc.supply_ratio
        n = self.real_horizon
        decum_x_tot_out = {}
        decum_x_out = {a: {p: None for p in self.affiliate_products[a]} for a in self.affiliate_name}
        print("###########################################################")
        print("Week: ", model.week)
        for p in self.products:
            # get product inputs
            x_in = list(utils.accumu(pa[p][:n]))
            s0 = initial_stock[p]
            # calculate possibility models
            rpm = self.risk_manager.getRpm(reception, p)
            aff_dpm = self.risk_manager.getDpm(demand, p)
            # get dpm / product, sum over afiiliate
            params = ["a", "b", "c", "d"]
            dpm = {param: [sum([aff_dpm[a][param][t] for a in aff_dpm]) for t in range(n)] for param in params}
            print("              *************                         ")
            print("Product: ", p)
            for param, vals in dpm.items():
                print(param, ": ", vals)
            print("----------------------------------------")
            for param, vals in rpm.items():
                print(param, ": ", vals)
            # smoothing
            # print("************************** algo **********************************")
            # print("Week: ", model.week)
            x_out_product = self.filter(rpm, dpm, s0, x_in)
            self.validateOutput(x_in, x_out_product)
            # decumlate
            decum_x_tot_out[p] = utils.diff(x_out_product) + pa[p][n:]
            # dispatch
            for a in self.itProductAff(p):
                decum_x_out[a][p] = self.dispatchWithNetSupply(pa_aff[a][p], supply_ratio, decum_x_tot_out[p], a, p)

            # # repatch
            # decu_product_x = self.sumOverAffiliate(decum_x_out, p, self.horizon)
            # # recumu    
            # product_x = list(utils.accumu(decu_product_x[:n]))
            # l4n_out = self.risk_manager.getL4Necessity(rpm, dpm, product_x, s0)
            # l4n_in = self.risk_manager.getL4Necessity(rpm, dpm, x_in, s0)
            # g_out = self.risk_manager.getSeverity(l4n_out)
            # g_in = self.risk_manager.getSeverity(l4n_in)
            # if g_out > g_in:
            #     print([i -j for i, j in zip(decum_x_tot_out[p], decu_product_x)])
            #     print(l4n_in)
            #     print(l4n_out)
            #     print(f"{g_out} > {g_in}")
            #     tot_supply_r = self.sumOverAffiliate(supply_ratio, p , self.horizon)
            #     print(tot_supply_r)
            #     raise Exception("Dispatching led to wrong x!")
            
        return decum_x_out



