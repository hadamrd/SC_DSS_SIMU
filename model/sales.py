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
        self.loadModel(self.sales_UCMF)
    
    def loadModel(self, file_name):
        with open(file_name) as fp:
            self.ucm = json.load(fp)
            
    def loadModelFromExcel(self, umcpv_f):
        wb = openpyxl.load_workbook(umcpv_f)
        self.ucm = {}
        for a in self.itAffiliates():
            aff_code = self.getAffCode(a)
            sh = wb[aff_code]
            self.ucm[a] = {}
            for k, param in enumerate(["a", "b", "c", "d", "ref_week"]):
                self.ucm[a][param] = [sh.cell(row=2+k, column=t+2).value for t in range(self.horizon)]
    
    def saveSalesHistory(self, hist, dst_folder):
        nbr_weeks = len(hist)
        if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)
        for w in range(nbr_weeks):
            dst_file = os.path.join(dst_folder, f"sales_S{w}.json")
        with open(dst_file, "w") as fp:
            json.dump(hist, fp)
            
    def generateSalesHistory(self, nbr_weeks):
        pv_hist = [self.getEmptyAffQ() for _ in range(nbr_weeks)] 
        for a, p in self.itParams():
            hist = utils.genRandQHist(nbr_weeks, self.ucm[a][p], self.getAffPvRange(a))
            for w in range(nbr_weeks):
                pv_hist[w][a][p] = hist[w]
        return pv_hist
    



        

    

     