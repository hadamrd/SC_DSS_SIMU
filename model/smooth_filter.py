from .risk_manager import RiskManager
from .model import Model
from . import utils


class SmoothFilter:

    def __init__(self, alpha, fixed_horizon) -> None:
        self.alpha = alpha
        self.fix_hor = fixed_horizon

    def validateOutput(self, x_in, x_out):
        n = len(x_out)
        if n != len(x_in):
            raise Exception(f"Solution size {len(x_out)} != input size {len(x_in)}!")
        for t in range(n-1):
            if x_out[t] > x_out[t+1]:
                raise Exception(f"x_out[{t}] = {x_out[t]} > x_out[{t+1}] = {x_out[t+1]}!")
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
        while solved | unsolvable != to_solve:
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
        return x

    def dispatch(self, risk_m: RiskManager, x: dict):
        daffpm = risk_m.d_aff_model
        res = {a: {p: [None for _ in range(risk_m.horizon)] for p in daffpm[a]} for a in daffpm}
        for a in daffpm:
            for p in daffpm[a]:
                for t in range(risk_m.horizon):
                    tot_dem = sum([daffpm[a][p]["b"][t] for a in daffpm if p in daffpm[a]])
                    res[a][p][t] = x[p][t] * daffpm[a][p]["b"][t] / tot_dem if tot_dem != 0 else 0
        return res

    def run(self, risk_manager: RiskManager, model: Model) -> dict[str, dict[str, list[int]]]:
        data = model.getCurrState()
        pa = data["pa"]
        reception = data["reception"]
        demand = data["demand"]
        initial_stock = data["initial_stock"]
        n = risk_manager.horizon
        x_out = {}
        for product in pa:
            # get product inputs
            x_in = list(utils.accumu(pa[product]))[:n]
            r = list(utils.accumu(reception[product]))[:n]
            s0 = initial_stock[product]
            # calculate possibility models
            rpm = risk_manager.getRpm(r, product)
            dpm = risk_manager.getDpm(demand, product)
            # smoothing
            x_out[product] = self.filter(risk_manager, rpm, dpm, s0, x_in)
            self.validateOutput(x_in, x_out[product])
        return self.dispatch(risk_manager, x_out)



if __name__ == "__main__":
    pass


