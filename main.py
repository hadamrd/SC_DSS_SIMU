from re import template
from model.filter import SmoothingFilter
from model import RiskManager, SalesManager, Simulation, metrics

def printNervosity(simu: Simulation, qn, qn_star, qtype):
    if qtype == "affiliate":
        for p in simu.model.products:
            for a in simu.model.itProductAff(p):
                print(f"affiliate: {a}, product: {p}")
                print("Nervousness S1 (mean, var) : (", round (qn["mean"][a][p], 3),round (qn["var"][a][p], 2), ")")
                print("Nervousness S2 (mean, var) : (", round (qn_star["mean"][a][p],3), round (qn_star["var"][a][p], 2), ")")
                res = round(100 * (qn_star["var"][a][p] - qn["var"][a][p]) / qn["var"][a][p], 1)
                print(f"Nervousness (S1/S2) = {res}%")
    elif qtype == "product":
        for p in simu.model.products:
            print(f"product: {p}")
            print("Nervousness S1 (mean, var) : (", round(qn["mean"][p], 3), ";" , round (qn["var"][p], 2) ,")")
            print("Nervousness S2 (mean, var) : (", round (qn_star["mean"][p],3), ";" , round (qn_star["var"][p], 2), ")")
            res = round(100 * (qn_star["var"][p] - qn["var"][p]) / qn["var"][p], 1)
            print(f"Nervousness (S1/S2) = {res}%")

if __name__ == "__main__":
    initial_sales_f     = "config/sales_S2.json"
    initial_input_f     = "config/input_S2.json"
    sales_folder        = "sales_history"
    demand_UCMF         = "uncertainty_models/UMCDF_I2.xlsx"
    reception_UCMF      = "uncertainty_models/UMCRF_I1.xlsx"
    sales_UCMF          = "uncertainty_models/UMCPVF_I1.xlsx"
    start_week          = 2
    end_week            = 42
    risk_manager        = RiskManager(demand_UCMF, reception_UCMF)
    smoothing_filter    = SmoothingFilter(risk_manager)
    sales_manager       = SalesManager(sales_UCMF)

    print("*** START")
    # Generate all sales history beforhand
    sales_manager.generateSalesHistory(
        initial_sales_f,
        start_week,
        end_week,
        sales_folder
    )

    # Run without smoothing the PA plan
    print("> Working on with smoothing filter case: ")
    simu1 = Simulation("simu1")
    simu1.run(
        initial_input_f=initial_input_f, 
        start_week=start_week, 
        end_week=end_week, 
        sales_folder=sales_folder,
        pa_filter=smoothing_filter
    )
    print("*** Finished")

    print("> Working on without smoothing filter case: ")
    simu2 = Simulation("simu2")
    simu2.run(
        initial_input_f=initial_input_f, 
        start_week=start_week, 
        end_week=end_week, 
        sales_folder=sales_folder,
        pa_filter=None
    )
        
    risk_indicator_f = f"risk_indicators.xlsx"
    print("Generating metrics ... ", end="")
    risk_indicators1 = metrics.generateMetricsResult(
        hist=simu1.sim_history,
        riskm=risk_manager
    )
    
    risk_indicators2 = metrics.generateMetricsResult(
        hist=simu2.sim_history,
        riskm=risk_manager
    )
    print("Finished")

    print("Generating indicators excel ... ", end="")
    indicators_template_f = "templates/template_risk_indicators.xlsx"
    indicators_f = "risk_indicators.xlsx"
    nbr_weeks = end_week - start_week + 1
    products = simu1.model.products
    metrics.exportToExcel(risk_indicators1, risk_indicators2, indicators_template_f, indicators_f, nbr_weeks, products)
    # print("########################## PA #############################")
    # printNervosity(nervosity["pa"], risk_indicator["vervousness"]["pa"], "affiliate")
    # print("######################## PA total #########################")
    # printNervosity(nervosity["pa_product"], risk_indicator["vervousness"]["pa"]["pa_product"], "product")

    print("*** FINISHED")
    
    

