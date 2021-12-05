import json
from typing import Any, Tuple
import enum
import math
class PvRandStrat(enum.Enum):
    minmax = "minmax"
    uniform = "uniform"
class Shared:
    def __init__(self) -> None:
        with open("config/settings.json") as fp:
            self.settings: dict[str, Any] = json.load(fp)
        self.affiliate_name: list[str]      = self.settings["affiliates"]
        self.affiliate_code: dict[str, str] = self.settings["affiliate_code"]
        self.horizon: int                   = self.settings["horizon"]
        self.products: list[str]            = self.settings["products"]
        self.prod_time: int                 = self.settings["prod_time"]
        self.delivery_time: dict[str, int]  = self.settings["delivery_time"]
        self.target_stock: dict[str, int]   = self.settings["target_stock"]
        self.affiliate_products: dict[str, list[str]] = self.settings["affiliate_products"]
        self.affiliate_pv_range: int        = self.settings["affiliate_pv_range"]
        self.real_horizon: int              = self.settings["real_horizon"]
        self.fixed_horizon: int             = self.settings["fixed_horizon"]
        self.l4n_threshold: float           = self.settings["l4n_threshold"]
        self.history_template_f: str        = self.settings["history_template"]
        self.metrics_template_f: str        = self.settings["metrics_template"]
        self.proba_pv_inf: float            = self.settings["proba_pv_inf"]
        self.pv_dependency: bool            = self.settings["pv_dependency"]
        self.ba_dependency: bool            = self.settings["ba_dependency"]
        self.pdp_dependency: bool           = self.settings["pdp_dependency"]
        self.pv_rand_strat: PvRandStrat     = PvRandStrat(self.settings["rand_pv_stat"])
        self.demand_UCMF: str               = self.settings["demand_UCMF"]
        self.reception_UCMF: str            = self.settings["reception_UCMF"]
        self.sales_UCMF: str                = self.settings["sales_UCMF"]
        self.indicators_template_f: str     = self.settings["indicators_template_f"]
        self.platform_template_f: str       = self.settings["platform_template_f"]

    def getAffiliateCode(self, aff_name) -> str:
        for code, name in self.affiliate_code.items():
            if name == aff_name:
                return code
    
    def sumOverAffiliate(self, quantity, product=None, horizon=None) -> list[int]:
        if not horizon:
            horizon = self.horizon
        if product:
            return [sum([quantity[a][product][t] for a in self.itProductAff(product)]) for t in range(horizon)]
        else:
            return {product: [sum([quantity[a][product][t] for a in self.itProductAff(product)]) for t in range(horizon)] for product in self.products}

    def itParams(self):
        for a in self.affiliate_name:
            for p in self.affiliate_products[a]:
                yield a, p

    def itProductAff(self, p):
        for a in self.affiliate_name:
            if p in self.affiliate_products[a]:
                yield a

    def dipatchSupply(self, capacity, raw_demand, a, p, t):
        if raw_demand[a][p][t] < 0:
            return 0
        tot_raw_demand = sum([raw_demand[a][p][t] for a in self.itProductAff(p) if raw_demand[a][p][t] > 0])
        if capacity[p][t] < tot_raw_demand:
            return math.floor(capacity[p][t] * raw_demand[a][p][t] / tot_raw_demand)
        else:
            return raw_demand[a][p][t]

    def dispatch(self, capacity, demand, prev_supply) -> dict[str, dict[str, list[int]]]:
        supply = {a: {p: [None] * self.horizon for p in self.affiliate_products[a]} for a in self.affiliate_name}
        raw_demand = {a: {p: [None] * self.horizon for p in self.affiliate_products[a]} for a in self.affiliate_name}        
        dept = {a: {p: [None] * self.horizon for p in self.affiliate_products[a]} for a in self.affiliate_name}
        for p in self.products:
            for t in range(self.horizon):
                for a in self.itProductAff(p):
                    raw_demand[a][p][t] = demand[a][p][t] + (dept[a][p][t-1] if t>0 else 0)
                for  a in self.itProductAff(p):
                    if t < self.fixed_horizon:
                        supply[a][p][t] = self.dipatchSupply(capacity, prev_supply, a, p, t)
                    else:
                        supply[a][p][t] = self.dipatchSupply(capacity, raw_demand, a, p, t)
                    dept[a][p][t] = raw_demand[a][p][t] - supply[a][p][t]
        return supply