from os import system
import os
from model.model import Model
from model.sales import Sales
import simu_history_generator
import json


def simuWithoutPlatform(start_week, end_week):
    model = Model(f"simu_inputs/global_input.json")

    for k in range(start_week, end_week+1):
        model.loadWeekInput(f"simu_inputs/input_S{k}.json")
        model.runAffiliatesToCDC()
        model.runCDCToFactory()
        model.runCDCToAffiliates()
        # model.saveSnapShot(f"simu_history/snapshot_S{k}.json")
        model.saveCurrState(f"simu_history/state_S{k}.json")
        model.generateNextWeekInput(f"simu_inputs/input_S{k+1}.json")
    
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
        
if __name__ == "__main__":
    start_week = 2
    end_week = 40
    #simuWithPlatform(start_week, end_week)
    simuWithoutPlatform(start_week, end_week)
    #simu_history_generator.run()

