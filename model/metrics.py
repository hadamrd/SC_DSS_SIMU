
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

def periodNervousness(Q_history: list[list[int]], t: int, fh: int) -> float:
    n = len(Q_history[0])
    res = 0
    for k in range(n-1):
        y = t - k
        if y < n - fh:
            res += abs(Q_history[y][k] - Q_history[y-1][k+1])
    return res / (n - fh)

def getQMetric(Q_plan: dict, metric, size: int, fh: int):
    if type(next(iter(Q_plan.values()))) == dict:
        return {a: {p: [
            metric(Q_plan[a][p], t, fh) for t in range(size - 1, 2 * size - 1)
        ]
        for p in Q_plan[a]} for a in Q_plan}
    elif type(next(iter(Q_plan.values()))) == list:
        return {p: [
            metric(Q_plan[p], t, fh) for t in range(size - 1, 2 * size - 1)
        ]
        for p in Q_plan}
    else:
        raise Exception("Given history is of unknown type: ", type(Q_plan))

def getMeanVarMetric(Q_metric: dict, size):
    if type(next(iter(Q_metric.values()))) == dict:
        Q_metric_mean   =  {a: {p: sum(Q_metric[a][p]) / size for p in Q_metric[a]} for a in Q_metric}
        Q_metric_var    =  {a: {p: math.sqrt(sum([(Q_metric[a][p][t] - Q_metric_mean[a][p])**2 for t in range(size)]) / size) / Q_metric_mean[a][p] for p in Q_metric[a]} for a in Q_metric}
    elif type(next(iter(Q_metric.values()))) == list:
        Q_metric_mean   = {p: sum(Q_metric[p]) / size for p in Q_metric}
        Q_metric_var    = {p: math.sqrt(sum([(Q_metric[p][t] - Q_metric_mean[p])**2 for t in range(size)]) / size) / Q_metric_mean[p] for p in Q_metric}
    else:
        raise Exception("Given history is of unknown type: ", type(Q_metric))
    return {"mean": Q_metric_mean, "var": Q_metric_var}

def generateMetricsResult(hist: History, riskm: RiskManager):
    fixed_horizon   = hist.fixed_horizon
    horizon         = hist.real_horizon
    input = {"pa": hist.pa_product}
    cpa = {p: hist.getQuantityCumHistory(hist.pa_product[p]) for p in hist.products}
    cpa_nervousness = getQMetric(cpa, periodNervousness, horizon, fixed_horizon)

    result = {"pa": {}}
    result["pa"] = {
        "nervousness": getMeanVarMetric(cpa_nervousness, horizon)["var"],
        "robustness":   {p: [None] * hist.nbr_weeks for p in hist.products},
        "frequency":    {p: [None] * hist.nbr_weeks for p in hist.products},
        "severity":     {p: [None] * hist.nbr_weeks for p in hist.products},
        "adaptability": {p: [None] * hist.nbr_weeks for p in hist.products}
    }

    if hist.with_filter:
        input["pa_in_filter"] = hist.pa_in_filter
        result["pa_in_filter"] = {
            "robustness":   {p: [None] * hist.nbr_weeks for p in hist.products},
            "frequency":    {p: [None] * hist.nbr_weeks for p in hist.products},
            "severity":     {p: [None] * hist.nbr_weeks for p in hist.products},
            "adaptability": {p: [None] * hist.nbr_weeks for p in hist.products}
        }

    n = hist.real_horizon

    for key, pa in input.items():
        for p in hist.products:
            for w in range(hist.nbr_weeks):
                # get product inputs
                demand = {a: {p: hist.ba[a][p][w] for p in hist.ba[a]} for a in hist.ba}
                s0 = hist.s0[p][w]
                reception = {p: hist.pdp[p][w][:n] for p in hist.pdp}
                rpm     = riskm.getRpm(reception, p, s0)
                dpm = riskm.getDpm(demand, p)
                # calculate risk indicators
                x = list(utils.accumu(pa[p][w][:n]))
                l4p = riskm.getL4Possibility(rpm, dpm, x)
                l4n = riskm.getL4Necessity(rpm, dpm, x)
                result[key]["robustness"][p][w] = riskm.getRobustness(l4p)
                result[key]["frequency"][p][w]  = riskm.getFrequency(l4p)
                result[key]["severity"][p][w] = riskm.getSeverity(l4n)
                result[key]["adaptability"][p][w] = 1 - l4n[n-1]
    return result

def exportIndicatorRes(sheet, hist1, hist2, indicator, w, p, row, col):
    sheet.cell(row, col).value     = hist1[indicator][p][w]
    sheet.cell(row, col + 1).value = hist2[indicator][p][w]

def exportToExcel(result1, result2, tmplate_f, dst_f, nbr_weeks, products):
    wb = openpyxl.load_workbook(tmplate_f)
    sh = wb.active
    curr_row = 3
    col = 2
    for w in range(nbr_weeks):
        for p in products:
            sh.cell(curr_row, col + 1).value = result2["pa"]["robustness"][p][w]
            sh.cell(curr_row, col + 2).value = result1["pa_in_filter"]["robustness"][p][w]
            sh.cell(curr_row, col + 3).value = result1["pa"]["robustness"][p][w]
            
            sh.cell(curr_row, col + 6).value = result2["pa"]["severity"][p][w]
            sh.cell(curr_row, col + 7).value = result1["pa_in_filter"]["severity"][p][w]
            sh.cell(curr_row, col + 8).value = result1["pa"]["severity"][p][w]
            
            sh.cell(curr_row, col + 11).value = result2["pa"]["frequency"][p][w]
            sh.cell(curr_row, col + 12).value = result1["pa_in_filter"]["frequency"][p][w]
            sh.cell(curr_row, col + 13).value = result1["pa"]["frequency"][p][w]
            
            sh.cell(curr_row, col + 16).value = result2["pa"]["adaptability"][p][w]
            sh.cell(curr_row, col + 17).value = result1["pa_in_filter"]["adaptability"][p][w]
            sh.cell(curr_row, col + 18).value = result1["pa"]["adaptability"][p][w]
            curr_row+=1
    curr_row = 3
    col = 23
    for p in products:
        sh.cell(curr_row, col).value = result1["pa"]["nervousness"][p]
        sh.cell(curr_row, col + 1).value = result2["pa"]["nervousness"][p]
        curr_row += 1
    wb.save(dst_f)





