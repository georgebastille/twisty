import gdax
from time import sleep, time
from exchange import TwistyBook
from datetime import datetime, timedelta

class Monitor():
    def __init__(self):
        self.client = gdax.PublicClient()
        self.log = open('./logs/index.html', 'w')

        self.monitor_every = 10
        self.product = 'BTC-EUR'
        self.running = True

        def book_close():
            self.running = False

        self.book = TwistyBook(self.product, shutdown_func=book_close)

    def go(self):
        print('Entering Runloop')
        
        self.book.start()
        sleep(5)
        
        while self.running:
            start = time()
            log_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            price = self.book.ask()
            bid_vol = self.book.bid_vol()
            ask_vol = self.book.ask_vol()
            vol_ratio = bid_vol/ask_vol

            log_s += ', Price = {} , BidVol = {} , AskVol = {} , Ratio = {}'.format(price, bid_vol, ask_vol, vol_ratio)
            
            passed = time() - start
            log_s += ", Processing = {}s".format(round(passed, 2))
            self.log.write("{}<br>".format(log_s))
            self.log.flush()
            print(log_s)
            if self.monitor_every > passed:
                sleep(self.monitor_every - passed)
 
if __name__ == '__main__':
    while(True):
        m = Monitor()
        m.go()
