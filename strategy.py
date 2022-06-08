import logging
import os
import random
import string
from time import sleep

from pybit import usdt_perpetual
from pybit.exceptions import FailedRequestError, InvalidRequestError

from models import TradesDao
from price_cache import PriceCache

BYBIT_EXCHANGE_URL = os.environ.get('BYBIT_EXCHANGE_URL', "https://api-testnet.bybit.com")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

class Strategy:

    def __init__(self, trades_dao: TradesDao, price_cache: PriceCache):
        self.trades_dao = trades_dao
        self.price_cache = price_cache
        self.exchange_client = usdt_perpetual.HTTP(endpoint=BYBIT_EXCHANGE_URL, api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET)

    def start_strategy(self):
        while True:
            for open_conditional in self.trades_dao.list_items():
                is_conditional_already_open = bool(open_conditional["is_conditional_open"])
                is_position_already_open = bool(open_conditional["is_position_open"])
                if is_conditional_already_open or is_position_already_open:
                    continue
                symbol = str(open_conditional["symbol"])
                price = self.price_cache.read_price(symbol)
                if price is None:
                    continue
                current_price = float(price)
                target_price = float(open_conditional["open_conditional_price"])
                side = str(open_conditional["side"]).lower().capitalize()
                condition_met = False
                if side == "Buy":
                    if current_price < target_price:
                        condition_met = True
                else:
                    if current_price > target_price:
                        condition_met = True
                if condition_met:
                    # In case websockets fail for whatever reason, we should double check we don't already have the position or conditional in place
                    qty = float(open_conditional["quantity"])
                    conditional_price = float(open_conditional["trigger_price"])
                    is_valid_to_enter = self.__is_valid_entry(symbol, side, qty, conditional_price)
                    if is_valid_to_enter:
                        self.__place_order(symbol, side, qty, conditional_price, open_conditional)
            sleep(5)

    def __place_order(self, symbol: str, side: str, qty: float, conditional_price: float, open_conditional: dict):
        try:
            sl = float(open_conditional["sl_price"])
            tp = float(open_conditional["tp_price"])
            rand = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(8))
            order_id = "conditional_" + str(open_conditional["id"]) + "_" + rand
            logging.info("Condition met to open conditional trade on %s. Conditional price: %s. SL price: %s. TP price: %s. Order ID: %s", symbol, conditional_price, sl, tp, order_id)
            base_price_delta = conditional_price * 0.01
            if side == "Buy": # stop_px > market price & base_price
                base_price = conditional_price - base_price_delta
            else:  # stop_px < market price & base_price
                base_price = conditional_price + base_price_delta
            base_price = conditional_price - base_price_delta if side == "Buy" else conditional_price + base_price_delta
            precision = len(str(float(conditional_price)).split(".")[1])
            base_price = round(base_price, precision)
            self.exchange_client.place_conditional_order(symbol=symbol, side=side, order_type="Market", qty=qty, base_price=base_price, stop_px=conditional_price, time_in_force="GoodTillCancel", reduce_only=False, close_on_trigger=False, stop_loss=sl, take_profit=tp, trigger_by="LastPrice", order_link_id=order_id)
            logging.info("--------------- NEW CONDITIONAL ORDER OPENED ---------------")
            logging.info("Symbol: %s, Side: %s, Quantity: %s, Base Price: %s, Trigger Price: %s, SL Price: %s, TP Price: %s, Order ID: %s", symbol, side, qty, base_price, conditional_price, sl, tp, order_id)
        except (FailedRequestError, InvalidRequestError):
            logging.exception("Error occurred placing order with ByBit: ")
        except Exception:
            logging.exception("Unknown exception occurred constructing order: ")

    def __is_valid_entry(self, symbol: str, side: str, qty: float, conditional_price: float):
        is_conditional_exists = False
        is_position_exists = False
        try:
            # Ensure there's not already a conditional with same symbol, side, quantity and trigger price
            conditional_orders = self.exchange_client.query_conditional_order(symbol=symbol)
            if conditional_orders is not None:
                result = conditional_orders["result"]
                is_conditional_exists = len([x for x in result if side == str(x["side"]) and qty == float(x["qty"]) and float(x["trigger_price"]) == conditional_price]) > 0
            # Ensure there's not already a position with same symbol and side
            open_positions = self.exchange_client.my_position(symbol=symbol)
            if open_positions is not None:
                result = open_positions["result"]
                is_position_exists = len([x for x in result if side == str(x["side"]) and float(x["size"]) > 0]) > 0
        except (FailedRequestError, InvalidRequestError):
            logging.exception("Error occurred querying existing conditional/position orders on ByBit. Will not place new conditional order: ")
            return False
        except Exception:
            logging.exception("Unknown exception occurred constructing order query. Will not place new conditional order: ")
            return False
        return not is_conditional_exists and not is_position_exists
