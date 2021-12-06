from re import S, template
from model.filter import SmoothingFilter
from model import RiskManager, SalesManager, Simulation, metrics


if __name__ == "__main__":
    initial_sales_f     = "config/sales_S2.json"
    initial_input_f     = "config/input_S2.json"
    sales_folder        = "sales_history"  
    risk_indicator_f = f"risk_indicators.xlsx"
    start_week          = 2
    end_week            = 42
    smoothing_filter    = SmoothingFilter()
    sales_manager       = SalesManager()

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

    print("Generating indicators excel ... ", end="")
    nbr_weeks = end_week - start_week + 1
    metrics.exportToExcel(simu1.sim_history, simu2.sim_history, risk_indicator_f)

    print("*** FINISHED")
    
    
