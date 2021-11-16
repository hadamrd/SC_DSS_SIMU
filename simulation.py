from os import system
from model.model import Model
import excel_results_writer
import json

if __name__ == "__main__":
    start_week = 2
    end_week = 3
    for k in range(start_week, end_week+1):
        model = Model(f"simu_inputs/input_S{k}.json")
        model.runAffiliatesToCDC()
        model.runCDCToFactory()
        model.generateCDCToAffiliateInput(f"platform_inputs/input_S{k}.xlsx")
        model.loadSupplyPlanFromExcel(f"platform_outputs/output_S{k}.xlsx")
        model.generateNextInput(f"simu_inputs/input_S{k+1}.json")