from io import RawIOBase
import json
from risk_manager import RiskManager
from model.model import Model
from model import utils
from cvxopt import solvers, matrix

def solveProblem(risk_m: RiskManager, rpm, dpm, s0, x_in):
    n = risk_m.horizon
    def F(x=None, z=None):
        if x is None: return 0, matrix(1., (n,1))
        if min(x) < 0.0 or max(x) > x_in[-1]: return None
        l4n = risk_m.getL4Necessity(rpm, dpm, x, s0) # N1, N2, ... ,Nn
        f = sum(l4n)
        gradient = [1.0 * risk_m.l4nDiff(rpm, dpm, s0, x, t) for t in range(n)] # diffN1, diffN2, ... ,diffNn
        print(gradient)
        Df = matrix(gradient).T
        if z is None: return f, Df
        H = matrix(0.0, (n,n)) # On
        return f, Df, H
    G = matrix([[0.] * i + [1., -1.] + [0.] * (n-2-i) for i in range(n-1)] + [[0] * (n-1) + [-1.]]).T # x(t) - x(t+1) <= 0
    h = matrix(-10., (n, 1))
    A = matrix([[0.] * (n-1) + [1.]]).T
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
    x = list(utils.accumu(pa[product]))[:risk_manager.horizon]
    r = list(utils.accumu(reception[product]))[:risk_manager.horizon]
    d = demand
    s0 = initial_stock[product]

    rpm = risk_manager.getRpm(r, product)
    dpm = risk_manager.getDpm(d, product)
    print("max demand B: ", max(dpm["b"]), "total pa = ", x[-1], "diff = ", x[-1] - max(dpm["b"]))
    
    # l4n = risk_manager.getL4Necessity(rpm, dpm, x, s0)
    # print(l4n)
    # raise

    G_in = risk_manager.getG(rpm, dpm, s0, x)
    G_out = G_in
    print(f"Gravity of {product} at week {week} is : ", G_in)
    if G_in > 0.5:
        l4n = risk_manager.getL4Necessity(rpm, dpm, x, s0)
        print("Input x: ", x)
        print("L4 necessity(xt): ", l4n)
        l4n_of_total = l4n[n-1]
        if l4n_of_total > 0.5:
            print(f"L4 necessity of total quantity is > {l4n_of_total}, cannot reduce G")
        else:
            print("Trying to reduce gravity for product: ", product)
            x = solveProblem(risk_manager, rpm, dpm, s0, x)
            G_out = risk_manager.getG(rpm, dpm, s0, x)
            l4n = risk_manager.getL4Necessity(rpm, dpm, x, s0)
            print("Output x: ", x)
            print("output L4 necessity(xt): ", l4n)
            print("G after strat: ", G_out)
    return G_in, G_out


def main():
    model = Model("simu_inputs/global_input.json")
    risk_manager = RiskManager(model)
    risk_manager.loadDModel("uncertainty_models/UMCDF_I2.xlsx")
    risk_manager.loadRModel("uncertainty_models/UMCRF_I1.xlsx")
    week = 5
    G_in, G_out = applyStrat(risk_manager, week, "P3")
if __name__ == "__main__":
    main()



