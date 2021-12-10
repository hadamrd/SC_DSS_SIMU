from model import metrics, utils
import json 


def testVariance():
    q0 = 200
    hist_size = 40
    q_size = 24
    # generate and show uncertainty model
    ucm = utils.genUCM(model_args)
    print("Model: ")
    utils.showModel(ucm)
    
    print("*" * 7 * (q_size + 1))
    
    # calculate and show diff history
    print("Diff history: ")
    cq_hist = utils.genRandCQHist(hist_size, q_size, ucm, q0)
    cqdh = metrics.getDiffHist(cq_hist)
    for i, l in enumerate(cqdh):
       utils.show(f"W{i}", l)
       
    print("=" * 7 * (q_size + 1))
    
    # calculate and show mean and variance of diffs
    m, v = metrics.getMeanVarDiffHist(cqdh)
    utils.show("mean", [m])
    utils.show("var", [v])
    utils.show("nvar", [abs(v/m)])

def genUCMDR(ucmPv, pv0, r0, d0, du1, du2, ru1, ru2):
    size = len(ucmPv["a"])
    params = ["a", "b", "c", "d", "RefWeek"]
    ucmD = {param: [0] * size for param in params}
    ucmR = {param: [0] * size for param in params}
    ucmD["ModelType"] = ["I1"] * size
    ucmR["ModelType"] = ["I1"] * size
    dr0 = pv0 / d0
    rr0 = pv0 / r0
    for t in range(2, size):
        t0 = ucmPv["RefWeek"][t]
        rt = t / (t - t0) if t0 != t else 1
        ax, bx, cx, dx = ucmPv["a"][t], ucmPv["b"][t], ucmPv["c"][t], ucmPv["d"][t]
        
        ucmD["a"][t] = rt * (du1 * dr0 - 1) + du1 * dr0 * ax
        ucmD["b"][t] = (dr0 - 1) * rt + dr0 * (du2 * ax + (1 - du2) * bx)
        ucmD["c"][t] = 0
        ucmD["d"][t] = 0
        
        ucmR["d"][t] = rt * (ru1 * rr0 - 1) + ru1 * rr0 * dx
        ucmR["c"][t] = (rr0 - 1) * rt + rr0 * (ru2 * cx + (1 - ru2) * dx) 
        ucmR["a"][t] = 0
        ucmR["b"][t] = 0

        ucmD["RefWeek"][t] = ucmR["RefWeek"][t] = t0
    return ucmD, ucmR


if __name__ == "__main__":
    pv0 = d0 = r0 = 200
    hist_size = 40
    q_size = 24
    fh = 2
    
    # à la hausse
    model_args = [
        {"size": fh, "a": 0, "b": 0, "c": 0, "d": 0},
        {"size": (q_size-fh)//2, "a": 0, "b": 0, "c": 0.5, "d": 0.8},
        {"size": (q_size-fh)//2, "a": 0, "b": 0, "c": 0.25, "d": 0.4}
    ]

    # generate and show uncertainty model
    ucmPV = utils.genUCM(model_args)
    
    du1 = 0.5
    du2 = 0.5
    ru1 = 1.1
    ru2 = 0.5
    
    print("PV Model: ")
    utils.showModel(ucmPV)
    ucmD, ucmR = genUCMDR(ucmPV, pv0, r0, d0, du1, du2, ru1, ru2)
    
    print("*" * 7 * (q_size + 1))
    print("Reception model: ")
    utils.showModel(ucmR)
    
    print("*" * 7 * (q_size + 1))
    print("Demand model: ")
    utils.showModel(ucmD)
    
    with open("uncertainty_models/UMCPVF_I1.json", "w") as fp:
        json.dump({"france": {"P1": ucmPV}}, fp)
    
    with open("uncertainty_models/UMCDF_I1.json", "w") as fp:
        json.dump({"france": {"P1": ucmD}}, fp)
    
    with open("uncertainty_models/UMCRF_I1.json", "w") as fp:
        json.dump({"P1": ucmR}, fp)
        
    
    
    
    