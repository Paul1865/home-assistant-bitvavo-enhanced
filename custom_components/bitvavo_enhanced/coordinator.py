import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from bitvavo.BitvavoClient import BitvavoClient

from .const import CONF_BALANCES, CONF_TICKERS, CONF_ORDERS

_LOGGER = logging.getLogger(__name__)


class BitvavoCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api_key, api_secret):
        super().__init__(
            hass,
            _LOGGER,
            name="bitvavo_enhanced",
            update_interval=timedelta(seconds=60),
        )

        self.client = BitvavoClient(api_key, api_secret)

    # ---------------------------------------------------------
    # EUR PRICE LOOKUP
    # ---------------------------------------------------------
    def _get_eur_price(self, symbol, tickers):
        # EUR heeft altijd prijs 1
        if symbol == "EUR":
            return 1.0

        # 1. Direct EUR pair
        direct = f"{symbol}-EUR"
        if direct in tickers:
            return float(tickers[direct]["price"])

        # 2. USDT fallback
        usdt_pair = f"{symbol}-USDT"
        if usdt_pair in tickers and "USDT-EUR" in tickers:
            return float(tickers[usdt_pair]["price"]) * float(tickers["USDT-EUR"]["price"])

        # 3. BTC fallback
        btc_pair = f"{symbol}-BTC"
        if btc_pair in tickers and "BTC-EUR" in tickers:
            return float(tickers[btc_pair]["price"]) * float(tickers["BTC-EUR"]["price"])

        return None

    # ---------------------------------------------------------
    # MAIN UPDATE LOOP
    # ---------------------------------------------------------
    async def _async_update_data(self):
        balances_raw = await self.client.get_balance()
        tickers_raw = await self.client.get_price_ticker()
        orders_raw = await self.client.get_open_orders()
        staking_raw = await self.client.staking()

        # Maak tickers dictionary: {"BTC-EUR": {...}, ...}
        tickers_map = {t["market"]: t for t in tickers_raw}

        portfolio = {}

        # ---------------------------------
        # 1. BALANCES + FLEXIBLE STAKING
        # ---------------------------------
        for b in balances_raw:
            symbol = b.get("symbol")

            available = float(b.get("available", 0) or 0)
            in_order = float(b.get("inOrder", 0) or 0)
            staked = float(b.get("staked", 0) or 0)  # FLEXIBLE
            lent = float(b.get("lent", 0) or 0)

            portfolio[symbol] = {
                "available": available,
                "inOrder": in_order,
                "staked_flexible": staked,
                "staked_fixed": 0.0,  # vullen we zo
                "lent": lent,
                "orders": [],
            }

        # ---------------------------------
        # 2. FIXED STAKING TOEVOEGEN
        # ---------------------------------
        for s in staking_raw:
            symbol = s.get("symbol")
            amount = float(s.get("amount", 0) or 0)

            if symbol not in portfolio:
                portfolio[symbol] = {
                    "available": 0,
                    "inOrder": 0,
                    "staked_flexible": 0,
                    "staked_fixed": 0,
                    "lent": 0,
                    "orders": [],
                }

            portfolio[symbol]["staked_fixed"] += amount

        # ---------------------------------
        # 3. TOTAL + EUR VALUE
        # ---------------------------------
        for symbol, data in portfolio.items():
            total = (
                data["available"]
                + data["inOrder"]
                + data["staked_flexible"]
                + data["staked_fixed"]
                + data["lent"]
            )

            data["total"] = total

            eur_price = self._get_eur_price(symbol, tickers_map)
            if eur_price:
                data["eur_price"] = eur_price
                data["eur_value"] = eur_price * total
            else:
                data["eur_price"] = None
                data["eur_value"] = None

        # ---------------------------------
        # 4. OPEN ORDERS
        # ---------------------------------
        for o in orders_raw:
            market = o.get("market", "")
            if "-" not in market:
                continue

            base, quote = market.split("-")

            if base not in portfolio:
                portfolio[base] = {
                    "available": 0,
                    "inOrder": 0,
                    "staked_flexible": 0,
                    "staked_fixed": 0,
                    "lent": 0,
                    "orders": [],
                    "total": 0,
                    "eur_price": None,
                    "eur_value": None,
                }

            portfolio[base]["orders"].append(o)

        return {
            CONF_BALANCES: portfolio,
            CONF_TICKERS: tickers_map,
            CONF_ORDERS: orders_raw,
            "raw_portfolio": portfolio,
        }
