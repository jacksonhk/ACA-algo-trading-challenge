# ACA-algo-trading-challenge

Crypto:

1. Stat Arbs (Tried => Discarded): Time Window too short for profitability:
   Details:
   Using Spread ratio of ETHUSD and BTCUSD to calculate z-score, trade when z-score is extreme by dynamic calculation of upper bound and lower bound.
   Stop gain: dynamic bound of means
   Stop loss: position losses > 2%

2. Momentum Based Strategy (Current):
   Current plan: try with EMA 5-8-13 scalping with filters for more signals in intraday
