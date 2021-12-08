
import openpyxl
import math
from model import history
from model.risk import RiskManager
from . import History, utils


def periodMean(q_hist: list[list[int]], t: int, fh: int):
    n = len(q_hist[0])
    res = 0
    for k in range(n):
        res += q_hist[t - k][k]
    return res / (n - fh + 1)

def getMeanAbsDiff(cq_hist: list[dict[str, list[int]]], t: int, fh: int, h: int, p: str) -> float:
    res = 0
    for k in range(fh-1, h-2):
        y = t - k
        res += abs(cq_hist[y][p][k] - cq_hist[y-1][p][k+1] + cq_hist[y-1][p][0])
    return res / (h - (fh-1) - 2)

def getMeanVarMetric(q_metric: dict):
    q_metric_mean   = {p: utils.getMean(q_metric[p]) for p in q_metric}
    q_metric_var    = {p: utils.var(q_metric[p], q_metric_mean[p]) for p in q_metric}
    return {"mean": q_metric_mean, "var": q_metric_var}

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
            sh.cell(curr_row, col + 2).value = hist1.metrics[w]["in"]["robustness"][p]
            sh.cell(curr_row, col + 3).value = hist1.metrics[w]["out"]["robustness"][p]
            
            sh.cell(curr_row, col + 6).value = hist2.metrics[w]["in"]["severity"][p]
            sh.cell(curr_row, col + 7).value = hist1.metrics[w]["in"]["severity"][p]
            sh.cell(curr_row, col + 8).value = hist1.metrics[w]["out"]["severity"][p]

            sh.cell(curr_row, col + 11).value = hist2.metrics[w]["in"]["frequency"][p]
            sh.cell(curr_row, col + 12).value = hist1.metrics[w]["in"]["frequency"][p]
            sh.cell(curr_row, col + 13).value = hist1.metrics[w]["out"]["frequency"][p]
            
            sh.cell(curr_row, col + 16).value = hist2.metrics[w]["in"]["adaptability"][p]
            sh.cell(curr_row, col + 17).value = hist1.metrics[w]["in"]["adaptability"][p]
            sh.cell(curr_row, col + 18).value = hist1.metrics[w]["out"]["adaptability"][p]
            curr_row+=1
    curr_row = 3
    col = 23
    n = hist1.real_horizon
    fh = hist1.fixed_horizon
    cpa1_metric = {p: [getMeanAbsDiff(hist1.cproduct_supply, t, fh, n, p) for t in range(n - 1, 2 * n - 1)] for p in hist1.products}
    cpa2_metric = {p: [getMeanAbsDiff(hist2.cproduct_supply, t, fh, n, p) for t in range(n - 1, 2 * n - 1)] for p in hist1.products}
    cpa1_var = getMeanVarMetric(cpa1_metric)
    cpa2_var = getMeanVarMetric(cpa2_metric)
    for p in products:
        sh.cell(curr_row, col).value = cpa1_var['var'][p]
        sh.cell(curr_row, col + 1).value = cpa2_var['var'][p]
        curr_row += 1
    wb.save(dst_f)





