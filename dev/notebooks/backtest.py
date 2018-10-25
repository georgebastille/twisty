import gdax
import numpy as np
from datetime import datetime, timedelta
from math import ceil
from time import sleep

public_client = gdax.PublicClient()

class Trader:
    def __init__(self, algo, algo2=None, fee=0.0, trade_prob=0.8, verbose=False):
        self.algo = algo
        self.algo2 = algo2
        self.value = 100.
        self.stance = False
        self.last_price = 0
        self.num_trades = 0
        self.fee = fee
        self.trade_prob = trade_prob
        self.tick_count = 0
        self.verbose = verbose
        
    def tick(self, price):
        log = "{} - Price: {}, Stance: {}".format(self.tick_count, price, "In, " if self.stance else "Out, ")
        if self.last_price == 0:
            self.last_price = price
            
        decision1 = self.algo.tick(price)
        decision2 = self.algo2.tick(price) if self.algo2 else True
        decision = decision1 and decision2

        log += "Decision: {}".format("Buy, " if decision else "Sell, ")
        # Simulate difficulty buying with random trade prob
        if decision != self.stance and np.random.uniform() >= self.trade_prob:
            log += "Failed to {} @ {}".format("Buy" if decision else "Sell", price)
            decision = self.stance
            
        if self.stance:
            delta = self.value * ((price - self.last_price) / self.last_price)
            self.value += delta
            log += "Delta: {}, ".format(round(delta, 2))
            
        if decision != self.stance:
            self.stance = decision
            self.value -= (self.value * self.fee)
            self.num_trades += 1
            
        self.last_price = price
        log += "Value: {}".format(round(self.value, 2))
        if self.verbose: print(log)
        self.tick_count += 1
        
        return self.value, self.num_trades

def historic_prices(client, product, num_candles, granularity, max_per=200):
    start = datetime.utcnow().replace(microsecond=0)
    delta = timedelta(seconds=granularity) * max_per
    full = ceil(num_candles / max_per)
    rates = []
    pairs = []
    for i in range(1, full + 1):
        frm = start - (delta * i)
        to  = frm + delta
        print('From: {}, To: {}'.format(frm.isoformat(), to.isoformat()))
        rates.extend(client.get_product_historic_rates(product, start=frm.isoformat(), end=to.isoformat(), granularity=granularity))
        sleep(0.33)
    for rate in rates:
        pairs.append((rate[0], rate[4]))
    pairs = list(dict.fromkeys(pairs))
    prices = [x[1] for x in pairs]
    while 'a' in prices: prices.remove('a')
    prices.reverse()
    print('Last 10 prices: {}'.format(prices[-10:]))
    return prices
