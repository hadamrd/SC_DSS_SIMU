import json
from risk_manager import RiskManager
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
    for t in range(n-1):
        if x_in[t] < dpm["b"][t]:
            x_in[t] = dpm["b"][t]
        elif x_in[t] > rpm["c"][t] + s0:
            x_in[t] = rpm["c"][t] + s0
    return x_in

def applyStrat(risk_manager: RiskManager, week, product, data):
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

    if l4n_in[n-1] > 0.5:
        print(f"for week {week}, product {product}, L4 necessity of total Q is is {l4n_in[n-1]}, cannot reduce G")
        return G_in, G_out, False

    for t in range(n):
        if rpm["d"][t] + s0 < dpm["a"][t]:
            print(f"for week {week}, product {product}, possible demand exceeds possible reception + stock at periot {t}!")
            return G_in, G_out, False

    if G_in > 0.5:
        x_out = solveProblem(risk_manager, rpm, dpm, s0, x_in)
        l4n_out = risk_manager.getL4Necessity(rpm, dpm, x_out, s0)
        G_out = max(l4n_out)
        if G_out > 0.5:
            print(f"################# Processing week {week}, product {product} ###################################")
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
        with open(f"simu_history/state_S{week}.json") as fp:
            data = json.load(fp)
        for p in model.products:
            G_in, G_out, solvable = applyStrat(risk_manager, week, p, data)  
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



