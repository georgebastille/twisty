import gdax

from exchange import TwistyBook, PurchaseEngine
from backtest import historic_prices
from algorithms import get_PriceWatchOscillator
from algorithms import get_StochasticOscillator

from time import sleep, time
from datetime import datetime, timedelta

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
        
        self.monitor_every = 300
        self.product = 'BTC-EUR'
        self.min_coin_transaction = 0.001
        self.min_dp = 3
        self.running = True
        def book_close():
            self.running = False
        self.book = TwistyBook(self.product, shutdown_func=book_close)
        self.engine = PurchaseEngine(self.product, self.client, self.book, hold_back=600.0)

    def go(self):
        print('Entering Runloop')
        
        window = 72
        tick_count = 0
        algo = None
        
        self.engine.start()
        sleep(3)
        
        while self.running:
            start = time()
            if not algo or tick_count % window == 0:
                win_warm = int(window * 1.1)
                prices = historic_prices(self.client, self.product, win_warm, granularity=self.monitor_every)
                algo = get_PriceWatchOscillator(prices[-win_warm:])
                #algo = get_StochasticOscillator(prices[-win_warm:])

                algo.tick(prices[-1] + 0.01) # HACK!
                
            log_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            price = self.book.ask()
            decision = algo.tick(price)

            log_s += ': Decision = {}, Price = {} {}'.format(decision, price, self.product)
            
            if decision:
                self.engine.buy()
            else:
                self.engine.sell()
                
            passed = time() - start
            log_s += ", Processing = {}s".format(round(passed, 2))
            self.log.write("{}<br>".format(log_s))
            self.log.flush()
            print(log_s)
            tick_count += 1
            if self.monitor_every > passed:
                sleep(self.monitor_every - passed)
                
    def stop(self):
        self.engine.stop()

if __name__ == '__main__':
    while(True):
        t = Twisty()
        t.go()
        t.stop()
