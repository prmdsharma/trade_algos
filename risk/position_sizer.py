# [cite_start]Source: [cite: 41-44]

class PositionSizer:
    def __init__(self, config):
        self.capital = config['account']['initial_capital']
        self.risk_per_trade = config['risk']['risk_per_trade_pct'] # 1%
        self.stop_loss_pct = config['trade_params']['stop_loss_pct'] # 8%
        self.fixed_qty = config['trade_params'].get('fixed_qty')

    def calculate_qty(self, premium_price):
        """
        Example: Capital 5L -> Risk 5k -> Exposure 62.5k
        """
        if self.fixed_qty is not None:
            return self.fixed_qty

        risk_amount = self.capital * self.risk_per_trade
        total_exposure = risk_amount / self.stop_loss_pct
        qty = int(total_exposure / premium_price)
        return qty