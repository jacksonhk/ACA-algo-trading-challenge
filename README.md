# ACA-algo-trading-challenge

Crypto:

1. Stat Arbs (Tried => Discarded): Time Window too short for profitability:
   Details:
   Using Spread ratio of ETHUSD and BTCUSD to calculate z-score, trade when z-score is extreme by dynamic calculation of upper bound and lower bound.
   Stop gain: dynamic bound of means
   Stop loss: position losses > 2%

2. Momentum Based Strategy (Current):
   Current status: Singal generation: EMA 5-8-13 scalping + price cross long term EMA (50)
                   Range Filters: ADXR, AROON Oscillator
                   Momentum Filters: APO, MACD, AROON Oscillator, Price above long term EMA, Long Term EMA rising
                   Time Horizon: 6 hours
                   Stop loss: ATR trailing stop; Take profit (static): 2X stop loss 
   Development Plan:
   1.   Improve Activeness by considering trade opportunity in other instruments
      aa. Systems to rank trade opportunity
      ab. Better Take profit
      ac. Handling ranging market
      ad. Better Trend Filters (Smoothed HA candles?)
      ae. Logic to raise stake
