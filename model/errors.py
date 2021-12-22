class NegativeStockProjError(Exception):
    def __init__(self, entity, product, period, stock_v) -> None:
        self.entity = entity
        self.product = product
        self.period = period
        self.stock_v = stock_v
        self.msg = f"Entity {entity} reached negative proj_stock {stock_v} for product {product} at period {period}!"
        super().__init__(self.msg)