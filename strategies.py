from risk_manager import RiskManager
from model.model import Model
from model import utils
import matplotlib.pyplot as plt

def test_plot():
    model = Model("simu_inputs/global_input.json")
    risk_manager = RiskManager(model)
    risk_manager.loadDModel("uncertainty_models/UMCDF_I2.xlsx")
    risk_manager.loadRModel("uncertainty_models/UMCRF_I1.xlsx")
    
    week = 3
    print(f"# gravity for week {week}")
    model.loadWeekInput(f"simu_inputs/input_S{week}.json")
    model.runWeek()

    pa = model.pa_cdc.product_supply_plan
    initial_stock = model.pa_cdc.initial_stock
    reception = model.getCDCReception()
    demand = model.pa_cdc.getProductSupplyDemand()

    p = "P3"

    x = list(utils.accumu(pa[p]))
    r = list(utils.accumu(reception[p]))
    d = list(utils.accumu(demand[p]))
    s0 = initial_stock[p]
    rpm = risk_manager.getPossibilityDistParams(r, risk_manager.r_model[p])
    dpm = risk_manager.getPossibilityDistParams(d, risk_manager.d_model[p])

    ax, y = risk_manager.sampleL1Possibility(rpm, s0, 3, 100)
    plt.plot(ax, y, 'b')

    ax, y = risk_manager.sampleL2Possibility(dpm, 3, 100)
    plt.plot(ax, y, 'g')

    ax, y = risk_manager.sampleL4Possibility(rpm, dpm, s0, 3, 100)
    plt.plot(ax, y, 'r')

    plt.show()

    l1p = risk_manager.getL1Possibility(rpm, x, s0)
    l2p = risk_manager.getL2Possibility(dpm, x)
    l4p = risk_manager.getL4Possibility(l1p, l2p)
    l4n = [1 - l for l in l4p]
    G = max(l4n)
    print(p, ", L4 Nec: ", l4n, ", G: ", G)

if __name__ == "__main__":

    model = Model("simu_inputs/global_input.json")
    risk_manager = RiskManager(model)
    risk_manager.loadDModel("uncertainty_models/UMCDF_I2.xlsx")
    risk_manager.loadRModel("uncertainty_models/UMCRF_I1.xlsx")
    
    for week in range(2, 20):

        print(f"############# gravity for week {week} ##################")
        model.loadWeekInput(f"simu_inputs/input_S{week}.json")
        model.runWeek()

        pa = model.pa_cdc.product_supply_plan
        initial_stock = model.pa_cdc.initial_stock
        reception = model.getCDCReception()
        demand = model.pa_cdc.getSupplyDemand()

        for p in model.products:
            x = list(utils.accumu(pa[p]))
            r = list(utils.accumu(reception[p]))
            d = demand
            s0 = initial_stock[p]
            rpm = risk_manager.getRpm(r, p)
            dpm = risk_manager.getDpm(d, p)
            G = risk_manager.getG(rpm, dpm, s0, x)
            if G > 0.5:
                print(f"G for {p}: ", G)
                print("initial x sum: ", x[-1])
                x, G = risk_manager.findSolX(rpm, dpm, s0, x)
                print("sum after algo: ", x[-1])
                print("G after algo: ", G)
        model.generateNextWeekInput(f"simu_inputs/input_S{week+1}.json")




