import model
  

if __name__ == "__main__":
    start_week = 2
    end_week = 46
    for k in range(start_week, end_week+1):
        model.runModel(input_file=f"simu_inputs/input_S{k}.json",
                       load_supply_plan_from_excel=True)
        