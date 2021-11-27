import openpyxl
import json 
import os
import re 

def generate(prefix, history_folder, results_folder, template_file):
    with open(f"simu_inputs/global_input.json") as fp:
        data = json.load(fp)
    products = data["products"]
    affiliates = data["affiliates"]
    horizon = data["horizon"]
    
    start_week = None
    end_week = None
    for file_name in os.listdir(history_folder):
        if file_name.startswith("snapshot_S"):
            week = int(re.match(".*S(\d+).*", file_name).group(1))
            start_week = min(week, start_week) if start_week is not None else week
            end_week = max(week, end_week) if end_week is not None else week
    nbr_weeks = end_week - start_week + 1
    
    product_sales_history = [None] * nbr_weeks
    prod_plan_history =  [None] * nbr_weeks
    supply_demand_history =  [None] * nbr_weeks
    supply_plan_history =  [None] * nbr_weeks
    prod_demand_history =  [None] * nbr_weeks
    for file_name in os.listdir(history_folder):
        if file_name.startswith("snapshot_S"):
            with open(os.path.join(history_folder, file_name)) as fp:
                snapshot = json.load(fp)
            week = int(re.match(".*S(\d+).*", file_name).group(1))
            supply_demand_history[week-start_week] = snapshot["supply_demand"]
            prod_plan_history[week-start_week] = snapshot["prod_plan"]
            supply_plan_history[week-start_week] = snapshot["supply_plan"]
            prod_demand_history[week-start_week] = snapshot["prod_demand"]
            product_sales_history[week-start_week] = snapshot["sales_forcast"]

    if not os.path.exists(results_folder):
        os.mkdir(results_folder)

    wb = openpyxl.load_workbook(template_file)
    for p in products:
        for w in range(nbr_weeks):
            for t in range(horizon):
                wb["PV"].cell(row=3+w, column=3+t+w).value = sum([product_sales_history[w][a][p][t] for a in affiliates if p in data["affiliate_product"][a]])
                wb["BA"].cell(row=3+w, column=3+t+w).value = sum([supply_demand_history[w][a][p][t] for a in affiliates if p in data["affiliate_product"][a]])
                wb["BP"].cell(row=3+w, column=3+t+w).value = prod_demand_history[w][p][t]
                wb["PDP"].cell(row=3+w, column=3+t+w).value = prod_plan_history[w][p][t]
                wb["PA"].cell(row=3+w, column=3+t+w).value = sum([supply_plan_history[w][a][p][t] for a in affiliates if p in data["affiliate_product"][a]])
        wb.save(os.path.join(results_folder, f"{prefix}_{p}_results.xlsx"))

    wb = openpyxl.load_workbook(template_file)
    wb.remove_sheet(wb["PDP"])
    wb.remove_sheet(wb["BP"])
    for a in affiliates:
        for p in data["affiliate_product"][a]:
            for w in range(nbr_weeks):
                for t in range(horizon):
                     wb["PV"].cell(row=3+w, column=3+t+w).value = product_sales_history[w][a][p][t]
                     wb["BA"].cell(row=3+w, column=3+t+w).value = supply_demand_history[w][a][p][t]
                     wb["PA"].cell(row=3+w, column=3+t+w).value = supply_plan_history[w][a][p][t]
            wb.save(os.path.join(results_folder, f"{prefix}_{a}_{p}_results.xlsx"))



