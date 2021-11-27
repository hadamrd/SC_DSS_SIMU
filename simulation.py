import os
import history
import json
from model.model import Model
from model.smooth_filter import SmoothFilter
from model.risk_manager import RiskManager


def simuWithoutPlatform(start_week, end_week, inputs_folder, history_folder):
    model = Model(f"simu_inputs/global_input.json")
    for k in range(start_week, end_week+1):
        model.loadWeekInput(os.path.join(inputs_folder, f"input_S{k}.json"))
        model.runAffiliatesToCDC()
        model.runCDCToFactory()
        model.runCDCToAffiliates()
        if not os.path.exists(history_folder):
            os.mkdir(history_folder)
        model.saveSnapShot(os.path.join(history_folder, f"snapshot_S{k}.json"))
        model.generateNextWeekInput(os.path.join(inputs_folder, f"input_S{k+1}.json"))
    
def simuWithPlatform(start_week, end_week):
    model = Model(f"simu_inputs/global_input.json")
    for k in range(start_week, end_week+1):
        model.loadWeekInput(f"simu_inputs/input_S{k}.json")
        with open(f"old_inputs/input_S{k}.json") as fp:
            old_input = json.load(fp)
        model.sales_forcast = old_input["sales_forcast"]
        model.runAffiliatesToCDC()
        model.runCDCToFactory()
        model.runCDCToAffiliates()
        model.getPlatformInput(f"platform_inputs/input_S{k}.xlsx")
        while not os.path.exists(f"platform_outputs/output_S{k}.xlsx"):
            input(f"Press any button after putting the platform output_S{k}.xlsx in platform_outputs folder...")
        model.loadPlatformOutput(f"platform_outputs/output_S{k}.xlsx")
        model.saveCDCSupplyPlan(f"platform_outputs/supply_plan_S{k}.json")
        model.saveSnapShot(f"simu_history/snapshot_S{k}.json")
        model.generateNextWeekInput(f"simu_inputs/input_S{k+1}.json")

def simuWithAutomatedStrat(start_week, end_week):
    sales_forcast_folder = "inputs_without_plateforme"
    history_folder = "with_strat_history"
    inputs_folder = "with_strat_inputs"
    
    if not os.path.exists(inputs_folder):
        os.mkdir(inputs_folder)
    
    model = Model(f"simu_inputs/global_input.json")
    n = model.horizon - 4
    risk_manager = RiskManager(n)
    risk_manager.loadDModel(model, "uncertainty_models/UMCDF_I2.xlsx")
    risk_manager.loadRModel(model, "uncertainty_models/UMCRF_I1.xlsx")
    filter = SmoothFilter(alpha=0.5, fixed_horizon=2)
    for k in range(start_week, end_week+1):
        model.loadWeekInput(f"{inputs_folder}/input_S{k}.json")
        with open(f"{sales_forcast_folder}/input_S{k}.json") as fp:
            old_input = json.load(fp)
        model.sales_forcast = old_input["sales_forcast"]
        model.runAffiliatesToCDC()
        model.runCDCToFactory()
        model.runCDCToAffiliates()
        model.pa_cdc.supply_plan = filter.run(risk_manager, model)
        if not os.path.exists(history_folder):
            os.mkdir(history_folder)
        model.saveSnapShot(f"{history_folder}/snapshot_S{k}.json")
        model.generateNextWeekInput(f"{inputs_folder}/input_S{k+1}.json")

if __name__ == "__main__":
    history_folder = "history_without_plateforme"
    inputs_folder= "inputs_without_plateforme"
    start_week = 2
    end_week = 40

    # simuWithoutPlatform(start_week, end_week, inputs_folder, history_folder)
    
    # history.generate(history_folder="simu_history",
    #                 results_folder="simu_excel_results",
    #                 template_file="templates/template_simu_result.xlsx")

    # simuWithPlatform(start_week, end_week)

    # simuWithAutomatedStrat(start_week, end_week)

    history.generate(history_folder="with_strat_history",
                results_folder="with_strat_excel_results",
                template_file="templates/template_simu_result.xlsx")

    # history.generate(history_folder="history_without_plateforme",
    #             results_folder="without_plateforme_excel_results",
    #             template_file="templates/template_simu_result.xlsx")

    

