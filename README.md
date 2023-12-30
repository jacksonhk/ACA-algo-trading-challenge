# ACA-algo-trading-challenge

Crypto:

1. Stat Arbs (Tried => Discarded): Time Window too short for profitability:
   Details:
   Using Spread ratio of ETHUSD and BTCUSD to calculate z-score, trade when z-score is extreme by dynamic calculation of upper bound and lower bound.
   Stop gain: dynamic bound of means
   Stop loss: position losses > 2%

2. Momentum Based Strategy (Final):<br />
   Final status: Singal generation (4) : EMA 5-8-13 scalping + price cross long term EMA (50) + Stoch RSI crossover + Pullback <br />
                   Range Filters: ADXR, AROON Oscillator, RSI<br />
                   Momentum Filters: APO, MACD, RSI, AROON Oscillator, Price above long term EMA, Long Term EMA rising<br />
                   Time Horizon: 1 day<br />
                   Stop loss: ATR trailing stop; Take profit (static): 2.5X stop loss <br />
                   Systems to rank instruments: Lowest ATR (to minimize drawdown) <br />
                   Performance: Sharpe Ratio: 0.93 <br />
                                Mean Annual Return: 47% <br />
