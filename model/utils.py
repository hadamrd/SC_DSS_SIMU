import re
import json
import math
import random
import numpy as np 
from . import utils 


def writeRow(sh, row: int, start_col: int, lis: list):
    for t, v in enumerate(lis):
        sh.cell(row, start_col + t).value = v

def accumu(lis, q0=0):
    total = q0
    for v in lis:
        total += v
        yield total

def saveToFile(data: dict, dst_f: str):
    with open(dst_f, 'w') as fp:
        json.dump(data, fp)

def readSubRow(sheet, row, start_col, length):
    return [sheet.cell(row, start_col + t).value for t in range(length)]

def diff(lis, ref=0):
    n = len(lis)
    return [lis[0]-ref] + [lis[t] - lis[t-1] for t in range(1, n)]
    
def linspace(min, max, nbr_ech):
    return [min + (max-min) * (k / nbr_ech) for k in range(nbr_ech+1)]

def affineY(a, b, x):
    if a <= x <= b:
        return 1 if x == a == b else (x - a) / (b - a)
    elif x > b:
        return 1
    elif x < a:
        return 0

def readRefWeekRow(sheet, row, start_col, horizon):
    string_ref_weeks = readSubRow(sheet, row, start_col, horizon)
    ref_weeks = list(map(int, [re.match(".*W(\d+).*", rw).group(1) for rw in string_ref_weeks]))
    return ref_weeks

def generateSamples(f, min_ax, max_ax, nbr_ech):
    min_ax *= (1 - 1/10)
    max_ax *= (1 + 1/10)
    ax = linspace(min_ax, max_ax, nbr_ech)
    y = [f(x) for x in ax]
    return ax, y

def replicateFile(src, dst):
    with open(src) as fp:
        src_d = json.load(fp)
    with open(dst, "w") as fp:
        json.dump(src_d, fp)

def show(name, q):
    format_row = "{:>7}" + "{:>7}" * len(q)
    print(format_row.format(name, *q))

def showModel(model):
    for k, v in model.items():
        if k not in ["RefWeek", "ModelType"]:
            show(k, [round(_, 2) for _ in v])
        else:
            show(k, v)
        
def randQ(size_q, q0):
    return np.random.poisson(q0, size_q)

def genUCM(model_args, model_type="I1"):
    params = ["a", "b", "c", "d"]
    model = {param: [] for param in params}
    model["RefWeek"] = []
    model["ModelType"] = []
    s = 0
    for part in model_args:
        size = part["size"]
        for param in params:
            model[param] += [part[param]] * size
        model["RefWeek"] += [s] * size
        model["ModelType"] += [model_type] * size
        s += size
    return model

def getFuzzyDist(prev_dist, cq, model, n, s0=0, k=0):
    params = ["a", "b", "c", "d"]
    dist = {param: [None] * n for param in params}
    for param in params:
        for t in range(n):
            t0 = model["RefWeek"][t] - 1
            model_type = model["ModelType"][t] 
            alpha_t = model[param][t]
            if prev_dist[param][0] is None:
                print(k, prev_dist[param])
            prev_param = dist[param][t-1] if t > 0 else prev_dist[param][0]
            F_t = cq[t+k] - cq[k+t0-1] if k + t0 - 1 > 0 else cq[t+k]
            if F_t < 0:
                raise Exception("F_t can't be negative")
            if model_type == "I1":
                F_t /= t - t0 + 1
            dist[param][t] = round(prev_param + F_t +(alpha_t * F_t ) + s0)
        validateCQ(dist[param])

    # for t in range(n):
    #     if t > 0:
    #         dist["a"][t] = max(dist["a"][t-1], dist["a"][t]) 
    #         dist["b"][t] = max(dist["b"][t-1], dist["b"][t]) 
    #     tr = n - 1 - t
    #     if tr < n - 1:
    #         dist["c"][tr] = min(dist["c"][tr], dist["c"][tr+1])
    #         dist["d"][tr] = min(dist["d"][tr], dist["d"][tr+1])

    for t in range(n):
        for i in range(3):
            if dist[params[i]][t] > dist[params[i+1]][t]:
                print("s\n")
                utils.showModel(dist)
                utils.showModel(model)
                raise Exception(f"When calculating distribution '{params[i+1]}' can't be smaller than '{params[i]}'!")

    return dist

def pickRand(a, b, c, d):
    alpha = random.random()
    x1 = round(a + alpha * (b - a))
    x2 = round(d - alpha * (d - c))
    if a == b == 0:
        return x2
    if c == d == 0:
        return x1
    return x1 if random.random() < 0.5 else x2

def genRandCQ(size, q0):
    return list(accumu(randQ(size, q0)))
    
def genRandCQFromUCM(prev_dist, ucm: dict, cq: list, w):
    n = len(ucm["a"])
    cqpm = getFuzzyDist(prev_dist, cq, ucm, n, k=w)
    cres = [0 for _ in range(n)]
    for t in range(n):
        rand_q = pickRand(cqpm["a"][t], cqpm["b"][t], cqpm["c"][t], cqpm["d"][t])
        cres[t] = max(rand_q, cres[t-1] if t > 0 else 0)
    utils.validateCQ(cres)
    return cres

def genRandCQHist(size, ucm, q0):
    size_q = len(ucm["a"])
    hist = [None] * size
    cq_ref = list(accumu(randQ(size_q + size, q0)))
    cqpm = {param: [0 for _ in range(size_q)] for param in ["a", "b", "c", "d"]}
    for w in range(size):
        hist[w] = [0 for _ in range(size_q)]
        cqpm = getFuzzyDist(cqpm, cq_ref, ucm, size_q, k=w)
        for t in range(size_q):
            rand_q = pickRand(cqpm["a"][t], cqpm["b"][t], cqpm["c"][t], cqpm["d"][t])
            hist[w][t] = max(rand_q, hist[w][t-1] if t > 0 else 0)
        utils.validateCQ(hist[w])
    return hist 

def genRandQHist(size, ucm, q0):
    res = [None] * size
    chist = genRandCQHist(size, ucm, q0)
    for w in range(size):
        res[w] = diff(chist[w])
        res[w][0] -= chist[w-1][0] if w > 0 else 0
        if res[w][0] < 0:
            print(res[w][0], chist[w-1][0])
            raise Exception("PV can't be negative!")
    return res
    
def validateCQ(cq):
    n = len(cq)
    for t in range(1, n):
        if cq[t] < cq[t-1]:
            print(cq)
            raise Exception(f"x_out[{t}] = {cq[t]} < x_out[{t-1}] = {cq[t-1]}!")

        
        
        
        
    