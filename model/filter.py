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

    def smooth(self, rpm: dict[str, list[int]], dpm: dict[str, list[int]], x_in: list[int]):
        n = len(x_in)
        x = x_in.copy()
        l4n_in = self.risk_manager.getL4Necessity(rpm, dpm, x_in)
        l4n = l4n_in.copy()
        to_solve = set([i for i in range(max(self.fixed_horizon-1,0), n-1) if l4n_in[i] >= self.l4n_threshold])
        unsolvable = set()
        while to_solve:
            for t in to_solve:
                if l4n[t] < self.l4n_threshold:
                    continue
                c, d = rpm["c"][t], rpm["d"][t] 
                a, b = dpm["a"][t], dpm["b"][t]
                if d <= a:
                    unsolvable.add(t) 
                    continue
                if a == b and d == c:
                    x_star = (a + b) / 2
                else:
                    x_star = ((b - a) * c + b * (d - c)) / (b - a + d - c)
                nl4_star = self.risk_manager.l4n(a, b, c, d, x_star)
                if nl4_star >= self.l4n_threshold:
                    unsolvable.add(t)
                x[t] = self.findBest(x, x_star, t, to_solve, unsolvable)
            l4n = self.risk_manager.getL4Necessity(rpm, dpm, x)
            to_solve = set([i for i in range(max(self.fixed_horizon-1,0), n-1) if l4n[i] >= self.l4n_threshold]) - unsolvable
        self.validateOutput(x_in, x)
        if self.risk_manager.getSeverity(l4n) > self.risk_manager.getSeverity(l4n_in):
            raise Exception("Severity increased!")
        return x

    def run(self, model: Model, demand_ref, reception_ref) -> dict[str, dict[str, list[int]]]:
        data = model.getSnapShot()
        pa = data["pa_product"]
        pa_aff = model.cdc_supply_plan
        reception = data["reception"]
        demand = data["demand"]
        initial_stock = data["initial_stock"]
        
        n = self.real_horizon
        decum_x_tot_out = {}
        decum_x_out = {a: {p: None for p in self.affiliate_products[a]} for a in self.affiliate_name}
        print("###########################################################")
        for p in self.products:
            # get product inputs
            x_in = list(utils.accumu(pa[p][:n]))
            s0 = initial_stock[p]

            # calculate possibility distributions
            if self.pdp_dependency:
                rpm = self.risk_manager.getRpm(reception, p, s0)
            else:
                rpm = self.risk_manager.getRpm(reception_ref, p, s0)
            if self.ba_dependency:
                dpm = self.risk_manager.getDpm(demand, p)
            else:
                dpm = self.risk_manager.getDpm(demand_ref, p)

            # print distributions
            print("              *************              ")
            print("Product: ", p)
            print("Demand: ")
            for param, vals in dpm.items():
                print(param, ": ", vals)
            print("----------------------------------------")
            print("Reception: ")
            print("S0: ", s0)
            for param, vals in rpm.items():
                print(param, ": ", [v for v in vals])

            # smooth the pa pplan 
            x_out_product = self.smooth(rpm, dpm, x_in)
            
            # decumlate the plan
            decum_x_tot_out[p] = utils.diff(x_out_product) + pa[p][n:]

        # dispatch
        decum_x_out = self.dispatch(decum_x_tot_out, demand, pa_aff)
            
        return decum_x_out



