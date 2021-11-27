import openpyxl
import json 
import os

def sumOverAffiliates(quantity, affiliates, products, horizon):
    return {
            p: [
                sum([quantity[a][p][t] for a in affiliates if p in quantity[a]]) for t in range(horizon)
            ] for p in products
        }
    
def generate(history_folder, results_folder, template_file):
    with open(f"simu_inputs/global_input.json") as fp:
        data = json.load(fp)
    products = data["products"]
    affiliates = data["affiliates"]
    horizon = data["horizon"]
    
    wb = openpyxl.load_workbook(template_file)

    product_sales_history = []
    prod_plan_history = []
    supply_demand_history = []
    supply_plan_history = []
    prod_demand_history = []

    for file_name in os.listdir(history_folder):
        if file_name.startswith("snapshot_S"):
            with open(os.path.join(history_folder, file_name)) as fp:
                snapshot = json.load(fp)
            supply_demand_history.append(sumOverAffiliates(snapshot["supply_demand"], affiliates, products, horizon))
            prod_plan_history.append(snapshot["prod_plan"])
            supply_plan_history.append(sumOverAffiliates(snapshot["supply_plan"], affiliates, products, horizon))
            prod_demand_history.append(snapshot["prod_demand"])
            product_sales_history.append(sumOverAffiliates(snapshot["sales_forcast"], affiliates, products, horizon))

    nbr_weeks = len(prod_plan_history)
    for p in products:
        for w in range(nbr_weeks):
            for t in range(horizon):
                wb["PV"].cell(row=3+w, column=3+t+w).value = product_sales_history[w][p][t]
                wb["BA"].cell(row=3+w, column=3+t+w).value = supply_demand_history[w][p][t]
                wb["BP"].cell(row=3+w, column=3+t+w).value = prod_demand_history[w][p][t]
                wb["PDP"].cell(row=3+w, column=3+t+w).value = prod_plan_history[w][p][t]
                wb["PA"].cell(row=3+w, column=3+t+w).value = supply_plan_history[w][p][t]
        if not os.path.exists(results_folder):
            os.mkdir(results_folder)
        wb.save(os.path.join(results_folder, f"{p}_results.xlsx"))