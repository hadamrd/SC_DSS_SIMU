import datetime
import random
import openpyxl
from . import Shared
from . import utils 
import os
import json 
import time
import copy
random.seed(datetime.datetime.now())

class SalesManager(Shared):

    def __init__(self) -> None:
        super().__init__()
        self.ucm: dict = {}
        if self.sales_UCMF.endswith(".json"):
            self.loadModel(self.sales_UCMF)
        elif self.sales_UCMF.endswith(".xlsx"):
            self.ucm = self.loadAffModelFromExcel(self.sales_UCMF, size=self.horizon)
            
    def loadModel(self, file_name):
        with open(file_name) as fp:
            self.ucm = json.load(fp)
            
    def saveSalesHistory(self, hist, dst_folder):
        nbr_weeks = len(hist)
        if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)
        dst_file = os.path.join(dst_folder, f"sales.json")
        with open(dst_file, "w") as fp:
            json.dump(hist, fp)
            
    def generateSalesHistory(self, nbr_weeks):
        pv_hist = [self.getEmptyAffQ() for _ in range(nbr_weeks)] 
        for a, p in self.itParams():
            print(".", end="", flush=True)
            hist = utils.genRandQHist(nbr_weeks, self.ucm[a][p], self.getAffPvRange(a), fh=self.fixed_horizon)
            for w in range(nbr_weeks):
                pv_hist[w][a][p] = hist[w]
        return pv_hist