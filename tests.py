from model import utils
import numpy as np
import math
import random 


def testVariance():
    q0 = 200
    hist_size = 40
    q_size = 20
    a = -0.5 
    b = -0.25
    c = 0.25
    d = 0.5
    model_args = [
        {
            "size": q_size//2,
            "a": a,
            "b": b,
            "c": c,
            "d": d
         },
        {
            "size": q_size//2,
            "a": a/2,
            "b": b/2,
            "c": c/2,
            "d": d/2
         }
    ]
    ucm = utils.genUCM(q_size, model_args)
    print("Model: ")
    utils.showModel(ucm)
    print("*" * 7 * (q_size + 1))
    print("Diff history: ")
    cq_hist = utils.genRandCQHist(hist_size, q_size, ucm, q0)
    cqdh = utils.getDiffHist(cq_hist)
    for i, l in enumerate(cqdh):
       utils.show(f"W{i}", l)
    print("=" * 7 * (q_size + 1))
    m, v = utils.getMeanVarDiffHist(cqdh)
    utils.show("mean", [m])
    utils.show("var", [v])
    utils.show("nvar", [abs(v/m)])
    
    
if __name__ == "__main__":
    testVariance()

    