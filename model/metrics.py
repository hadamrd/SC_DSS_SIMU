
import openpyxl
import math
from model import history
from . import History, utils


def periodMean(Q_history: list[list[int]], t: int, fh: int):
    n = len(Q_history[0])
    res = 0
    for k in range(n):
        res += Q_history[t - k][k]
    return res / (n - fh + 1)

def periodNervosity(Q_history: list[list[int]], t: int, fh: int) -> float:
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
    return Q_metric_mean, Q_metric_var

def generateMetricsResult(hist: History, dst_file: str):
    fixed_horizon   = hist.fixed_horizon
    horizon         = hist.real_horizon
    cum_hist        = hist.getCumHistory()

    pa_product = hist.sumCumHistOverAff(cum_hist.supply_plan)
    ba_product = hist.sumCumHistOverAff(cum_hist.supply_demand)
    pv_product = hist.sumCumHistOverAff(cum_hist.sales_forcast)

    pa_nervosity    = getQMetric(cum_hist.supply_plan, periodNervosity, horizon, fixed_horizon)
    pdp_nervosity   = getQMetric(cum_hist.prod_plan, periodNervosity, horizon, fixed_horizon)
    bp_nervosity    = getQMetric(cum_hist.prod_demand, periodNervosity, horizon, fixed_horizon)
    ba_nervosity    = getQMetric(cum_hist.supply_demand, periodNervosity, horizon, fixed_horizon)
    pv_nervosity    = getQMetric(cum_hist.sales_forcast, periodNervosity, horizon, fixed_horizon)

    pa_product_nervosity = getQMetric(pa_product, periodNervosity, horizon, fixed_horizon)
    ba_product_nervosity = getQMetric(ba_product, periodNervosity, horizon, fixed_horizon)
    pv_product_nervosity = getQMetric(pv_product, periodNervosity, horizon, fixed_horizon)

    wb = openpyxl.load_workbook(hist.metrics_template_f)
    
    for p in hist.products:
        sheet = wb[p]
        utils.writeRow(sheet, 3, 3, pa_product_nervosity)
        utils.writeRow(sheet, 4, 3, ba_product_nervosity)
        utils.writeRow(sheet, 5, 3, pv_product_nervosity)
        utils.writeRow(sheet, 6, 3, pdp_nervosity[p])
        utils.writeRow(sheet, 7, 3, bp_nervosity[p])
        curr_row = 8
        for a in hist.itProductAff(p):
            curr_row += 1
            sheet.cell(curr_row, 1).value = a 
            utils.writeRow(sheet, curr_row, 3, pv_nervosity[a][p])
            utils.writeRow(sheet, curr_row + 1, 3, ba_nervosity[a][p])
            utils.writeRow(sheet, curr_row + 2, 3, pa_nervosity[a][p])
            curr_row += 3
        curr_row = 27
    wb.save(dst_file)

    mean_var_nervosity = {}
    m, v = getMeanVarMetric(pa_nervosity, horizon)
    mean_var_nervosity["pa"] = {"mean": m, "var": v}
    m, v = getMeanVarMetric(ba_nervosity, horizon)
    mean_var_nervosity["ba"] = {"mean": m, "var": v}
    m, v = getMeanVarMetric(pdp_nervosity, horizon)
    mean_var_nervosity["pdp"] = {"mean": m, "var": v}
    m, v = getMeanVarMetric(pv_nervosity, horizon)
    mean_var_nervosity["bv"] = {"mean": m, "var": v}
    m, v = getMeanVarMetric(bp_nervosity, horizon)
    mean_var_nervosity["bp"] = {"mean": m, "var": v}
    m, v = getMeanVarMetric(pa_product_nervosity, horizon)
    mean_var_nervosity["pa_product"] = {"mean": m, "var": v}
    m, v = getMeanVarMetric(ba_product_nervosity, horizon)
    mean_var_nervosity["ba_product"] = {"mean": m, "var": v}
    m, v = getMeanVarMetric(pv_product_nervosity, horizon)
    mean_var_nervosity["pv_product"] = {"mean": m, "var": v}

    return mean_var_nervosity








