import re
import matplotlib.pyplot as plt


def accumu(lis, q0=0):
    total = q0
    for v in lis:
        total += v
        yield total

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

def plotSamples(f, min_ax, max_ax, nbr_ech):
    min_ax *= (1 - 1/10)
    max_ax *= (1 + 1/10)
    ax = linspace(min_ax, max_ax, nbr_ech)
    y = [f(x) for x in ax]
    plt.plot(ax, y)

if __name__ == "__main__":
    pass
    