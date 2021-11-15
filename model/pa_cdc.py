class PA_CDC:
    def __init__(self, model) -> None:
        self.model = model
        self.raw_need = {p: [None for _ in range(model.horizon)] for p in model.products}
        self.unavailability = {a: {p: [0] * model.horizon for p in model.products} for a in model.affiliates.keys()}
        self.possible_to_promise = {p: [None] * model.horizon for p in model.products}
        self.initial_stock = self.model.cbn_cdc.initial_stock
        self.projected_stock = {p: [None] * model.horizon for p in model.products}
        self.supply_plan = {a: {p: [0] * model.horizon for p in aff.products} for a, aff in model.affiliates.items()}
        self.calculate_pa = True
        if model.week % 4 == 1:
            self.prod_plan = model.factory.prod_plan
        else:
            self.prod_plan = model.prev_prod_plan 
        
    def run(self):
        prod_t = self.model.prod_time
        self.supply_demand = self.model.cbn_cdc.total_supply_demand
        total_prev_supply_plan = {p: [sum([self.model.prev_supply_plan[a][p][t+aff.delivery_time] 
            if t + aff.delivery_time < self.model.horizon else 0
            for a, aff in self.model.affiliates.items() if p in aff.products])
                for t in range(self.model.horizon)]
                    for p in self.model.products}
        
        for a, affiliate in self.model.affiliates.items():
            for p in affiliate.products:
                if self.calculate_pa:
                    self.supply_plan[a][p][0] = self.model.prev_supply_plan[a][p][0 + affiliate.delivery_time]
                    self.supply_plan[a][p][1] = self.model.prev_supply_plan[a][p][1 + affiliate.delivery_time]
                self.unavailability[a][p][0] = affiliate.supply_demand[p][0 + affiliate.delivery_time] - self.supply_plan[a][p][0]
        
        for p in self.model.products:
            self.raw_need[p][0] = self.supply_demand[p][0]
            self.possible_to_promise[p][0] = total_prev_supply_plan[p][0]
            total_supply_plan = sum([self.supply_plan[a][p][0] if p in aff.products else 0 for a, aff in self.model.affiliates.items()])
            self.projected_stock[p][0] = self.initial_stock[p] + self.model.cbn_cdc.queued_prod[p][0] - total_supply_plan

        for t in range(1, self.model.horizon):
            for p in self.model.products:
                total_unavailability = sum([self.unavailability[a][p][t-1] for a, aff in self.model.affiliates.items() if p in aff.products])
                self.raw_need[p][t] = self.supply_demand[p][t] + total_unavailability
                
            for p in self.model.products:
                planed_prod = self.prod_plan[p][t - prod_t] if t >= prod_t else 0
                total_supply_plan = sum([self.supply_plan[a][p][t] for a, aff in self.model.affiliates.items() if p in aff.products])
                self.projected_stock[p][t] = self.projected_stock[p][t-1] + planed_prod + self.model.cbn_cdc.queued_prod[p][t] - total_supply_plan
                if t < 2:
                    self.possible_to_promise[p][t] = total_prev_supply_plan[p][t]
                else:
                    self.possible_to_promise[p][t] = max(min(self.raw_need[p][t], planed_prod + self.model.cbn_cdc.queued_prod[p][t] + self.projected_stock[p][t-1]), 0)
            
            for a, affiliate in self.model.affiliates.items(): 
                for p in affiliate.products:
                    if self.calculate_pa and t >= 2:
                        if self.raw_need[p][t] > 0:
                            supply_ratio = (self.model.cbn_cdc.supply_demand[a][p][t] + self.unavailability[a][p][t-1]) / self.raw_need[p][t]
                            self.supply_plan[a][p][t] = max(round(supply_ratio * self.possible_to_promise[p][t]), 0)
                        else: 
                            self.supply_plan[a][p][t] = 0
                    self.unavailability[a][p][t] = self.unavailability[a][p][t-1] + self.model.cbn_cdc.supply_demand[a][p][t] - self.supply_plan[a][p][t] 
    
