import json
from typing import Any, Tuple
import enum
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
        self.factory_capacity: list[int]    = self.settings["factory_capacity"]
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
    
    def sumOverAffiliate(self, quantity, product, horizon) -> list[int]:
        return [sum([quantity[a][product][t] for a in self.itProductAff(product)]) for t in range(horizon)]

    def itParams(self):
        for a in self.affiliate_name:
            for p in self.affiliate_products[a]:
                yield a, p

    def itProductAff(self, p):
        for a in self.affiliate_name:
            if p in self.affiliate_products[a]:
                yield a
    
    def dispatch(self, capacity, demand, prev_supply) -> dict[str, dict[str, list[int]]]:
        supply_plan = {a: {p: [None] * self.horizon for p in self.affiliate_products[a]} for a in self.affiliate_name}
        unavailability = {a: {p: [None] * self.horizon for p in self.affiliate_products[a]} for a in self.affiliate_name}
        supply_ratio = {a: {p: [None] * self.horizon for p in self.affiliate_products[a]} for a in self.affiliate_name}

        for a, p in self.itParams():
            supply_plan[a][p][:self.fixed_horizon] = prev_supply[a][p][:self.fixed_horizon]
            unavailability[a][p][0] = demand[a][p][0] - supply_plan[a][p][0]
            raw_need_a_p_0 = sum([demand[a][p][0] for a in self.itProductAff(p)])
            supply_ratio[a][p][0] = demand[a][p][0] / raw_need_a_p_0 if raw_need_a_p_0 != 0 else 0

        for t in range(1, self.horizon):
            for a, p in self.itParams():
                raw_need_a_p_t = sum([demand[a][p][t] + unavailability[a][p][t-1] for a in self.itProductAff(p)])
                supply_ratio[a][p][t] = (demand[a][p][t] + unavailability[a][p][t-1]) / raw_need_a_p_t if raw_need_a_p_t != 0 else 0
                if t >= self.fixed_horizon:
                    supply_plan[a][p][t] = round(min(capacity[p][t] * supply_ratio[a][p][t], demand[a][p][t] + unavailability[a][p][t-1]))
                unavailability[a][p][t] = unavailability[a][p][t-1] + demand[a][p][t] - supply_plan[a][p][t]
        return supply_plan