import math
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
    if a < x < b:
        return 1 / (b - a)
    else:
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
        return necessity
    elif cR < bD:
        x_star = ((bD - aD) * cR + bD * (dR - cR)) / (bD - aD + dR - cR)
        if x <= x_star :
            return 1 - affineY(aD, bD, x)
        elif x > x_star:
            return affineY(cR, dR, x)

def l4nDiff(c, d, a, b, x):
    if a > d:
        return 0
    elif c >= b:
        return affineDy(c, d, x) - affineDy(a, b, x)
    elif c < b:
        x_star = ((b - a) * c + b * (d - c)) / (b - a + d - c)
        return -affineDy(a, b, x) if x <= x_star else affineDy(c, d, x)

def plotSamples(f, min_ax, max_ax, nbr_ech):
    min_ax *= (1 - 1/10)
    max_ax *= (1 + 1/10)
    ax = linspace(min_ax, max_ax, nbr_ech)
    y = [f(x) for x in ax]
    plt.plot(ax, y)

if __name__ == "__main__":
    # first case aD <= dR but cR >= bD
    a = 100
    b = a + 50
    c = b + 50
    d = c + 50

    # second case aD <= dR but cR < bD
    # aD = 100
    # bD = aD + 100
    # cR = bD - 50
    # dR = cR + 200

    # weird case
    # aD=bD=0
    # cR=dR=371

    nbr_ech = 1000
    print("aD: ", a, "cR: ", c, "bD: ", b, "dR: ", d)
    # x_star = ((bD - aD) * cR + bD * (dR - cR)) / (bD - aD + dR - cR)
    # print("x_star: ", x_star)
    f = lambda x: l4n(c, d, a, b, x)


    df = lambda x: 10 * l4nDiff(c, d, a, b, x)

    def g(x):
        if x <= a:
            alpha = math.log(1 + 2 / (b + c))
            return 1 - math.exp(alpha * x / a)
        else:
            return df(x)
    
    def dh(x):
        eps = 1 - 0.3
        c3 = ((eps-1)/(a**2*(a**2-b**2)) + 1/(2*(b-a)*b**3) - 1/(b**4) + 1/(b**2*(a**2-b**2)))/(a**2-b**2)
        c2 = 1/b**4 - 1/(2*(b-a)*b**3) - 2*b**2*c3
        c1 = (eps-1)/a**2 - a**2*c2 -a**4*c3
        return 2*c1*x + 4*c2*x**3 + 6*c3*x**5
        

    min_ax = min(c, d, a, b)
    max_ax = max(c, d, a, b)
    plotSamples(f, a, d, nbr_ech)
    plotSamples(df, a, d, nbr_ech)
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