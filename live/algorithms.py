import numpy as np
import sys

from backtest import Trader

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
        ret = 0.0
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


class SMA:
    def __init__(self, window):
        self.window = []
        self.full_len = window
        self.count = 0
        self.index = 0
        self.avg = 0.
        
    def tick(self, val):
        ret = 0.0
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

class PPOAlgo:
    def __init__(self, slow_win=26, fast_win=12, signal_win=9, prices=None):
        self.slow = EMA(slow_win)
        self.fast = EMA(fast_win)
        self.signal = EMA(signal_win)
        
        if prices:
            for price in prices:
                slow = self.slow.tick(price)
                fast = self.fast.tick(price)
                if slow and fast:
                    self.signal.tick((fast - slow) / slow)
        
    def tick(self, price):
        ret = False
        slow = self.slow.tick(price)
        fast = self.fast.tick(price)
        if slow > 0:
            ppo = (fast - slow) / slow
            signal = self.signal.tick(ppo)
            ret = ppo - signal > 0
        else:
            self.signal.tick(price)
        return ret

class MovingAverageAlgo:
    def __init__(self, slow=None, fast=None, buy_cutoff=0.0, sell_cutoff=0.0):
        self.slow = slow
        self.fast = fast
        self.buy_cutoff = buy_cutoff
        self.sell_cutoff = sell_cutoff
        self.last_diff = 0
        
    def tick(self, price):
        ret = None
        slow = self.slow.tick(price) if self.slow else price
        fast = self.fast.tick(price) if self.fast else price
        if (slow and fast):
            diff = (fast - slow) / slow
            if diff > self.last_diff:
                ret = diff > self.buy_cutoff
            else:
                ret = diff > self.sell_cutoff
            self.last_diff = diff
        return ret

class StochasticOscillator:
    def __init__(self, window=14, smooth=3):
        self.data = np.zeros(window) + 0.5
        self.avg = EMA(smooth)
        
    def tick(self, price):
        stance = False
        self.data = np.roll(self.data, -1)
        self.data[-1] = price
        low = np.min(self.data)
        high = np.max(self.data)
        if high == low:
            so = 0.5
        else:
            so = (price - low) / (high - low)
        avgv = self.avg.tick(so)
        if avgv:
            stance = so > avgv
        return stance

class PriceWatchOscillator:
    def __init__(self, up_chg=0.0, down_chg=0.0, up_out_chg=0.0):
        self.last_max = 0.0
        self.last_min = sys.float_info.max
        self.out_mul = (1.0 - down_chg)
        self.in_mul = (1.0 + up_chg)
        self.up_out_mul = (1.0 + up_out_chg)
        self.stance = False
        self.in_price = 0
        self.out_price = 0
                
    def tick(self, price):
        if self.stance:
            if price > self.last_max:
                self.last_max = price
            if (price < self.last_max * self.out_mul) or (price > self.in_price * self.up_out_mul):
                self.stance = False
                self.out_price = price
                self.last_max = 0.0
        else:
            if price < self.last_min:
                self.last_min = price
            elif price > self.last_min * self.in_mul:
                self.stance = True
                self.in_price = price
                self.last_min = sys.float_info.max
        return self.stance

def get_StochasticOscillator(prices):
    potential = []
    print('Backtesting Oscillator')
    for window in range (2, 30, 2):
        for smooth in range(2, 30, 2):
            algo = StochasticOscillator(window, smooth)
            trader = Trader(algo)
            final = 0
            for price in prices:
                final, _ = trader.tick(price)
            potential.append((window, smooth, final))
    potential.sort(key=lambda tup: tup[2], reverse=True)
    print('Optimal Values ({}, {}) give {}'.format(potential[0][0], potential[0][1], potential[0][2]))
    algo = StochasticOscillator(window=potential[0][0], smooth=potential[0][1])
    for price in prices:
        algo.tick(price)
    return algo

def get_PriceWatchOscillator(prices):
    potential = []
    print('Backtesting Oscillator')
    for up_chg in np.arange(0.0, 0.05, 0.005):
        for down_chg in np.arange(0.0, 0.05, 0.005):
            for up_out_chg in np.arange(0.0, 0.05, 0.005):
                algo = PriceWatchOscillator(up_chg=up_chg, down_chg=down_chg, up_out_chg=up_out_chg)
                trader = Trader(algo=algo, trade_prob=1.0)
                final = 0
                trades = 0
                for price in prices:
                    final, trades = trader.tick(price)
                final = (round(final, 2))
                adjusted = final - trades/10.0
                potential.append((adjusted, final, trades, up_chg, down_chg, up_out_chg))
    potential.sort(key=lambda tup: tup[0], reverse=True)       
    print('Optimal Parameters ({}, {}, {}) give {}'.format(potential[0][3], potential[0][4], potential[0][5], potential[0][1]))
    algo = PriceWatchOscillator(up_chg=potential[0][3], down_chg=potential[0][4], up_out_chg=potential[0][5])
    for price in prices:
        algo.tick(price)
    return algo
