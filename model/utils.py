import re
import json
import math
import random
import numpy as np 


def getMean(q):
    size = len(q)
    return sum(q) / size

def var(q, m):
    size = len(q)
    sigma = sum([(q[t] - m)**2 for t in range(size)]) / size
    var = math.sqrt(sigma)
    return var

def getSigma(q, m):
    size = len(q)
    sigma = sum([(q[t] - m)**2 for t in range(size)]) / size
    return sigma

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
    print(format_row.format(name, *[round(x, 2) for x in q]))

def showModel(model):
    for k, v in model.items():
        show(k, v)
        
def randQ(size_q, q0):
    return np.random.poisson(q0, size_q)

def genUCM(n, model_args):
    params = ["a", "b", "c", "d"]
    model = {param: [] for param in params}
    model["RefWeek"] = []
    s = 0
    for part in model_args:
        size = part["size"]
        for param in params:
            model[param] += [part[param]] * size
        model["RefWeek"] += [s + 1] * size
        s += size
    return model

def getPDist(cq, model: dict):
    a, b, c, d, rw = model.values()
    t0 = [rw-1 for rw in rw]
    size = len(t0)
    f = [cq[t] - cq[t0-1] if t0-1> 0 else cq[t] for t,t0 in zip(range(size), t0)]
    A = [round(cpv + f * a) for cpv, f, a in zip(cq, f, a)]
    B = [round(cpv + f * b) for cpv, f, b in zip(cq, f, b)]
    C = [round(cpv + f * c) for cpv, f, c in zip(cq, f, c)]
    D = [round(cpv + f * d) for cpv, f, d in zip(cq, f, d)]
    return {param: dist for param, dist in zip(["A", "B", "C", "D"], [A, B, C, D])}

def pickRand(a, b, c, d):
    alpha = random.random()
    x1 = round(a + alpha * (b - a))
    x2 = round(d - alpha * (d - c))
    return x1 if random.random() < 0.5 else x2
    
def genRandCQ(model: dict, q: list):
    cqpm = getPDist(q, model)
    n = len(q)
    cres = [0 for _ in range(n)]
    A, B, C, D = cqpm.values()
    for t in range(n):
        rand_q = pickRand(A[t], B[t], C[t], D[t])
        cres[t] = max(rand_q, cres[t-1] if t>0 else 0)
    return cres

def genRandCQHist(size_h, size_q, ucm, q0):
    hist = [None] * size_h
    cq_ref = list(accumu(randQ(size_q + size_h, q0)))
    for w in range(size_h):
        hist[w] = genRandCQ(ucm, cq_ref[w:w + size_q])
    return hist 

def getDiffHist(cq_hist):
    q_size = len(cq_hist[0])
    res = [[None] * q_size] * (q_size -1)
    for t in range(q_size - 1, 2 * q_size - 1):
        for k in range(q_size - 1):
            y = t - k
            res[k][t - (q_size - 1)] = cq_hist[y][k] - cq_hist[y-1][k+1]
    return res

def getMeanVarDiffHist(cqdh):
    nrows = len(cqdh)
    mean_ = 0
    for w in range(nrows):
        mean_ += getMean(cqdh[w])
    mean_ /= nrows
    sigma_ = 0
    for w in range(nrows):
        sigma_ += getSigma(cqdh[w], mean_)
    var = math.sqrt(sigma_ / nrows)
    return mean_, var
        

        
        
        
        
    