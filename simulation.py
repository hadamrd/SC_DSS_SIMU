import model
  

if __name__ == "__main__":
    for k in range(2, 47):
        model.runModel(input_file=f"simu_inputs/input_S{k}.json")
        