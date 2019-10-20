# Twisty
Twisty is a set of tools for developing, testing and running trading strategies on the Coinbase pro crypto currency exchange.

dev/ -  Jupyter notebooks demonstrationg how to fetch historic prices and then backtest using a variety of strategies

live/ - Python 3 trading engine, features:
+ Minimise fees by using Market making orders
+ Subscribes to live updates from the exchange to maximise trade probability at the desired price
+ Separates the signal generation time frame and from the trading timeframe
+ Runs on a Raspberry pi 1
+ Publishes logs on a webserver for monitoring
