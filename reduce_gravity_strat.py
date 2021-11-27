import json
from model.risk_manager import RiskManager
from model.model import Model
from model import utils

def validateSolution(x_in, x_out):
    n = len(x_out)
    if n != len(x_in):
        raise Exception("Solution and x in must have same size!")
    for t in range(n-1):
        if x_out[t] > x_out[t+1]:
            raise Exception(f"x_out[{t}] = {x_out[t]} > x_out[{t+1}] = {x_out[t+1]}!")
    if x_out[n-1] != x_in[n-1]:
        raise Exception("Didn't conserve same total quantity!")

def solveProblem(risk_m: RiskManager, rpm, dpm, s0, x_in):
    n = risk_m.horizon
    x_out = x_in.copy()
    for t in range(n-1):
        if x_out[t] < dpm["b"][t]:
            x_out[t] = dpm["b"][t]
        elif x_out[t] > rpm["c"][t] + s0:
            x_out[t] = rpm["c"][t] + s0
    return x_out

def applyReduceGraviteStrat(risk_manager: RiskManager, product, data):
    pa = data["pa"]
    reception = data["reception"]
    demand = data["demand"]
    initial_stock = data["initial_stock"]

    # get product inputs
    n = risk_manager.horizon
    x_in = list(utils.accumu(pa[product]))[:risk_manager.horizon]
    r = list(utils.accumu(reception[product]))[:risk_manager.horizon]
    d = demand
    s0 = initial_stock[product]

    # calculate possibility models
    rpm = risk_manager.getRpm(r, product)
    dpm = risk_manager.getDpm(d, product)

    # calculate L4 necessity and G
    l4n_in = risk_manager.getL4Necessity(rpm, dpm, x_in, s0)
    G_in = max(l4n_in)
    G_out = G_in
    x_out = x_in
    l4n_out = l4n_in
    solvable = True

    if l4n_in[n-1] > 0.5:
        # print(f"for week {week}, product {product}, L4 necessity of total Q is is {l4n_in[n-1]}, cannot reduce G")
        solvable = False

    for t in range(n):
        if rpm["d"][t] + s0 < dpm["a"][t]:
            # print(f"for week {week}, product {product}, possible demand exceeds possible reception + stock at periot {t}!")
            solvable = False

    if solvable and G_in > 0.5:
        x_out = solveProblem(risk_manager, rpm, dpm, s0, x_in)
        l4n_out = risk_manager.getL4Necessity(rpm, dpm, x_out, s0)
        G_out = max(l4n_out)
        if G_out > 0.5:
            print("Couldn't solve the seemingly solvable problem : ")
            print("max(d_A): ", max(dpm["a"]), ", max(d_B): ", max(dpm["b"]), ", total(x): ", x_in[-1], ", min(r_A) + s0: ", min(rpm["a"]) + s0)
            print("Input X : ", x_in)
            print("Input L4_necessity : ", l4n_in)
            print(f"Input G : ", G_in)
            for t in range(n):
              print("a: ", dpm["a"][t], ", b: ", dpm["b"][t], ", x: ", x_in[t], ", cR: ", rpm["c"][t] + s0, ", dR: ", rpm["d"][t] + s0,  ", necessity: ", l4n_in[t])
            print("Output X: ", x_out)
            print("Output L4_necessity : ", l4n_out)
            print("Output G : ", G_out)
        validateSolution(x_in, x_out)

    return x_in, x_out, l4n_in, l4n_out, G_in, G_out, solvable


def main():
    model = Model("simu_inputs/global_input.json")
    risk_manager = RiskManager(model)
    risk_manager.loadDModel("uncertainty_models/UMCDF_I2.xlsx")
    risk_manager.loadRModel("uncertainty_models/UMCRF_I1.xlsx")
    tot = 0
    solved = 0
    unsolvable = 0
    for week in range(2, 20):
        with open(f"simu_history/state_S{week}.json") as fp:
            data = json.load(fp)
        for product in model.products:
            print(f"################# Processing week {week}, product {product} ###################################")
            x_in, x_out, l4n_in, l4n_out, G_in, G_out, solvable = applyReduceGraviteStrat(risk_manager, product, data)
            print("x_in: ", x_in)
            print("l4n_in: ", l4n_in)
            print("---------------------------------------------------------")
            print("x_out: ", x_out)
            print("l4n_out: ", l4n_out)
            if G_in > 0.5:
                tot += 1
                if G_out < 0.5:
                    solved += 1
            if not solvable:
                unsolvable += 1
    print("################           Finished       ##############################")
    print(f"performance score : {100 * solved / (tot - unsolvable)}%")


if __name__ == "__main__":
    main()



