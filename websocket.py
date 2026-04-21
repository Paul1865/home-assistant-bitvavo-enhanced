import json
import logging
import websockets

_LOGGER = logging.getLogger(__name__)

WS_URL = "wss://ws.bitvavo.com/v2/"


class BitvavoWebsocket:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    async def connect(self):
        async with websockets.connect(WS_URL) as ws:
            await ws.send(json.dumps({
                "action": "subscribe",
                "channels": [{"name": "ticker", "markets": ["*"]}]
            }))

            while True:
                msg = await ws.recv()
                data = json.loads(msg)

                if isinstance(data, dict) and "event" in data:
                    continue

                for ticker in data:
                    market = ticker["market"]
                    price = float(ticker["price"])

                    if market in self.coordinator.data["tickers"]:
                        self.coordinator.data["tickers"][market]["price"] = price

                self.coordinator.async_set_updated_data(self.coordinator.data)