from os import system
from model import Model
import excel_results_writer
import json

if __name__ == "__main__":
    start_week = 2
    end_week = 46
    for k in range(start_week, end_week+1):
        model = Model(f"simu_inputs/input_S{k}.json")
        model.generatePlatformInput()
        model.loadSupplyPlanFromExcel()
        model.run()
        model.saveOutput(f"simu_outputs/output_S{k}.json")
        model.generateNextInput(f"simu_inputs/input_S{k+1}.json")
    excel_results_writer.writeToExcel()
    
    
        