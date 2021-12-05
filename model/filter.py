from . import Shared
from . import RiskManager, Model
from . import utils
import math

class SmoothingFilter(Shared):

    def __init__(self) -> None:
        super().__init__()
        self.params = self.settings["smoothing"]

    def validateOutput(self, x_in: list[int], x_out: list[int]):
        n = len(x_out)
        if n != len(x_in):
            raise Exception(f"Solution size {len(x_out)} != input size {len(x_in)}!")
        for t in range(1, n):
            if x_out[t] < x_out[t-1]:
                raise Exception(f"x_out[{t}] = {x_out[t]} < x_out[{t-1}] = {x_out[t-1]}!")
        # if x_out[n-1] != x_in[n-1]:
        #     raise Exception("Didn't conserve same total quantity!")

    def smooth(self, rpm: dict[str, list[int]], dpm: dict[str, list[int]], x_in: list[int]):
        n = len(x_in)
        x = x_in.copy()
        l4n_in = RiskManager.getL4Necessity(rpm, dpm, x_in)
        l4n = l4n_in.copy()
        to_solve = set([i for i in range(self.params["range"]["start"], self.params["range"]["end"]) if l4n_in[i] >= self.l4n_threshold])
        unsolvable = set()
        while to_solve:
            for t in to_solve:
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

                if x[t] < x_star:
                    if t+1 < n:
                        x[t] = min(x_star, x[t+1])
                        if x[t] == x[t+1] and t + 1 not in to_solve:
                            unsolvable.add(t)
                    else:
                        x[t] = x_star

                else:
                    x[t] = max(x_star, x[t-1]) if t-1 >= 0 else x_star
                    if x[t] == x[t-1] and t - 1 not in to_solve:
                        unsolvable.add(t)

            l4n = RiskManager.getL4Necessity(rpm, dpm, x)
            to_solve = set([i for i in range(self.params["range"]["start"], self.params["range"]["end"]) if l4n[i] >= self.l4n_threshold]) - unsolvable
        self.validateOutput(x_in, x)
        return x