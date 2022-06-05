import logging
import os
from typing import Dict, List

from pybit import usdt_perpetual

from models import TradesDao
from price_cache import PriceCache

BYBIT_TESTNET_EXCHANGE = bool(os.getenv("BYBIT_TESTNET_EXCHANGE", True))
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

class WebsocketStreams:

    def __init__(self, price_cache: PriceCache, trades_dao: TradesDao):
        self.price_cache = price_cache
        self.trades_dao = trades_dao
        self.active_symbols = set()
        self.prices = {}
        self.websocket = usdt_perpetual.WebSocket(test=BYBIT_TESTNET_EXCHANGE, api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET)

    def subscribe_to_price_stream(self, symbols: List[str]):
        for symbol in symbols:
            logging.info("Subscribing %s to price stream", symbol)
            self.active_symbols.add(symbol)
            self.subscribe(symbol=symbol)
        return self.active_symbols
    
    def subscribe(self, symbol):
        self.websocket.instrument_info_stream(self.__handle_instrument_info, symbol)

    def start_position_listener(self):
        self.websocket.position_stream(self.__handle_position_update)
        self.websocket.stop_order_stream(self.__handle_stop_order_update)
        self.websocket.order_stream(self.__handle_order_update)

    def __handle_instrument_info(self, message):
        try:
            symbol = message["data"]["symbol"]
            price = message["data"]["last_price"]
            self.prices[symbol] = price
            self.price_cache.upsert_price(symbol, price)
        except Exception:
            logging.exception("Exception occurred handling price update: ")

    def __handle_position_update(self, message):
        logging.info("- POSITION UPDATE -")
        logging.info(message)
        try:
            data: List[Dict] = message["data"]
            if data is None or len(data) == 0:
                logging.warning("No data received in position update message: %s", message)
                return
            open_positions = [update for update in data if float(update["size"]) > 0]
            closed_positions = [update for update in data if float(update["size"]) == 0]
            # If there are no open positions, it indicates that the position is now closed and we should ensure the DB reflects this
            for closed_position in closed_positions:
                symbol = closed_position["symbol"]
                side = closed_position["side"]
                matching_trades = self.trades_dao.query_trades(symbol=symbol, side=side)
                db_open_positions = [trade for trade in matching_trades if trade["is_position_open"]]
                for open_position in db_open_positions:
                    row_id = open_position["id"]
                    self.trades_dao.update(row_id, params={"is_position_open": False})
            
            for open_position in open_positions:
                # Ensure DB reflects that this position is open
                symbol = open_position["symbol"]
                side = open_position["side"]
                qty = open_position["size"]
                matched_trades = self.trades_dao.query_trades(symbol, side, qty)
                for matched_trade in matched_trades:
                    row_id = matched_trade["id"]
                    self.trades_dao.update(row_id, params={"is_position_open": True})
        except Exception:
            logging.exception("Exception occurred handling position update: ")
        
    def __handle_stop_order_update(self, message):
        logging.info("- STOP ORDER UPDATE -")
        logging.info(message)
        try:
            data: List[Dict] = message["data"]
            if data is None or len(data) == 0:
                logging.warning("No data received in stop order update message: %s", message)
                return
            for update in data:
                # Handle placement of conditional stop orders
                order_id = str(update["order_link_id"])
                is_conditional_order = '_' in order_id and order_id.split('_')[0] == "conditional"
                if is_conditional_order:
                    logging.info("Found conditional order update")
                    # If the conditional order has an order status of untriggered, it indicates the conditional order is pending and we should update the DB accordingly
                    row_id = order_id.split('_')[1]
                    is_open = update["order_status"] == "Untriggered"
                    self.trades_dao.update(row_id, params={"is_conditional_open": is_open})
                    # If the user manually cancels the conditional order, then deactivate the trade from entering again
                    is_cancelled = update["cancel_type"] == "CancelByUser" and update["order_status"] == "Deactivated"
                    if is_cancelled:
                        self.trades_dao.deactivate_trade(row_id)
        except Exception:
            logging.exception("Exception occurred handling stop order update: ")

    def __handle_order_update(self, message):
        logging.info("- ORDER UPDATE -")
        logging.info(message)
        try:
            data: List[Dict] = message["data"]
            if data is None or len(data) == 0:
                logging.warning("No data received in order update message: %s", message)
                return
            for update in data:
                flipped_side = self.__flip_side(str(update["side"]))
                symbol = update["symbol"]
                create_type = update["create_type"]
                order_status = update["order_status"]
                order_id = update["order_link_id"]
                matching_trades = [trade for trade in self.trades_dao.query_trades(symbol=symbol, side=flipped_side) if not trade["is_conditional_open"]]
                # If any part of the position is closed out by non-StopLoss type orders, then deactivate trade completely.
                # By not deactivating for CreateByStopLoss orders here it will cause the conditional order to be re-entered automatically.
                if "Filled" in order_status and "CreateByStopLoss" not in create_type and not order_id:
                    logging.info("Received update for FILLED order of type: %s. Will deactivate trade", create_type)
                    for matching_trade in matching_trades:
                        row_id = matching_trade["id"]
                        logging.info("Deactivating trade: %s", row_id)
                        self.trades_dao.deactivate_trade(row_id)
                # If it's a StopLoss order, then increment the SL count in the DB
                elif "Filled" in order_status:
                    logging.info("Received update for FILLED order of type: %s. Will increment StopLoss counter", create_type)
                    for matching_trade in matching_trades:
                        row_id = matching_trade["id"]
                        logging.info("Incrementing SL counter for trade ID: %s", row_id)
                        updated_row = self.trades_dao.increment_sl_counter(row_id)
                        if int(updated_row["sl_counter"]) >= int(updated_row["max_sl_count"]):
                            logging.info("Max StopLoss count has been reached. Deactivating trade: %s", row_id)
                            self.trades_dao.deactivate_trade(row_id)
        except Exception:
            logging.exception("Exception occurred handling stop order update: ")
            
    def __flip_side(self, side: str) -> str:
        return "Sell" if "buy" in side.lower() else "Buy"

    
