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

        # Maak tickers dictionary: {"BTC-EUR": {...}, ...}
        tickers_map = {t["market"]: t for t in tickers_raw}

        portfolio = {}

        # ---------------------------------
        # 1. BALANCES + STAKING
        # ---------------------------------
        for b in balances_raw:
            symbol = b.get("symbol")

            available = float(b.get("available", 0) or 0)
            in_order = float(b.get("inOrder", 0) or 0)
            staked = float(b.get("staked", 0) or 0)
            lent = float(b.get("lent", 0) or 0)

            total = available + in_order + staked + lent

            portfolio[symbol] = {
                "available": available,
                "inOrder": in_order,
                "staked": staked,
                "lent": lent,
                "orders": [],
                "total": total,
            }

            # EUR prijs + waarde
            eur_price = self._get_eur_price(symbol, tickers_map)
            if eur_price:
                portfolio[symbol]["eur_price"] = eur_price
                portfolio[symbol]["eur_value"] = eur_price * total
            else:
                portfolio[symbol]["eur_price"] = None
                portfolio[symbol]["eur_value"] = None

        # ---------------------------------
        # 2. OPEN ORDERS (correct mapped)
        # ---------------------------------
        for o in orders_raw:
            market = o.get("market", "")
            if "-" not in market:
                continue

            base, quote = market.split("-")

            portfolio.setdefault(base, {
                "available": 0,
                "inOrder": 0,
                "staked": 0,
                "lent": 0,
                "orders": [],
                "total": 0,
                "eur_price": None,
                "eur_value": None,
            })

            portfolio[base]["orders"].append({
                "market": market,
                "side": o.get("side"),
                "amount": o.get("amount"),
                "price": o.get("price"),
                "status": o.get("status"),
            })

        # ---------------------------------
        # 3. CLEAN OUTPUT
        # ---------------------------------
        display_portfolio = {
            k: v for k, v in portfolio.items()
            if v["total"] > 0 or len(v["orders"]) > 0
        }

        return {
            CONF_BALANCES: display_portfolio,
            CONF_TICKERS: tickers_map,
            CONF_ORDERS: orders_raw,
            "raw_portfolio": portfolio,
        }
