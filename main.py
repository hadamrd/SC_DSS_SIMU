from model.filter import SmoothingFilter
from model import RiskManager, SalesManager, Simulation, simulation

def printNervosity(qn, qn_star, qtype):
    if qtype == "affiliate":
        for p in my_simu.model.products:
            for a in my_simu.model.itProductAff(p):
                print(f"affiliate: {a}, product: {p}")
                print("mean, var nervosity without platform: ", qn["mean"][a][p], qn["var"][a][p])
                print("mean, var nervosity with platform: ", qn_star["mean"][a][p], qn_star["var"][a][p])
                res = round(100 * (qn_star["var"][a][p] - qn["var"][a][p]) / qn["var"][a][p])
                print(f"nervosity(wit/without) = {res}%")
    elif qtype == "product":
        for p in my_simu.model.products:
            print(f"product: {p}")
            print("mean, var nervosity without platform: ", qn["mean"][p], qn["var"][p])
            print("mean, var nervosity with platform: ", qn_star["mean"][p], qn_star["var"][p])
            res = round(100 * (qn_star["var"][p] - qn["var"][p]) / qn["var"][p])
            print(f"nervosity(wit/without) = {res}")

if __name__ == "__main__":
    initial_sales_f     = "config/sales_S2.json"
    initial_input_f     = "config/input_S2.json"
    sales_folder        = "sales_history"
    demand_UCMF         = "uncertainty_models/UMCDF_I2.xlsx"
    reception_UCMF      = "uncertainty_models/UMCRF_I1.xlsx"
    sales_UCMF          = "uncertainty_models/UMCPVF_I1.xlsx"
    start_week          = 2
    end_week            = 42
    my_simu             = Simulation()
    risk_manager        = RiskManager(demand_UCMF, reception_UCMF)
    smoothing_filter    = SmoothingFilter(risk_manager)
    sales_manager       = SalesManager(sales_UCMF)

    print("*** START")
    # Generate all sales history beforhand
    sales_manager.generateSalesHistory(
        initial_sales_f,
        start_week,
        end_week,
        sales_folder,
        dependency=False
    )

    # Run without smoothing the PA plan
    print("> Working on with smoothing filter case: ")
    nervosity_ws = my_simu.run(
        initial_input_f=initial_input_f, 
        start_week=start_week, 
        end_week=end_week, 
        sales_folder=sales_folder, 
        output_folder="with_smoothing", 
        pa_filter=smoothing_filter
    )
    ws_hist = my_simu.sim_history
    print("*** Finished")

    for w in range(my_simu.sim_history.nbr_weeks):
        print("Week: ", w)
        for p in my_simu.model.products:
            print("Product: ", p)
            print("g risk in: ", ws_hist.g_risk_in[p][w])
            print("g risk out: ", ws_hist.g_risk_out[p][w])
            res = -100 * (ws_hist.g_risk_in[p][w] - ws_hist.g_risk_out[p][w]) / ws_hist.g_risk_in[p][w] if ws_hist.g_risk_in[p][w] != 0 else 0
            print(f"Delta risk({p}): {round(res, 2)}%")
        print("-------------------------------------------------------------")

    # Run with smoothing the PA plan
    print("> Working on without smoothing filter case: ")
    nervosity = my_simu.run(
        initial_input_f=initial_input_f, 
        start_week=start_week, 
        end_week=end_week, 
        sales_folder=sales_folder, 
        output_folder="without_smoothing",
        pa_filter=None
    )
    # print("########################## PA #############################")
    # printNervosity(nervosity["pa"], nervosity_ws["pa"], "affiliate")
    print("################# PA total ###########################################")
    printNervosity(nervosity["pa_product"], nervosity_ws["pa_product"], "product")
    print("*** FINISHED")

    

