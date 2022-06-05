import logging
import os
import threading
from functools import wraps
from pprint import pprint
from time import sleep
from typing import List

from flask import Flask, jsonify, request

from models import Schema, TradesDao
from price_cache import PriceCache
from rest_service import RestService
from strategy import Strategy
from websocket_streams import WebsocketStreams

FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT = os.environ.get('FLASK_PORT', 5000)

logging.basicConfig(filename="tradebot.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

app = Flask(__name__)

def require_api_key(api_method):
    @wraps(api_method)

    def check_api_key(*args, **kwargs):
        apikey = request.headers.get("api_key")
        if apikey and apikey == os.getenv("BOT_API_KEY"):
            return api_method(*args, **kwargs)
        else:
            response = jsonify({'message':'Unauthorised'})
            return response, 401

    return check_api_key

@app.after_request
def add_headers(response):
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Access-Control-Allow-Headers'] =  "Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With"
    response.headers['Access-Control-Allow-Methods']=  "POST, GET, PUT, DELETE, OPTIONS"
    return response


@app.route("/trade", methods=["GET"])
@require_api_key
def list_trade():
    return jsonify(RestService().list())


@app.route("/trade", methods=["POST"])
@require_api_key
def create_trade():
    return jsonify(RestService().create(request.get_json()))


@app.route("/trade/<item_id>", methods=["PUT"])
@require_api_key
def update_item(item_id):
    return jsonify(RestService().update(item_id, request.get_json()))

@app.route("/trade/<item_id>", methods=["GET"])
@require_api_key
def get_item(item_id):
    return jsonify(RestService().get_by_id(item_id))

@app.route("/trade/<item_id>", methods=["DELETE"])
@require_api_key
def delete_item(item_id):
    return jsonify(RestService().delete(item_id))

def print_cache(prices: PriceCache):
    while True:
        pprint(prices.read_all_prices())
        sleep(5)

def sync_stream(prices: PriceCache, trade_model: TradesDao, websockets: WebsocketStreams, starting_symbols: List[str]):
    if starting_symbols is not None and len(starting_symbols) > 0:
        logging.info("Waiting for prices to load for %s", starting_symbols)
        for symbol in starting_symbols:
            while prices.read_price(symbol) is None:
                sleep(1)
        logging.info("Prices for %s loaded", starting_symbols)
        
    while True:
        for open_conditional in trade_model.list_items():
            symbol = open_conditional["symbol"]
            if prices.read_price(symbol) is None:
                logging.info("Found new symbol. Subscribing to price stream for %s", symbol)
                websockets.subscribe(symbol)
        sleep(10)


if __name__ == "__main__":
    Schema()
    trades_model = TradesDao()
    symbols = set(x["symbol"] for x in trades_model.list_items())
    if len(symbols) > 0:
        logging.info("Starting bot. Found existing active trades. Will start monitoring symbols: %s", symbols)
    else:
        logging.info("Starting bot. No existing active trades found")
    price_cache = PriceCache()
    price_stream = WebsocketStreams(price_cache, trades_model) 
    price_stream.subscribe_to_price_stream(symbols)
    price_stream.start_position_listener()
    
    print_cache_worker = threading.Thread(target=print_cache, args=(price_cache,))
    print_cache_worker.start()

    sync_stream_worker = threading.Thread(target=sync_stream, args=(price_cache, trades_model, price_stream, symbols))
    sync_stream_worker.start()

    strategy = Strategy(trades_model, price_cache)
    strategy_worker = threading.Thread(target=strategy.start_strategy)
    strategy_worker.start()

    app.run(host=FLASK_HOST, port=FLASK_PORT)
