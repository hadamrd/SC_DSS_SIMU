from model.filter import SmoothingFilter
from model import RiskManager, SalesManager, Simulation, simulation


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
    sales_manager.generateSalesHistory(initial_sales_f, start_week, end_week, sales_folder)

    # Run without smoothing the PA plan
    print("> Working on with smoothing filter case: ")
    mean_var_nerv_wf = my_simu.run(
        initial_input_f=initial_input_f, 
        start_week=start_week, 
        end_week=end_week, 
        sales_folder=sales_folder, 
        output_folder="with_smoothing", 
        pa_filter=smoothing_filter
    )
    print("*** Finished")

    # Run with smoothing the PA plan
    print("> Working on without smoothing filter case: ")
    mean_var_nerv = my_simu.run(
        initial_input_f=initial_input_f, 
        start_week=start_week, 
        end_week=end_week, 
        sales_folder=sales_folder, 
        output_folder="without_smoothing",
        pa_filter=None
    )

    for a, p in my_simu.model.itParams():
        print(f"affiliate: {a}, product: {p}")
        print("mean, var nervosity without platform: {0}\t{1}".format(mean_var_nerv["pa"]["mean"][a][p], mean_var_nerv["pa"]["var"][a][p]))
        print("mean, var nervosity with platform: ", mean_var_nerv_wf["pa"]["mean"][a][p], mean_var_nerv_wf["pa"]["var"][a][p])
        res = round(100 * (mean_var_nerv_wf["pa"]["var"][a][p] - mean_var_nerv["pa"]["var"][a][p]) / mean_var_nerv["pa"]["var"][a][p])
        print(f"nervosity(wit/without) = {res}")

    print("*** FINISHED")

    

