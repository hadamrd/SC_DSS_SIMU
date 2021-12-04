
import openpyxl
import math
from model import history
from model.risk import RiskManager
from . import History, utils


def periodMean(Q_history: list[list[int]], t: int, fh: int):
    n = len(Q_history[0])
    res = 0
    for k in range(n):
        res += Q_history[t - k][k]
    return res / (n - fh + 1)

def getMeanAbsDiff(Q_history: list[list[int]], t: int, fh: int, p: str) -> float:
    n = len(Q_history[0])
    res = 0
    for k in range(n-1):
        y = t - k
        if y < n - fh:
            res += abs(Q_history[y][p][k] - Q_history[y-1][p][k+1])
    return res / (n - fh)

def getMeanVarMetric(Q_metric: dict, size):
    Q_metric_mean   = {p: sum(Q_metric[p]) / size for p in Q_metric}
    Q_metric_var    = {p: math.sqrt(sum([(Q_metric[p][t] - Q_metric_mean[p])**2
    for t in range(size)]) / size) / Q_metric_mean[p]  if Q_metric_mean[p] != 0 else 0 for p in Q_metric}
    return {"mean": Q_metric_mean, "var": Q_metric_var}

def exportToExcel(hist1: History, hist2: History, dst_f):
    wb = openpyxl.load_workbook(hist1.indicators_template_f)
    sh = wb.active
    curr_row = 3
    col = 2
    nbr_weeks = hist1.nbr_weeks
    products = hist1.products
    for w in range(nbr_weeks):
        for p in products:
            sh.cell(curr_row, col + 1).value = hist2.metrics[w]["in"]["robustness"][p]
            sh.cell(curr_row, col + 2).value = hist1.metrics[w]["out"]["robustness"][p]
            sh.cell(curr_row, col + 3).value = hist1.metrics[w]["in"]["robustness"][p]
            
            sh.cell(curr_row, col + 6).value = hist2.metrics[w]["in"]["severity"][p]
            sh.cell(curr_row, col + 7).value = hist1.metrics[w]["out"]["severity"][p]
            sh.cell(curr_row, col + 8).value = hist1.metrics[w]["in"]["severity"][p]
            
            sh.cell(curr_row, col + 11).value = hist2.metrics[w]["in"]["frequency"][p]
            sh.cell(curr_row, col + 12).value = hist1.metrics[w]["out"]["frequency"][p]
            sh.cell(curr_row, col + 13).value = hist1.metrics[w]["in"]["frequency"][p]
            
            sh.cell(curr_row, col + 16).value = hist2.metrics[w]["in"]["adaptability"][p]
            sh.cell(curr_row, col + 17).value = hist1.metrics[w]["out"]["adaptability"][p]
            sh.cell(curr_row, col + 18).value = hist1.metrics[w]["in"]["adaptability"][p]
            curr_row+=1
    curr_row = 3
    col = 23
    n = hist1.horizon
    fh = hist1.fixed_horizon
    cpa1_metric = {p: [getMeanAbsDiff(hist1.cpa_product, t, fh, p) for t in range(n - 1, 2 * n - 1)] for p in hist1.products}
    cpa2_metric = {p: [getMeanAbsDiff(hist2.cpa_product, t, fh, p) for t in range(n - 1, 2 * n - 1)] for p in hist1.products}
    cpa1_var = getMeanVarMetric(cpa1_metric, n)
    cpa2_var = getMeanVarMetric(cpa2_metric, n)
    for p in products:
        sh.cell(curr_row, col).value = cpa1_var['var'][p]
        sh.cell(curr_row, col + 1).value = cpa2_var['var'][p]
        curr_row += 1
    wb.save(dst_f)





