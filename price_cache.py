import os
from typing import Dict, List, Optional

import redis

REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_PORT = os.environ.get('REDIS_PORT', 6379)

class PriceCache:

    def __init__(self):
        self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.redis.flushall()
    
    def upsert_price(self, symbol: str, price: float):
        return self.redis.set(symbol, price)
    
    def read_price(self, symbol: str) -> Optional[float]:
        return self.redis.get(symbol)

    def read_all_prices(self) -> List[Dict]:
        return [{key: self.redis.get(key)} for key in self.redis.keys('*')]
