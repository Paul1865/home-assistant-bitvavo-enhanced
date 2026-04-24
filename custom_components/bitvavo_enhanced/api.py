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

    def _sign(self, timestamp: str, method: str, path: str, body: str) -> str:
        # EXACT volgens Bitvavo docs:
        # timestamp + method + /v2 + endpoint + body
        prehash = f"{timestamp}{method}/v2{path}{body}"
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

        # Querystring (NIET in signature!)
        if params:
            from urllib.parse import urlencode
            url += "?" + urlencode(params)

        # Body (string)
        if body:
            body_str = json.dumps(body, separators=(",", ":"))
        else:
            body_str = ""

        headers = {}
        if private:
            ts = str(int(time.time() * 1000))
            signature = self._sign(ts, method, path, body_str)

            headers = {
                "Bitvavo-Access-Key": self._api_key,
                "Bitvavo-Access-Signature": signature,
                "Bitvavo-Access-Timestamp": ts,
                "Bitvavo-Access-Window": "60000",
            }

            if body:
                headers["Content-Type"] = "application/json"

        async with self._session.request(method, url, headers=headers, data=body_str) as resp:
            text = await resp.text()

            if resp.status == 403:
                raise Exception(f"403 Forbidden — auth mismatch: {text}")

            resp.raise_for_status()
            return json.loads(text)

    async def get_balance(self):
        return await self._request("GET", "/balance", private=True)

    async def get_staking_balance(self):
        return await self._request("GET", "/stakingBalance", private=True)

    async def get_tickers(self):
        return await self._request("GET", "/ticker/price")

    async def get_open_orders(self):
        # FIX: /ordersOpen i.p.v. /orders
        return await self._request("GET", "/ordersOpen", private=True)
