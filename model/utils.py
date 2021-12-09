import re
import json
import math
import random
import numpy as np 


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

def diff(lis):
    n = len(lis)
    return [lis[0]] + [lis[t] - lis[t-1] for t in range(1, n)]
    
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

def genUCM(model_args):
    params = ["a", "b", "c", "d"]
    model = {param: [] for param in params}
    model["RefWeek"] = []
    s = 0
    for part in model_args:
        size = part["size"]
        for param in params:
            model[param] += [part[param]] * size
        model["RefWeek"] += [s] * size
        s += size
    return model

def getPDist(cq, model: dict):
    a, b, c, d, rw = model.values()
    size = len(rw)
    f = [cq[t] - cq[t0 - 1] if t0 > 0 else cq[t] for t, t0 in zip(range(size), rw)]
    return {
        "A": [round(cpv + f * a) for cpv, f, a in zip(cq, f, a)],
        "B": [round(cpv + f * b) for cpv, f, b in zip(cq, f, b)],
        "C": [round(cpv + f * c) for cpv, f, c in zip(cq, f, c)],
        "D": [round(cpv + f * d) for cpv, f, d in zip(cq, f, d)]
    }

def pickRand(a, b, c, d):
    alpha = random.random()
    x1 = round(a + alpha * (b - a))
    x2 = round(d - alpha * (d - c))
    return x1 if random.random() < 0.5 else x2
    
def genRandCQ(ucm: dict, q: list):
    cqpm = getPDist(q, ucm)
    n = len(q)
    cres = [0 for _ in range(n)]
    A, B, C, D = cqpm.values()
    for t in range(n):
        rand_q = pickRand(A[t], B[t], C[t], D[t])
        cres[t] = max(rand_q, cres[t-1] if t>0 else 0)
    return cres

def genRandCQHist(size, ucm, q0):
    size_q = len(ucm["a"])
    hist = [None] * size
    cq_ref = list(accumu(randQ(size_q + size, q0)))
    for w in range(size):
        hist[w] = genRandCQ(ucm, cq_ref[w:w + size_q])
    return hist 

def genRandQHist(size, ucm, q0):
    res = [None] * size
    chist = genRandCQHist(size, ucm, q0)
    for w in range(size):
        res[w] = diff(chist[w]) 
        res[w][0] -= res[w-1][0] if w > 0 else 0
    return res
    


        
        
        
        
    