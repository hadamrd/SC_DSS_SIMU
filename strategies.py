from io import RawIOBase
import json
from risk_manager import RiskManager
from model.model import Model
from model import utils
from cvxopt import solvers, matrix

def solveProblem(risk_m: RiskManager, rpm, dpm, s0, x_in):
    n = risk_m.horizon
    for t in range(n-1):
        if x_in[t] < dpm["a"][t]:
            x_in[t] = dpm["b"][t]
        elif x_in[t] > rpm["d"][t] + s0:
            x_in[t] = rpm["c"][t] + s0
    def F(x=None, z=None):
        if x is None: return 0, matrix(list(map(float, x_in[:n])))
        if min(x) < 0.0: return None
        if not all(rpm["d"][t] + s0 < dpm["a"][t] or dpm["a"][t] <= x[t] <= rpm["d"][t] + s0 for t in range(n-1)): return None
        l4n = [risk_m.l4n(rpm, dpm, s0, x, t) for t in range(n)] # N1, N2, ... ,Nn
        f = 1. * sum(l4n)
        gradient = [1. * risk_m.l4nDiff(rpm, dpm, s0, x, t) for t in range(n)] # diffN1, diffN2, ... ,diffNn
        Df = matrix(gradient).T
        if z is None: return f, Df
        H = matrix(0.1, (n,n)) # On
        return f, Df, H
    G = matrix([[0.] * i + [1., -1.] + [0.] * (n-2-i) for i in range(n-1)] + [[0] * (n-1) + [-1.]]).T # x(t) - x(t+1) <= 0
    h = matrix(0., (n, 1))
    A = matrix([0.] * (n-1) + [1.]).T
    b = matrix([1. * x_in[-1]])
    options = {'show_progress': False}
    solutions = solvers.cp(F, G=G, h=h, A=A, b=b, options=options)
    return list(map(round, solutions['x']))

def applyStrat(risk_manager: RiskManager, week, product):
    print(f"############# Processing week {week} ##################")
    with open(f"simu_history/state_S{week}.json") as fp:
        data = json.load(fp)
    pa = data["pa"]
    reception = data["reception"]
    demand = data["demand"]
    initial_stock = data["initial_stock"]

    n = risk_manager.horizon
    x_in = list(utils.accumu(pa[product]))[:risk_manager.horizon]
    r = list(utils.accumu(reception[product]))[:risk_manager.horizon]
    d = demand
    s0 = initial_stock[product]

    rpm = risk_manager.getRpm(r, product)
    dpm = risk_manager.getDpm(d, product)
    print(f"max(d_B): ", max(dpm["b"]), ", max(d_A): ", max(dpm["a"]), ", total(x): ", x_in[-1], ", min(r_A) + s0: ", min(rpm["a"]) + s0)

    l4n_in = risk_manager.getL4Necessity(rpm, dpm, x_in, s0)

    # for t in range(n):
    #   print("a = ", dpm["a"][t], ", b = ", dpm["b"][t], ", x = ", x[t], ", cR = ", rpm["c"][t] + s0, ", dR = ", rpm["d"][t] + s0,  ", necessity =", l4n[t])
    
    G_in = max(l4n_in)
    G_out = G_in
    diffG = 0

    if x_in[-1] < max(dpm["a"]):
        print("total Q < possible (cum)demand at some period!")
        return G_in, G_out, False

    if l4n_in[n-1] > 0.5:
        print(f"L4 necessity of total Q is is {l4n_in[n-1]}, cannot reduce G")
        return G_in, G_out, False

    for t in range(n):
        if rpm["d"][t] + s0 < dpm["a"][t]:
            print(f"possible demand exceeds possible reception + stock_0 at periot {t}!")
            return G_in, G_out, False

    if G_in > 0.5:
        print("Input X : ", x_in)
        print("Input L4_necessity : ", l4n_in)
        print(f"Input G : ", G_in)

        print("Trying to reduce gravity for product: ", product)
        x_out = solveProblem(risk_manager, rpm, dpm, s0, x_in)
        l4n_out = risk_manager.getL4Necessity(rpm, dpm, x_in, s0)
        G_out = max(l4n_out)

        print("Output X: ", x_out)
        print("Output L4_necessity : ", l4n_out)
        print("Output G : ", G_out)

        # valdiate solution
        for t in range(n-1):
            if x_out[t] > x_out[t+1]:
                raise Exception(f"x_out[{t}] = {x_out[t]} > x_out[{t+1}] = {x_out[t+1]}:")

        if x_out[n-1] != x_in[n-1]:
            raise Exception("Didn't conserve same total quantity:")

        diffG = sum(l4n_in) - sum(l4n_out)
        if diffG < 0:
            print("Warning algo increased total G")
        
    return G_in, G_out, True


def main():
    model = Model("simu_inputs/global_input.json")
    risk_manager = RiskManager(model)
    risk_manager.loadDModel("uncertainty_models/UMCDF_I2.xlsx")
    risk_manager.loadRModel("uncertainty_models/UMCRF_I1.xlsx")
    tot = 0
    solved = 0
    unsolvable = 0
    for week in range(2, 20):
        for p in model.products:
            G_in, G_out, solvable = applyStrat(risk_manager, week, p)  
            if G_in > 0.5:
                tot += 1
                if G_out < 0.5:
                    solved += 1
            if not solvable:
                unsolvable += 1
    print("################           Finished     ##############################")
    print(f"performance score : {100 * solved / (tot - unsolvable)}%")
if __name__ == "__main__":
    main()



