import re
import json
import math
import random
import numpy as np 
import logging

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


def getModelStr(model):
    res = "Model:\n"
    size = len(model['a'])
    format_row = "{:>7}" + "{:>7}" * size
    res += format_row.format("week", *[f"W{t}" for t in range(size)])
    for k, v in model.items():
        if k not in ["RefWeek", "ModelType"]:
            res += "\n" + format_row.format(k, *[round(_, 2) for _ in v])
        elif k == "RefWeek":
            res += "\n" + format_row.format("t0", *[_ - 1 for _ in v])
        elif k == "ModelType":
            res += "\n" + format_row.format("MT", *v)
    return res
    
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

def validateFuzzyCDist(fcdist):
    params = ["a", "b", "c", "d"]
    n = len(fcdist["a"])
    for param in params:
        try:
            validateCQ(fcdist[param])
        except Exception as e:
            print("Validation failed for param : ", param)
            raise e 
    for t in range(n):
        for i in range(3):
            if fcdist[params[i]][t] > fcdist[params[i+1]][t]:
                raise Exception(f"Dist param '{params[i+1]}' can't be smaller than '{params[i]}'!")

def getFuzzyDist(prev_dist, cq, model, n, s0=0, k=0):
    logging.debug("calcul fuzzy dist with:")
    log_msg = getModelStr(model)
    format_row = "{:>7}" + "{:>7}" * n
    log_msg += "\n"+ format_row.format("CQ", *cq[k:k+n])
    params = ["a", "b", "c", "d"]
    dist = {param: [None] * n for param in params}
    F = [None] * n
    model_type = model["ModelType"][0] 
    for t in range(n):
        t0 = model["RefWeek"][t] - 1
        F[t] = cq[t + k] - cq[k + t0 - 1] if k + t0 > 0 else cq[t + k]            
        if F[t] < 0:
            raise Exception("F_t can't be negative")
        if model_type == "I1":
            F[t] /= t - t0 + 1
    log_msg += "\n"+ format_row.format("F", *[round(_, 2) for _ in F])
    logging.debug(log_msg)
    for param in params:
        logging.debug("calculs fd for param: " + param)
        for t in range(n):
            t0 = model["RefWeek"][t] - 1
            alpha_t = model[param][t]
            prev_param = dist[param][t0 - 1] if t0 > 0 else prev_dist[param][0]
            dist[param][t] = math.floor(prev_param + (1 + alpha_t) * F[t] + s0)
            logging.debug(f"t: {t}, t0: {t0}, F(t): {F[t]}, {param.lower()}(t): {alpha_t}, {param.upper()}(t0-1): {prev_param} ===> {param.upper()}(t) = {param.upper()}(t0-1) + (1 + {param.lower()}(t)) * F(t) = {dist[param][t]}")
            if t > 0 and model_type == "I2" and dist[param][t] < dist[param][t-1]:
                raise Exception(f"While calculating cum dist for param {param}, got a non cumulated result!")
    logging.debug(getModelStr(dist))
    validateFuzzyCDist(dist)
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
    validateCQ(cres)
    return cres

def genRandCQHist(size, ucm, q0):
    size_q = len(ucm["a"])
    hist = [None] * size
    cq_ref = list(accumu(randQ(size_q + size, q0)))
    cqpm = {param: [0 for _ in range(size_q)] for param in ["a", "b", "c", "d"]}
    for w in range(size):
        logging.debug(f"Calcul Randomized CQ for week: {w}")
        cqpm = getFuzzyDist(cqpm, cq_ref, ucm, size_q, k=w)
        hist[w] = [0 for _ in range(size_q)]
        for t in range(size_q):
            rand_q = pickRand(cqpm["a"][t], cqpm["b"][t], cqpm["c"][t], cqpm["d"][t])
            hist[w][t] = max(rand_q, hist[w][t-1] if t > 0 else 0)
        validateCQ(hist[w])
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

        
        
        
        
    