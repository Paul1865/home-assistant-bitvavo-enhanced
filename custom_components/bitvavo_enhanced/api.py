import aiohttp
import asyncio
import time
import hmac
import hashlib
import logging
import json
from urllib.parse import urlencode

_LOGGER = logging.getLogger(__name__)


class BitvavoAPI:
    BASE_URL = "https://api.bitvavo.com"

    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret.encode()
        self.session = aiohttp.ClientSession()

        self._lock = asyncio.Lock()
        self._last_call = 0.0
        self._min_interval = 0.2  # seconds

        self._cache: dict[str, dict] = {}

    async def _request(self, method: str, endpoint: str, params=None, body=None):
        query = ""
        if params:
            query = "?" + urlencode(params)

        body_str = ""
        if body:
            body_str = json.dumps(body, separators=(",", ":"))

        async with self._lock:
            now = time.time()
            wait = self._min_interval - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.time()

        url = f"{self.BASE_URL}{endpoint}{query}"

        timestamp = str(int(time.time() * 1000))
        message = timestamp + method + endpoint + query + body_str

        signature = hmac.new(
            self.api_secret,
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Bitvavo-Access-Key": self.api_key,
            "Bitvavo-Access-Signature": signature,
            "Bitvavo-Access-Timestamp": timestamp,
            "Bitvavo-Access-Window": "10000",
            "Content-Type": "application/json",
        }

        try:
            async with self.session.request(method, url, headers=headers, data=body_str) as resp:
                text = await resp.text()

                if resp.status != 200:
                    _LOGGER.error("API error (%s) for %s: %s", resp.status, endpoint, text)
                    return None

                try:
                    return await resp.json()
                except Exception:
                    _LOGGER.error("JSON decode error for %s: %s", endpoint, text)
                    return None

        except Exception as err:
            _LOGGER.error("Request exception for %s: %s", endpoint, err)
            return None

    def _get_cache(self, key: str, ttl: float):
        entry = self._cache.get(key)
        if entry and time.time() - entry["time"] < ttl:
            return entry["data"]
        return None

    def _set_cache(self, key: str, data):
        self._cache[key] = {"data": data, "time": time.time()}

    async def get_tickers(self):
        cache = self._get_cache("tickers", 5)
        if cache:
            return cache

        data = await self._request("GET", "/v2/ticker/price")
        if data:
            self._set_cache("tickers", data)
        return data

    async def get_balance(self):
        return await self._request("GET", "/v2/balance")

    async def get_staking_balance(self):
        return await self._request("GET", "/v2/stakingBalance")

    async def get_open_orders(self):
        return await self._request("GET", "/v2/ordersOpen")

    async def get_trades_for_market(self, market: str):
        return await self._request("GET", "/v2/trades", params={"market": market})

    async def get_all_trades(self, markets: list[str]):
        all_trades: list[dict] = []
        for market in markets:
            trades = await self.get_trades_for_market(market)
            if trades:
                all_trades.extend(trades)
        return all_trades

    async def close(self):
        if not self.session.closed:
            await self.session.close()
