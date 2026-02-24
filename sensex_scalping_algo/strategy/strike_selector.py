# [cite_start]Source: [cite: 23-24]

class StrikeSelector:
    @staticmethod
    def get_atm_strike(spot_price):
        """
        Logic: Round spot price to nearest 100.
        """
        return round(spot_price / 100) * 100