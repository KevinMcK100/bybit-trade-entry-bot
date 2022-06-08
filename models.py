import logging
import sqlite3
from typing import Dict, List


class Schema:
    def __init__(self):
        self.conn = sqlite3.connect('trades.db', check_same_thread=False)
        self.create_trades_table()

    def __del__(self):
        self.conn.commit()
        self.conn.close()

    def create_trades_table(self):

        query = """
        CREATE TABLE IF NOT EXISTS "trades" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            side TEXT,
            quantity REAL,
            open_conditional_price REAL,
            trigger_price REAL,
            sl_price REAL,
            tp_price REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            max_sl_count INTEGER DEFAULT 1,
            sl_counter INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            is_position_open BOOLEAN DEFAULT 0,
            is_conditional_open BOOLEAN DEFAULT 0
        );
        """
        c = self.conn.cursor()
        c.execute(query)
        self.conn.commit()


class TradesDao:

    def __init__(self):
        self.conn = sqlite3.connect('trades.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def __del__(self):
        self.conn.commit()
        self.conn.close()

    def get_by_id(self, row_id, is_active: bool = True) -> dict:
        c = self.conn.cursor()
        trades = c.execute("SELECT * FROM trades WHERE is_active=? and id=? LIMIT 1", (int(is_active), row_id,)).fetchall()
        self.conn.commit()
        result = {} if trades is None or len(trades) == 0 else trades[0]
        return dict(result)

    def create(self, params) -> dict:
        trade = (params.get("symbol"), params.get("side"), params.get("quantity"), params.get("open_conditional_price"), params.get("trigger_price"), params.get("sl_price"), params.get("tp_price"), params.get("max_sl_count", 1))
        c = self.conn.cursor()
        insert_result = c.execute('insert into trades (symbol, side, quantity, open_conditional_price, trigger_price, sl_price, tp_price, max_sl_count) values (?,?,?,?,?,?,?,?)', trade)
        self.conn.commit()
        return self.get_by_id(insert_result.lastrowid)

    def update(self, row_id, params: dict) -> dict:
        if row_id is None:
            logging.warning("No row ID provided to update function. Nothing to update for params: %s", params)
            return {}
        if params is None or len(params) == 0:
            logging.warning("No params passed to update function. Nothing to updated. Row ID: %s", row_id)
            return {}
        set_query = ""
        update_tuple = ()
        separator = ""
        if params.get("is_active") is not None:
            set_query = set_query + separator + " is_active=?"
            update_tuple = update_tuple + (params.get("is_active"),)
            separator = ","
        if params.get("is_position_open") is not None:
            set_query = set_query + separator + " is_position_open=?"
            update_tuple = update_tuple + (params.get("is_position_open"),)
            separator = ","
        if params.get("is_sl_hit") is not None:
            set_query = set_query + separator + " is_sl_hit=?"
            update_tuple = update_tuple + (params.get("is_sl_hit"),)
            separator = ","
        if params.get("is_conditional_open") is not None:
            set_query = set_query + separator + " is_conditional_open=?"
            update_tuple = update_tuple + (params.get("is_conditional_open"),)
            separator = ","
        if len(update_tuple) == 0:
            logging.warning("Invalid params passed to update function. Nothing to updated. Row ID: %s", row_id)
            return {}
        query = "UPDATE trades SET" + set_query + " WHERE id=?"
        update_tuple = update_tuple + (row_id,)
        c = self.conn.cursor()
        c.execute(query, update_tuple)
        self.conn.commit()
        return self.get_by_id(row_id)

    def deactivate_trade(self, row_id) -> dict:
        c = self.conn.cursor()
        c.execute("UPDATE trades SET is_active=? WHERE id=?", (0, row_id))
        self.conn.commit()
        return self.get_by_id(row_id, False)

    def increment_sl_counter(self, row_id) -> dict:
        c = self.conn.cursor()
        c.execute("UPDATE trades SET sl_counter=sl_counter+1 WHERE id=?", (row_id,))
        self.conn.commit()
        result = self.get_by_id(row_id)
        return result

    def list_items(self) -> List[Dict]:
        c = self.conn.cursor()
        result_set = c.execute("SELECT * FROM trades WHERE is_active=?", (1,)).fetchall()
        self.conn.commit()
        result = [{column: row[i]
                  for i, column in enumerate(result_set[0].keys())}
                  for row in result_set]
        return result
    
    def query_trades(self, symbol: str = None, side: str = None, qty: float = None) -> List[Dict]:
        c = self.conn.cursor()
        query_tuple = (1,)
        query = "SELECT * FROM trades WHERE is_active=?"
        if symbol:
            query = query + " and symbol=? COLLATE NOCASE"
            query_tuple = query_tuple + (symbol,)
        if side:
            query = query + " and side=? COLLATE NOCASE"
            query_tuple = query_tuple + (side,)
        if qty:
            query = query + " and quantity=?"
            query_tuple = query_tuple + (qty,)
        query_result = c.execute(query, query_tuple).fetchall()
        self.conn.commit()
        result = [{column: row[i]
                  for i, column in enumerate(query_result[0].keys())}
                  for row in query_result]
        return result
