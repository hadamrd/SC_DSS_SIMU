import re
import matplotlib.pyplot as plt


def accumu(lis):
    total = 0
    for v in lis:
        total += v
        yield total

def readSubRow(sheet, row, start_col, length):
    return [sheet.cell(row, start_col + t).value for t in range(length)]

def diff(lis):
    n = len(lis)
    return [list[0]] + [lis[t] - lis[t-1] for t in range(1, n)]
    
def linspace(min, max, nbr_ech):
    return [min + (max-min) * (k / nbr_ech) for k in range(nbr_ech+1)]

def affineY(a, b, x):
    if a <= x <= b:
        return 1 if x == a == b else (x - a) / (b - a)
    elif x > b:
        return 1
    elif x < a:
        return 0

def affineDy(a, b, x):
    if x == a == b:
        return 0
    if a < x < b:
        return 1 / (b - a)
    elif x < a:
        return -0.1
    elif x > b:
        return 0  

def readRefWeekRow(sheet, row, start_col, horizon):
        string_ref_weeks = readSubRow(sheet, row, start_col, horizon)
        ref_weeks = list(map(int, [re.match(".*W(\d+).*", rw).group(1) for rw in string_ref_weeks]))
        return ref_weeks

def l4n(cR, dR, aD, bD, x):
    if aD > dR:
        return 1
    elif cR >= bD:
        necessity = affineY(cR, dR, x) + 1 - affineY(aD, bD, x)
        # print(f"here: aD = {aD}, bD = {bD}, xt = {x}, cR = {cR}, dR = {dR} and necessity = {necessity}")
        return necessity
    elif cR < bD:
        x_star = ((bD - aD) * cR + bD * (dR - cR)) / (bD - aD + dR - cR)
        if x <= x_star :
            return 1 - affineY(aD, bD, x)
        elif x > x_star:
            return affineY(cR, dR, x)

def l4nDiff(cR, dR, aD, bD, x):
    if aD > dR:
        res = 0
    elif cR >= bD:
        return affineDy(cR, dR, x) - affineDy(aD, bD, x)
    elif cR < bD:
        x_star = ((bD - aD) * cR + bD * (dR - cR)) / (bD - aD + dR - cR)
        return -affineDy(aD, bD, x) if x <= x_star else affineDy(cR, dR, x)
    return res

def plotSamples(f, min_ax, max_ax, nbr_ech):
    min_ax *= (1 - 1/10)
    max_ax *= (1 + 1/10)
    ax = linspace(min_ax, max_ax, nbr_ech)
    y = [f(x) for x in ax]
    plt.plot(ax, y)

if __name__ == "__main__":
    # first case aD <= dR but cR >= bD
    # aD = 100
    # bD = aD + 50
    # cR = bD + 50
    # dR = cR + 50

    # second case aD <= dR but cR < bD
    # aD = 100
    # bD = aD + 100
    # cR = bD - 50
    # dR = cR + 200

    # weird case
    aD=bD=0
    cR=dR=371

    nbr_ech = 1000
    print("aD: ", aD, "cR: ", cR, "bD: ", bD, "dR: ", dR)
    # x_star = ((bD - aD) * cR + bD * (dR - cR)) / (bD - aD + dR - cR)
    # print("x_star: ", x_star)
    f = lambda x: l4n(cR, dR, aD, bD, x)

    # min_df_val = - 1 / (bD - aD)
    # max_df_val = 1 / (dR - cR)
    # nor_df = 1 / max(abs(min_df_val), abs(max_df_val))
    df = lambda x: 10 * l4nDiff(cR, dR, aD, bD, x)

    min_ax = min(cR, dR, aD, bD)
    max_ax = max(cR, dR, aD, bD)
    plotSamples(f, min_ax, max_ax, nbr_ech)
    plotSamples(df, min_ax, max_ax, nbr_ech)
    plt.show()

# def sampleTrapeze(a, b, c, d, nbr_ech):
#     min = a - a/20
#     max = d + d/20
#     ax = linspace(min, max, nbr_ech)
#     y = [self.tpzd(a, b, c, d, x) for x in ax]
#     return ax, y

# def sampleL1Possibility(self, rpm, s0, t, nbr_ech):
#     a, b, d = rpm["a"][t], rpm["b"][t], rpm["d"][t]
#     min = a - a/20
#     max = d + d/20
#     ax = linspace(min, max, nbr_ech)
#     l1_p = [l1p(a, b, s0, x) for x in ax]
#     return ax, l1_p

# def sampleL2Possibility(self, dpm, t, nbr_ech):
#     a, c, d = dpm["a"][t], dpm["c"][t], dpm["d"][t]
#     min = a - a/20
#     max = d + d/20
#     ax = utils.linspace(min, max, nbr_ech)
#     l2_p = [self.l2p(c, d, x) for x in ax]
#     return ax, l2_p

# def sampleL4Possibility(self, dpm, rpm, s0, t, nbr_ech):
#     ax_l2, l2_p = self.sampleL2Possibility(dpm, t, nbr_ech)
#     ax_l1, l1_p = self.sampleL1Possibility(rpm, s0, t, nbr_ech)
#     min_ax = min(ax_l1[0], ax_l2[0])
#     max_ax = max(ax_l1[-1], ax_l2[-1])
#     ax = linspace(min_ax, max_ax, nbr_ech)
#     l4_p = [max(l1, l2) for l2, l1 in zip(l1_p, l2_p)]
#     return ax, l4_p

# def tpzd(self, a, b, c, d, x):
#     if x < a:
#         return 0
#     elif x < b:
#         return (x - a) / (b - a)
#     elif x < c:
#         return 1
#     elif x < d:
#         return (d - x) / (d - c)
#     else:
#         return 0

# def sumOverAffiliate(self, q, p, param):
#     return [sum([q[a][p][param][t] for a in q if p in q[a]]) for t in range(self.horizon)]