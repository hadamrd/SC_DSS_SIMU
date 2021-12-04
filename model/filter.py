from . import Shared
from . import RiskManager, Model
from . import utils
import math

class SmoothingFilter(Shared):

    def __init__(self) -> None:
        super().__init__()

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
        l4n_in = RiskManager.getL4Necessity(rpm, dpm, x_in)
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
                    x_star = round((a + b) / 2)
                else:
                    x_star = round(((b - a) * c + b * (d - c)) / (b - a + d - c))
                nl4_star = RiskManager.l4n(a, b, c, d, x_star)
                if nl4_star >= self.l4n_threshold:
                    unsolvable.add(t)
                x[t] = self.findBest(x, x_star, t, to_solve, unsolvable)
            l4n = RiskManager.getL4Necessity(rpm, dpm, x)
            to_solve = set([i for i in range(max(self.fixed_horizon-1,0), n-1) if l4n[i] >= self.l4n_threshold]) - unsolvable
        self.validateOutput(x_in, x)
        return x