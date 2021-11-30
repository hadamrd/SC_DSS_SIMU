import json
from typing import Any, Tuple


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