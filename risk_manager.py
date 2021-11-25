import re
import openpyxl
from model.model import Model
import model.utils as utils


class RiskManager:

    def __init__(self, model: Model) -> None:
        self.model = model
        self.horizon = self.model.horizon - 4

    def sumOverAffiliate(self, q, p, param):
        return [sum([q[a][p][param][t] for a, aff in self.model.affiliate_product.items() if p in aff]) for t in range(self.horizon)]

    def loadDModel(self, file_name: str):
        """Load demand uncertainty model from excel file

        Args:
            file_name (str): the excel file
        """
        self.d_aff_model = {a: {p: {} for p in aff_products} for a, aff_products in self.model.affiliate_product.items()}
        self.d_model = {p: {} for p in self.model.products}
        wb = openpyxl.load_workbook(file_name)
        sh = wb.active
        r = 2
        while sh.cell(r, 1).value:
            product = sh.cell(r, 1).value
            aff_code = sh.cell(r, 2).value
            aff = self.model.affiliate_code[aff_code]
            param = sh.cell(r, 4).value
            if param == "RefWeek":
                quantity = self.readRefWeekRow(sh, r, 5)
            else:
                quantity = utils.getSubRow(sh, r, 5, self.horizon)
            self.d_aff_model[aff][product][param] = quantity
            r += 1
        for p in self.model.products:
            for param in ["a", "b", "c", "d"]:
                self.d_model[p][param] = self.sumOverAffiliate(self.d_aff_model, p, param)
            self.d_model[p]["model_type"] = self.d_aff_model["france"]["P1"]["ModelType"]
            self.d_model[p]["ref_week"] = self.d_aff_model["france"]["P1"]["RefWeek"]

    def readRefWeekRow(self, sheet, row, start_col):
        string_ref_weeks = utils.getSubRow(sheet, row, start_col, self.horizon)
        ref_weeks = list(map(int, [re.match(".*W(\d+).*", rw).group(1) for rw in string_ref_weeks]))
        return ref_weeks
        
    def loadRModel(self, file_name: str) -> None:
        """Load the receptin uncertainty model 

        Args:
            file_name (str): the excel file containing the exert data
        """
        wb = openpyxl.load_workbook(file_name)
        sh = wb.active
        params = ["a", "b", "c", "d", "model_type", "ref_week"]
        self.r_model = {p: {
            param: utils.getSubRow(sh, 2 + j + len(params) * k, 5, self.horizon) if param != "ref_week" else 
            self.readRefWeekRow(sh, 2 + j + len(params) * k, 5) 
            for j, param in enumerate(params)
        } for k, p in enumerate(self.model.products) }
    
    def getPossibilityDistParams(self, quantity: dict, model: dict) -> dict:
        """calculate the trapeziodal possibility distribution params for a given quantity

        Args:
            quantity (dict): quantity 
            model (dict): expert uncertainty model

        Returns:
            dict: trapeziodal possibility distribution params 
        """
        params = ["a", "b", "c", "d"]
        Q = list(utils.accumu(quantity))
        dist = {p: [None] * self.horizon for p in params}
        for t in range(self.horizon):
            rw = model["ref_week"][t]
            model_type = model["model_type"][t]
            for param in params:
                if model_type == "I2":
                    dist[param][t] = round(Q[t] + model[param][t] * (Q[t] - Q[rw-1]))
                elif model_type == "I1":
                    dist[param][t] = round(Q[t] + model[param][t] * (Q[t] - Q[rw-1]) / (t - (rw - 1) + 1))
        return dist

    def getL1Possibility(self, rpm: dict, x: dict, s0: dict) -> dict:
        """calculate L1 possibility for every period 't' in the horizon

        Args:
            fcr (dict): reception possibility model parameters
            x (dict): provisionning plan the cdc is trying to figure out
            s0 (dict): the cdc initial stocks for every product

        Returns:
            dict: L1 possibility
        """
        l1_possibility = [None for _ in range(self.horizon)]
        for t in range(self.horizon):
            if x[t] - s0 < rpm["a"][t]:
                l1_possibility[t] = 0
            elif x[t] - s0 < rpm["b"][t]:
                l1_possibility[t] = (x[t] - s0 - rpm["a"][t]) / (rpm["b"][t] - rpm["a"][t])
            else:
                l1_possibility[t] = 1
        return l1_possibility

    def getL2Possibility(self, dpm: dict, x: dict) -> dict:
        """calculate L2 possibility for every period 't' in the horizon

        Args:
            dpm (dict): demand possibility model
            x (dict): provisionning plan the cdc is trying to figure out

        Returns:
            dict: L2 possibility
        """
        l2_possibility = [None for _ in range(self.horizon)]
        for t in range(self.horizon):
            if x[t] > dpm["d"][t]:
                l2_possibility[t] = 0
            elif x[t] > dpm["c"][t]:
                l2_possibility[t] = (dpm["d"][t] - x[t]) / (dpm["d"][t] - dpm["c"][t])
            else:
                l2_possibility[t] = 1
        return l2_possibility

    def getL4Possibility(self, l1p: dict, l2p: dict) -> dict:
        """calculate L4 possibility for every period 't' in the horizon
        Args:
            l1p (dict): L1 possibility for the product 'p'
            l2p (dict): L2 possibility for the product 'p'

        Returns:
            dict: L4 possibility 
        """
        l4_possibility = [max(l1p[t], l2p[t]) for t in range(self.horizon)]
        return l4_possibility
    

if __name__ == "__main__":
    
    model = Model("simu_inputs/global_input.json")
    risk_manager = RiskManager(model)
    risk_manager.loadDModel("uncertainty_models/UMCDF_I2.xlsx")
    risk_manager.loadRModel("uncertainty_models/UMCRF_I1.xlsx")
    
    for week in range(2, 21):
        print(f"# gravity for week {week}")
        model.loadWeekInput(f"simu_inputs/input_S{week}.json")
        model.runWeek()

        x = model.pa_cdc.product_supply_plan
        s0 = model.pa_cdc.initial_stock
        r = model.getCDCReception()
        d = model.pa_cdc.getProductSupplyDemand()

        for p in model.products:
            rpm = risk_manager.getPossibilityDistParams(r[p], risk_manager.r_model[p])
            dpm = risk_manager.getPossibilityDistParams(d[p], risk_manager.d_model[p])
            l1p = risk_manager.getL1Possibility(rpm, x[p], s0[p])
            l2p = risk_manager.getL2Possibility(dpm, x[p])
            l4p = risk_manager.getL4Possibility(l1p, l2p)
            l4n = [1 - l for l in l4p]
            G = max(l4n)
            print(p, ", L4 Nec: ", l4n, ", G: ", G)


