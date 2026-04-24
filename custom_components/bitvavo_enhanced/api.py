import time
import hmac
import hashlib
import json
from typing import Any, Dict, Optional

import aiohttp


BASE_URL = "https://api.bitvavo.com/v2"


class BitvavoAPI:
    def __init__(self, api_key: str, api_secret: str, session: aiohttp.ClientSession):
        self._api_key = api_key
        self._api_secret = api_secret.encode("utf-8")
        self._session = session

    def _sign(self, timestamp: str, method: str, path: str, query: str, body: str) -> str:
        prehash = f"{timestamp}{method}{path}{query}{body}"
        return hmac.new(self._api_secret, prehash.encode("utf-8"), hashlib.sha256).hexdigest()

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        private: bool = False,
    ) -> Any:
        url = BASE_URL + path
        query = ""
        if params:
            # Bitvavo verwacht querystring in signing
            from urllib.parse import urlencode
            query = "?" + urlencode(params)
            url += query

        data = ""
        json_body = None
        if body:
            data = json.dumps(body, separators=(",", ":"))
            json_body = body

        headers = {}
        if private:
            ts = str(int(time.time() * 1000))
            signature = self._sign(ts, method, path, query, data)
            headers = {
                "Bitvavo-Access-Key": self._api_key,
                "Bitvavo-Access-Signature": signature,
                "Bitvavo-Access-Timestamp": ts,
                "Bitvavo-Access-Window": "60000",
                "Content-Type": "application/json",
            }

        async with self._session.request(method, url, headers=headers, json=json_body) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_balance(self):
        return await self._request("GET", "/balance", private=True)

    async def get_staking_balance(self):
        return await self._request("GET", "/stakingBalance", private=True)

    async def get_tickers(self):
        return await self._request("GET", "/ticker/price")

    async def get_open_orders(self):
        return await self._request("GET", "/orders", private=True)
