from . import Shared
from . import RiskManager

class SmoothingFilter(Shared):

    def __init__(self) -> None:
        super().__init__()
        self.range = self.settings["smoothing"]["range"]
        self.optimisme = self.settings["smoothing"]["optimisme"]

    def validateOutput(self, x_in: list[int], x_out: list[int]):
        n = len(x_out)
        if n != len(x_in):
            raise Exception(f"Solution size {len(x_out)} != input size {len(x_in)}!")
        for t in range(1, n):
            if x_out[t] < x_out[t-1]:
                print(x_out)
                raise Exception(f"x_out[{t}] = {x_out[t]} < x_out[{t-1}] = {x_out[t-1]}!")
    
    def findFirstSolvable(self, x, unsolvable, idx, start, end):
        for j in range(idx, start, -1):
            if j not in unsolvable:
                return x[j]
        for j in range(idx, end):
            if j not in unsolvable:
                return x[j]
        return x[idx]
    
    def fixBounds(self, x):
        start = self.range["start"]
        end = self.range["end"]
        if start > 0:
            for t in range(start, end):
                x[t] = max(x[t-1], x[t])
        if end < self.real_horizon:
            for t in range(end-1, start, -1):
                x[t] = min(x[t], x[t+1])
    
    def smooth(self, rpm: dict[str, list[int]], dpm: dict[str, list[int]], x_in: list[int]):
        x = x_in.copy()
        start = self.range["start"]
        end = self.range["end"]
        unsolvable = set()
        for t in range(start, end):
            c, d = rpm["c"][t], rpm["d"][t] 
            a, b = dpm["a"][t], dpm["b"][t]
            l4n_min = RiskManager.getMinL4n(a, b, c, d)
            if l4n_min >= self.l4n_threshold:
                unsolvable.add(t) 
                continue
            x1, x2 = RiskManager.getL4nAlphaBound(self.l4n_threshold, a, b, c, d)
            u = 1
            x[t] = round(u * x1 + (1 - u) * x2)
        for idx in unsolvable:
            x[idx] = self.findFirstSolvable(x, unsolvable, idx, start, end)
        for t in range(start, self.real_horizon):
            x[t] = max(x[t-1], x[t])
        self.validateOutput(x_in, x)
        return x