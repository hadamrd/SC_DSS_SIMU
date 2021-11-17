from os import system
from model.model import Model
import platform_interface
import simu_history_generator
import json

def simuWithoutPlatform(start_week, end_week):
    model = Model(f"simu_inputs/global_input.json")
    for k in range(start_week, end_week+1):
        model.loadWeekInput(f"simu_inputs/input_S{k}.json")
        model.runAffiliatesToCDC()
        model.runCDCToFactory()
        model.runCDCToAffiliates()
        model.saveSnapShot(f"simu_history/snapshot_S{k}.json")
        model.generateNextWeekInput(f"simu_inputs/input_S{k+1}.json")
    
def simuWithPlatform(start_week, end_week):
    model = Model(f"simu_inputs/global_input.json")
    for k in range(start_week, end_week+1):
        model.loadWeekInput(f"simu_inputs/input_S{k}.json")
        model.runAffiliatesToCDC()
        model.runCDCToFactory()
        model.runCDCToAffiliates()
        platform_interface.generateInput(f"platform_inputs/input_S{k}.xlsx", model)
        input("Press any button after putting the platform output in platform_outputs folder...")
        cdc_supply_plan = platform_interface.loadSupplyPlan(f"platform_outputs/output_S{k}.xlsx",
                                                            model.affiliate_code,
                                                            model.horizon)
        with open(f"platform_outputs/supply_plan_S{k}.json", 'w') as fp:
            json.dump(cdc_supply_plan, fp)
        model.setCDCSupplyPlan(cdc_supply_plan)
        model.saveSnapShot(f"simu_history/snapshot_S{k}.json")
        model.generateNextWeekInput(f"simu_inputs/input_S{k+1}.json")
        
if __name__ == "__main__":
    start_week = 2
    end_week = 40
    simuWithoutPlatform(start_week, end_week)
    simu_history_generator.run()