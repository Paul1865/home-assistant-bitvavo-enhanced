import json
import os

STORAGE_FILE = "/config/.storage/bitvavo_cost_basis.json"


class CostBasisStorage:
    def __init__(self):
        self.data = {}

    def load(self):
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, "r") as f:
                self.data = json.load(f)
        return self.data

    def save(self):
        with open(STORAGE_FILE, "w") as f:
            json.dump(self.data, f, indent=2)

    def get(self, symbol):
        return self.data.get(symbol, {"amount": 0.0, "cost": 0.0})

    def update(self, symbol, amount, cost):
        self.data[symbol] = {
            "amount": amount,
            "cost": cost,
        }