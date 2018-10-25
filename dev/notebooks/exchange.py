import gdax
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

class TwistyBook(gdax.WebsocketClient):
    def __init__(self, product, shutdown_func=None):
        super().__init__(channels=["level2", "matches"])
        self.products = product
        self.sell_fn = None
        self.buy_fn = None
        self.stop_func = shutdown_func
        self.last_buy = None
        self.last_sell = None
        self.buy = {}
        self.sell = {}
        
    def on_open(self):
        print("Connected to websocket")
        
    def _snapshot(self, msg):
        for ask in msg['asks']:
            self.sell[float(ask[0])] = ask[1]
        for bid in msg['bids']:
            self.buy[float(bid[0])] = bid[1]
        self.last_buy = self._bid()
        self.last_sell = self._ask()
        print("Exchange Sychronised")

    def on_message(self, msg):
        if not 'type' in msg:
            return
        
        if msg['type'] == 'snapshot':
            print("Snapshot")
            self._snapshot(msg)
            
        elif msg['type'] == 'l2update':
            for change in msg['changes']:
                price = float(change[1])
                if change[0] == 'sell':
                    if float(change[2]):
                        self.sell[price] = change[2]
                        if price < self.last_sell:
                            if self.sell_fn:
                                self.sell_fn(old_price=self.last_sell, new_price=price)
                            self.last_sell = price
                    else:
                        del self.sell[price]
                        if price == self.last_sell:
                            self.last_sell = self._ask()
                            if self.sell_fn:
                                self.sell_fn(old_price=price, new_price=self.last_sell)
                else:
                    if float(change[2]):
                        self.buy[price] = change[2]
                        if price > self.last_buy:
                            if self.buy_fn:
                                self.buy_fn(old_price=self.last_buy, new_price=price)
                            self.last_buy = price
                    else:
                        del self.buy[price]
                        if price == self.last_buy:
                            self.last_buy = self._bid()
                            if self.buy_fn:
                                self.buy_fn(old_price=price, new_price=self.last_buy)

        elif msg['type'] == 'match' and 'user_id' in msg:
            print('Match: '.format(msg))

    def on_close(self):
        print("-- Goodbye! --")
        if self.stop_func:
            self.stop_func()
        
    def _bid(self):
        return max(self.buy, key=float)
    
    def _ask(self):
        return min(self.sell, key=float)
    
    def bid(self):
        return self.last_buy
    
    def ask(self):
        return self.last_sell

    
class PurchaseEngine:
    def __init__(self, product, client, book, hold_back=0.0):
        self.product = product
        self.client = client
        self.book = book
        self.fiat_bal = None
        self.cryp_bal = None
        self.fiat_avail = None
        self.cryp_avail = None
        self._get_balance()
        self.buying = None
        self.pool = None
        self.hold_back = hold_back
        self.active_futures = []
        
    def start(self):
        self.book.start()
        self.pool = ThreadPoolExecutor(max_workers=1)

    def stop(self):
        self.book.close()
        self.pool.shutdown()
        
    def _get_balance(self):
        fx_str = self.product.split('-')
        cryp_str = fx_str[0]
        fiat_str = fx_str[1]
        accounts = self.client.get_accounts()
        for account in accounts:
            if account['currency'] == cryp_str:
                # TODO Use Decimal instead
                self.cryp_bal = float(account['balance'])
                self.cryp_avail = float(account['available'])
            if account['currency'] == fiat_str:
                # TODO Use Decimal instead
                self.fiat_bal = float(account['balance'])
                self.fiat_avail = float(account['available'])
                
    def buy(self):
        print("Buy Called")
        if self.buying == True:
            return
        self.buying = True
        self._cancel_pending()
        self._cancel_booked()
        self._get_balance()
        self._place_buy_order(self.book.ask() - 0.01)
        self.book.sell_fn = self._buy
        self.book.buy_fn = None
        
    def _buy(self, old_price, new_price):
        print("_Buy Called")
        min_purchase = new_price * 0.01
        if not self.buying or (self.fiat_bal - self.hold_back) < min_purchase:
            self.book.sell_fn = None
        # Place new order
        self._cancel_pending()
        self.active_futures.append(pool.submit(self._get_balance))
        self.active_futures.append(self.pool.submit(self._place_buy_order, new_price - 0.01))

    def _place_buy_order(self, price):
        size = round((self.fiat_bal - self.hold_back) / price - 0.00005, 4)
        if size <= 0.0:
            return
        price  = round(price, 2)
        self._cancel_booked()
        order = self.client.buy(price=str(price), size=str(size), product_id=self.product, post_only=True)
        print('Buy Order Placed: {}, {}, {}'.format(price, size, order))
         
    def sell(self):
        print("Sell Called")
        if self.buying == False:
            return
        self.buying = False
        self._cancel_pending()
        self._cancel_booked()
        self._get_balance()
        self._place_sell_order(self.book.bid() + 0.01)
        self.book.buy_fn = self._sell
        self.book.sell_fn = None
        
    def _sell(self, old_price, new_price):
        print("_Sell Called")
        if self.buying or self.cryp_bal < 0.0000001:
            self.book.buy_fn = None
        # Place new order
        self._cancel_pending()
        self.active_futures.append(pool.submit(self._get_balance))
        self.active_futures.append(self.pool.submit(self._place_sell_order, new_price + 0.01))

    def _place_sell_order(self, price):
        size = self.cryp_bal
        if size <= 0.0:
            return
        self._cancel_booked()
        price  = round(price, 2)
        order = self.client.sell(price=str(price), size=str(size), product_id=self.product, post_only=True)
        print('Sell Order Placed: {}, {}, {}'.format(price, size, order))

    def _cancel_pending(self):
        # Cancel all futures
        for future in self.active_futures:
            future.cancel()
        print('Futures cancelled: {}'.format(len(self.active_futures)))
        self.active_futures.clear()

    def _cancel_booked(self):
        # Cancel active orders
        order = self.client.cancel_all(self.product)
        print('Orders Cancelled: {}'.format(len(order)))

