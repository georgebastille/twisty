import gdax
import numpy as np
from time import sleep, time
from datetime import datetime, timedelta
from math import ceil

class Twisty():
    def __init__(self):
        phrase_file = open('./auth/gdax.p', 'r')
        key_file = open('./auth/gdax.k', 'r')
        sec_file = open('./auth/gdax.s', 'r')

        phrase = phrase_file.read().replace('\n','')
        key = key_file.read().replace('\n','')
        sec = sec_file.read().replace('\n','')

        self.client = gdax.AuthenticatedClient(key, sec, phrase)
        self.log = open('./logs/index.html', 'w')
        #print(self.client.get_accounts())

        phrase_file.close()
        key_file.close()
        sec_file.close()
        self.prev_val = 0.0
        self.monitor_every = 3600

        self.product = 'ETH-EUR'
        self.coin = self.eth
        self.min_coin_transaction = 0.001
        self.min_dp = 3

    def book(self, product):
        book_val = None
        while book_val == None:
            try:
                book_val = self.client.get_product_order_book(product)
            except:
                self.log.write(' Exception parsing book response')
                sleep(0.5)
        return book_val

    def bid_price(self, product):
        price_val = None
        while price_val == None:
            try:
                book = self.client.get_product_order_book(product)
                price_val = float(book['bids'][0][0])
            except:
                self.log.write(' Exception parsing bid_price response')
                sleep(0.5)
        return price_val

    def ask_price(self, product):
        price_val = None
        while price_val == None:
            try:
                book = self.client.get_product_order_book(product)
                price_val = float(book['asks'][0][0])
            except:
                self.log.write(' Exception parsing ask_price response')
                sleep(0.5)
        return price_val

    def eur(self):
        eur_val = None
        while eur_val == None:
            try:
                eur_tmp = self.client.get_account('3abf21d3-d448-41e8-9657-dc8c132d25df')
                eur_val = float(eur_tmp['balance'])
            except:
                self.log.write(' Exception parsing eur response')
                sleep(0.5)
        return eur_val

    def btc(self):
        btc_val = None
        while btc_val == None:
            try:
                btc_tmp = self.client.get_account('3e569968-1139-44dd-af2c-7ddf6e88ab66')
                btc_val = float(btc_tmp['balance'])
            except:
                self.log.write(' Exception parsing btc response')
                sleep(0.5)
        return btc_val

    def eth(self):
        eth_val = None
        while eth_val == None:
            try:
                eth_tmp = self.client.get_account('3f07c3fc-ad0b-4be0-97f5-a147460e5eb2')
                eth_val = float(eth_tmp['balance'])
            except:
                self.log.write(' Exception parsing eth response')
                sleep(0.5)
        return eth_val

    def min_fiat_transaction(self):
        return self.ask_price(self.product) * self.min_coin_transaction

    def go(self):
        t_win = 250
        s_win = 28
        f_win = 13
        sto_win = 41
        sto_smooth = 21

        tortoise = SMA(t_win)
        slow = SMA(s_win)
        fast = SMA(f_win)
        stochastic_algo = StochasticOscillator(sto_win, sto_smooth)
        print ('Backfilling Moving Averages')
        prices = historic_prices(self.client, self.product, t_win, granularity=self.monitor_every)

        for price in prices[-t_win-1:]:
            tortoise.tick(price)

        for price in prices[-s_win-1:]:
            slow.tick(price)

        for price in prices[-f_win-1:]:
            fast.tick(price)

        for price in prices[-(sto_win + sto_smooth + 1):]:
            stochastic_algo.tick(price)

        fast_algo = MovingAverageAlgo(slow=slow, fast=fast)
        slow_algo = MovingAverageAlgo(slow=tortoise)

        print('Entering Runloop')
        while True:
            log_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            start = time()
            price = self.ask_price(self.product)

            slow_decision = slow_algo.tick(price)
            fast_decision = fast_algo.tick(price)
            stochastic_decision = False
            decision = fast_decision if slow_decision else stochastic_decision 

            log_s += ': Decision(T,F,O) = ({}, {}: {}), Price = {} {}'.format(slow_decision, fast_decision, decision, price, self.product)
            if decision:
                self.buy()
            else:
                self.sell()
            eur = self.eur()
            coin = self.coin()
            val = eur + (coin * price)
            log_s += ', Eur = {}, Coin = {}, Val = {}'.format(round(eur, 2) , round(coin, 4), round(val, 2)) 
            passed = time() - start
            log_s += ", Processing = {}s".format(round(passed, 2))
            self.log.write("{}<br>".format(log_s))
            self.log.flush()
            if self.monitor_every > passed:
                sleep(self.monitor_every - passed)

    def buy(self, hold_back=0):
        count = 0
        max_count = (self.monitor_every / 60.0) - 2
        avail = self.eur() - hold_back
        while (avail > self.min_fiat_transaction()) and count < max_count:
            start = time()
            book = self.book(self.product)
            ptb = self.ask_price(self.product) - 0.01
            amount = round((avail / ptb) - self.min_coin_transaction / 2, self.min_dp)
            print(' B {} {} @ {} euro.'.format(amount, self.product, ptb))
            try:
                order = self.client.buy(price=str(ptb), 
                   size=str(amount), 
                   product_id=self.product, 
                   post_only=True, 
                   time_in_force='GTT', 
                   cancel_after='min')
            except:
                print(' Error placing Buy Order: {} '.format(order))
                continue
            count += 1
            passed = time() - start
            if passed < 61:
                sleep(61 - passed)
            avail = self.eur() - hold_back

    def sell(self):
        count = 0
        max_count = (self.monitor_every / 60.0) - 2
        avail = self.coin()
        while avail > self.min_coin_transaction and count < max_count:
            start = time()
            price = self.bid_price(self.product) + 0.01
            print(' S {} {} @ {} euro.'.format(avail, self.product, price))
            try:
                order = self.client.sell(price=str(price), 
                    size=str(avail),
                    product_id=self.product, 
                    post_only=True, 
                    time_in_force='GTT', 
                    cancel_after='min')
            except:
                print(' Error placing Sell Order: {} '.format(order))
                continue
            count += 1
            passed = time() - start
            if passed < 61:
                sleep(61 - passed)
            avail = self.coin()

# Save historical data, take number of points and granularity
def historic_prices(client, product, num_candles, granularity=60, max_per=200):
    start = datetime.utcnow().replace(microsecond=0)
    delta = timedelta(seconds=granularity) * max_per
    full = ceil(num_candles / max_per)
    rates = []
    print('Collecting Historical data...')
    for i in range(1, full + 1):
        frm = start - (delta * i)
        to  = frm + delta
        print('From: {}, To: {}'.format(frm.isoformat(), to.isoformat()))
        rates.extend(client.get_product_historic_rates(product, start=frm.isoformat(), end=to.isoformat(), granularity=granularity))
        sleep(0.33)
    prices = [x[4] for x in rates]
    while 'a' in prices: prices.remove('a')
    prices.reverse()        
    print('Last 10 prices: {}'.format(prices[-10:]))
    return prices

class SMA:
    def __init__(self, window):
        self.window = []
        self.full_len = window
        self.count = 0
        self.index = 0
        self.avg = 0.
        
    def tick(self, val):
        ret = None
        if self.count == self.full_len:
            self.avg -= self.window[self.index]
            self.avg += val
            self.window[self.index] = val
            self.index += 1
            self.index = self.index % self.full_len
            ret = self.avg / self.full_len
        else:
            self.window.append(val)
            self.avg += val
            self.index += 1
            self.index = self.index % self.full_len
            self.count += 1
            if self.count == self.full_len:
                ret = self.avg / self.count
        return ret

class EMA:
    #https://stackoverflow.com/questions/42869495/numpy-version-of-exponential-weighted-moving-average-equivalent-to-pandas-ewm
    def __init__(self, window):
        self.window = window
        alpha = 2 /(window + 1.0)
        alpha_rev = 1 - alpha
        self.pows = alpha_rev**(np.arange(window))
        self.pows = np.flip(self.pows, 0)
        self.norm = np.sum(self.pows)
    
        self.data = np.array([])
        self.count = 0
        
    def tick(self, val):
        ret = None
        if self.count < self.window:
            self.data = np.append(self.data, val)
            self.count += 1
            if self.count == self.window:
                ret = np.sum(self.data * self.pows) / self.norm
        else:
            self.data = np.roll(self.data, -1)
            self.data[-1] = val
            ret = np.sum(self.data * self.pows) / self.norm
        return ret

class StochasticOscillator:
    def __init__(self, window=20, smooth=6):
        self.data = np.zeros(window) + 0.5
        self.avg = SMA(smooth)
        
    def tick(self, price):
        stance = False
        self.data = np.roll(self.data, -1)
        self.data[-1] = price
        low = np.min(self.data)
        high = np.max(self.data)
        so = (price - low) / (high - low)
        avgv = self.avg.tick(so)
        if avgv:
            stance = so > avgv
        return stance

class MovingAverageAlgo:
    def __init__(self, slow=None, fast=None, buy_cutoff=0.0, sell_cutoff=0.0):
        self.slow = slow
        self.fast = fast
        self.buy_cutoff = buy_cutoff
        self.sell_cutoff = sell_cutoff
        self.last_diff = 0
        
    def tick(self, price):
        ret = False
        slow = self.slow.tick(price) if self.slow else price
        fast = self.fast.tick(price) if self.fast else price
        if (slow != None and fast != None):
            diff = (fast - slow) / slow
            if diff > self.last_diff:
                ret = diff > self.buy_cutoff
            else:
                ret = diff > self.sell_cutoff
            self.last_diff = diff
        return ret

class DoubleSMADecision:
    def __init__(self, slow=50, fast=5, cutoff=0.1):
        self.slow = SMA(slow)
        self.fast = SMA(fast)
        self.cutoff = cutoff
        
    def tick(self, price):
        ret = None
        slow = self.slow.tick(price)
        fast = self.fast.tick(price)
        if (slow != None and fast != None):
            ret = (fast - slow) > self.cutoff
            #print("Slow: {}  Fast: {} Diff: {}".format(slow, fast, (fast - slow)))
        return ret


if __name__ == '__main__':
    t = Twisty()
    t.go()
