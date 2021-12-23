from re import S, template
from model.filter import SmoothingFilter
from model import SalesManager, Simulation, metrics
import time
import logging 
import json

with open("config/settings.json") as fp:
    settings = json.load(fp)
    logging.basicConfig(filename=settings["log_f"], encoding='utf-8', level=logging.getLevelName(settings["logging_level"]), filemode="w")

if __name__ == "__main__":
    sales_folder        = "sales_history"
    risk_indicator_f    = f"risk_indicators.xlsx"
    start_week          = 0
    end_week            = 40
    nbr_weeks           = end_week - start_week + 1
    smoothing_filter    = SmoothingFilter()
    sales_manager       = SalesManager()


    print("*** START")
    # Generate all sales history beforhand
    st = time.perf_counter()
    print("Generating sales history ", end="", flush=True)
    sales_hist, sales_ref = sales_manager.generateSalesHistory(nbr_weeks)
    print("Finished in ", round(time.perf_counter() - st, 2))
    sales_manager.saveSalesHistory(sales_hist, sales_folder) 

    # Run without smoothing the PA plan
    print("> Working on with smoothing filter case: ")
    simu1 = Simulation("simu1")
    ini_input = simu1.getInitInput(sales_hist[0], simu1.risk_manager.r_model)
    simu1.run(
        sales_ref=sales_ref,
        sales_history=sales_hist,
        start_week=start_week, 
        ini_input=ini_input,
        end_week=end_week, 
        pa_filter=smoothing_filter
    )
    print("*** Finished")

    print("> Working on without smoothing filter case: ")
    simu2 = Simulation("simu2")
    simu2.run(
        sales_ref=sales_ref,
        sales_history=sales_hist,
        start_week=start_week, 
        end_week=end_week, 
        ini_input=ini_input,
        pa_filter=None
    )

    print("Generating indicators excel ... ", end="")
    metrics.exportToExcel(simu1.sim_history, simu2.sim_history, risk_indicator_f)
    print("*** Finished")

    print("*** FINISHED")
    
    
