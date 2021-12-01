
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

def generateMetricsResult(hist: History, riskm: RiskManager, dst_file: str):
    fixed_horizon   = hist.fixed_horizon
    horizon         = hist.real_horizon
    cum_hist        = hist.getCumHistory()

    pa_product = hist.sumCumHistOverAff(cum_hist.pa)
    ba_product = hist.sumCumHistOverAff(cum_hist.ba)
    pv_product = hist.sumCumHistOverAff(cum_hist.pv)

    pa_nervousness    = getQMetric(cum_hist.pa, periodNervousness, horizon, fixed_horizon)
    pdp_nervousness   = getQMetric(cum_hist.pdp, periodNervousness, horizon, fixed_horizon)
    bp_nervousness    = getQMetric(cum_hist.bp, periodNervousness, horizon, fixed_horizon)
    ba_nervousness    = getQMetric(cum_hist.ba, periodNervousness, horizon, fixed_horizon)
    pv_nervousness    = getQMetric(cum_hist.pv, periodNervousness, horizon, fixed_horizon)

    pa_product_nervousness = getQMetric(pa_product, periodNervousness, horizon, fixed_horizon)
    ba_product_nervousness = getQMetric(ba_product, periodNervousness, horizon, fixed_horizon)
    pv_product_nervousness = getQMetric(pv_product, periodNervousness, horizon, fixed_horizon)

    # wb = openpyxl.load_workbook(hist.metrics_template_f)
    # for p in hist.products:
    #     sheet = wb[p]
    #     utils.writeRow(sheet, 3, 3, pa_product_nervousness[p])
    #     utils.writeRow(sheet, 4, 3, ba_product_nervousness[p])
    #     utils.writeRow(sheet, 5, 3, pv_product_nervousness[p])
    #     utils.writeRow(sheet, 6, 3, pdp_nervousness[p])
    #     utils.writeRow(sheet, 7, 3, bp_nervousness[p])
    #     curr_row = 8
    #     for a in hist.itProductAff(p):
    #         curr_row += 1
    #         sheet.cell(curr_row, 1).value = a 
    #         utils.writeRow(sheet, curr_row, 3, pv_nervousness[a][p])
    #         utils.writeRow(sheet, curr_row + 1, 3, ba_nervousness[a][p])
    #         utils.writeRow(sheet, curr_row + 2, 3, pa_nervousness[a][p])
    #         curr_row += 3
    #     curr_row = 27
    # wb.save(dst_file)

    result = {}

    result["nervousness"] = {
        "pa": getMeanVarMetric(pa_nervousness, horizon),
        "ba": getMeanVarMetric(ba_nervousness, horizon),
        "pv": getMeanVarMetric(pv_nervousness, horizon),
        "pa_product": getMeanVarMetric(pa_product_nervousness, horizon),
        "ba_product": getMeanVarMetric(ba_product_nervousness, horizon),
        "pv_product": getMeanVarMetric(pv_product_nervousness, horizon),
        "bp": getMeanVarMetric(bp_nervousness, horizon),
        "pdp": getMeanVarMetric(pdp_nervousness, horizon),
    }

    result["robustness"] = {p: [None] * hist.nbr_weeks for p in hist.products}
    result["frequency"] = {p: [None] * hist.nbr_weeks for p in hist.products}
    result["severity"] = {p: [None] * hist.nbr_weeks for p in hist.products}
    result["adaptability"] = {p: [None] * hist.nbr_weeks for p in hist.products}

    n = hist.real_horizon
    for p in hist.products:
        for w in range(hist.nbr_weeks):
            # get product inputs
            demand = {a: {p: hist.ba[a][p][w] for p in hist.ba[a]} for a in hist.ba}
            s0 = hist.s0[p][w]
            x = pa_product[p][w][:n]
            reception = {p: hist.pdp[p][w][:n] for p in hist.pdp}
            # calculate possibility models
            rpm = riskm.getRpm(reception, p)
            aff_dpm = riskm.getDpm(demand, p)
            # get dpm / product, sum over afiiliate
            params = ["a", "b", "c", "d"]
            dpm = {param: [sum([aff_dpm[a][param][t] for a in aff_dpm]) for t in range(n)] for param in params}
            # calculate risk indicators
            l4p = riskm.getL4Possibility(rpm, dpm, x, s0)
            l4n = riskm.getL4Necessity(rpm, dpm, x, s0)
            result["robustness"][p][w] = riskm.getRobustness(l4p)
            result["frequency"][p][w] = riskm.getFrequency(l4p)
            result["severity"][p][w] = riskm.getSeverity(l4n)
            result["adaptability"][p][w] = 1 - l4n[n-1]
    return result

def exportToExcel(result1, result2, tmplate_f, dst_f, nbr_weeks, products):
    wb = openpyxl.load_workbook(tmplate_f)
    sh = wb.active
    curr_row = 3
    col = 3
    for w in range(nbr_weeks):
        for p in products:
            sh.cell(curr_row, col).value     = result1["robustness"][p][w]
            sh.cell(curr_row, col + 1).value = result2["robustness"][p][w]

            sh.cell(curr_row, col + 3).value     = result1["severity"][p][w]
            sh.cell(curr_row, col + 3 + 1).value = result2["severity"][p][w]

            sh.cell(curr_row, col + 6).value = result1["frequency"][p][w]
            sh.cell(curr_row, col + 6 + 1).value = result2["frequency"][p][w]

            sh.cell(curr_row, col + 9).value = result1["adaptability"][p][w]
            sh.cell(curr_row, col + 9 + 1).value = result2["adaptability"][p][w]
            curr_row+=1
    wb.save(dst_f)







