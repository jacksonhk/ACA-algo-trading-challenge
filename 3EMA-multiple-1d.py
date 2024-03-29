



from AlgoAPI import AlgoAPIUtil, AlgoAPI_Livetest
from datetime import datetime, timedelta
import talib, numpy
import pandas as pd

class AlgoEvent:
    def __init__(self):
        
        self.fastperiod = 5
        self.midperiod = 8
        self.slowperiod = 13
        self.longperiod = 50
        self.atr_period = 14
        self.general_period = 14
        self.instrument_data = {}
        self.openOrder = {}
        self.netOrder = {}
        self.lasttradetime = datetime(2000,1,1)
        self.stoploss_atr = 2.5
        self.K, self.D = 3, 3
        
        self.allowance_allocation_ratio = 0.85
        self.risk_to_reward_ratio = 2.5
        self.candidate_no = 2
        self.risk_limit_portfolio = 0.2
        self.cooldown = 15
 
    def start(self, mEvt):
        self.myinstrument = mEvt['subscribeList'][0]
        self.no_instrument = len(mEvt['subscribeList'])
        self.evt = AlgoAPI_Livetest.AlgoEvtHandler(self, mEvt)
        self.evt.update_portfolio_sl(sl=self.risk_limit_portfolio, resume_after=60*60*24*self.cooldown)
        self.evt.start()

    def on_bulkdatafeed(self, isSync, bd, ab):
        # adding data for each instrument on every data received
        if isSync:
            if bd[self.myinstrument]['timestamp'] >= self.lasttradetime + timedelta(hours = 24): 
                self.lasttradetime = bd[self.myinstrument]['timestamp']
                # update trade time if timeframe match and continue the code
            else:
                return # do not trade if timeframe does not match
            for instrument in bd:
                if instrument not in self.instrument_data:
                    obs = self.evt.getHistoricalBar(contract={"instrument":instrument}, numOfBar=max(self.fastperiod + self.midperiod + self.slowperiod + 1, self.longperiod), interval="D")

                    self.instrument_data[instrument] = {
                        'arr_close': numpy.array([obs[t]['c'] for t in obs]),
                        'arr_fastMA': numpy.array([]),
                        'arr_midMA': numpy.array([]),
                        'arr_slowMA': numpy.array([]),
                        'arr_LongTermMA': numpy.array([]),
                        'highprice': numpy.array([]),
                        'lowprice': numpy.array([]),
                        'lasttradetime': datetime(2000,1,1),
                        'atr': numpy.array([]),
                        'K': numpy.array([]),
                        'D': numpy.array([]),
                        'stoploss': 0,
                        'entry_signal': 0 # 1 == long, -1 == short, 0 == No signal
                    }
                
                instrument_data = self.instrument_data[instrument]
                lastprice = bd[instrument]['lastPrice']
                instrument_data['arr_close'] = numpy.append(instrument_data['arr_close'], lastprice)
                instrument_data['highprice'] = numpy.append(instrument_data['highprice'], bd[instrument]['highPrice'])
                instrument_data['lowprice'] = numpy.append(instrument_data['lowprice'], bd[instrument]['lowPrice'])
                # keep the most recent observations
                time_period = (
                    max(self.fastperiod + self.midperiod + self.slowperiod + 1, self.longperiod)
                )
                    
                if len(instrument_data['arr_close']) >= time_period:
                    instrument_data['arr_close'] = instrument_data['arr_close'][-time_period:]
                        
                # keep the most recent observations
                if len(instrument_data['highprice']) >= time_period:
                    instrument_data['highprice'] = instrument_data['highprice'][-time_period:]
                # keep the most recent observations
                if len(instrument_data['lowprice']) >= time_period:
                    instrument_data['lowprice'] = instrument_data['lowprice'][-time_period:]
                    
                # fit SMA line
                instrument_data['arr_fastMA'] = talib.DEMA(
                    instrument_data['arr_close'], timeperiod=self.fastperiod
                )
                instrument_data['arr_midMA'] = talib.DEMA(
                    instrument_data['arr_close'], timeperiod=self.midperiod
                )
                instrument_data['arr_slowMA'] = talib.DEMA(
                    instrument_data['arr_close'], timeperiod=self.slowperiod
                )
                
                if not len(instrument_data['arr_close']) == len(instrument_data['highprice']) == len(instrument_data['lowprice']):
                    minlength = min(len(instrument_data['arr_close']), len(instrument_data['highprice']), len(instrument_data['lowprice']))
                    while len(instrument_data['arr_close']) > minlength:
                        instrument_data['arr_close'].popleft()
                    while len(instrument_data['highprice']) > minlength:
                        instrument_data['highprice'].popleft() 
                    while len(instrument_data['lowprice']) > minlength:
                        instrument_data['lowprice'].popleft() 
                        
                instrument_data['atr'] = talib.ATR(
                    instrument_data['highprice'],
                    instrument_data['lowprice'],
                    instrument_data['arr_close'],
                    timeperiod=self.atr_period
                )
                    
                instrument_data['stoploss'] = self.stoploss_atr * instrument_data['atr'][-1]
                # Long EMA as a momentum indicator:
                instrument_data['arr_LongTermMA'] = talib.EMA(instrument_data['arr_close'], timeperiod=self.longperiod)
                    
                # checking for entry signal
                
                 # Ranging/Momentum filter: all short-term moving average move in same direction
                
                fast, mid, slow = instrument_data['arr_fastMA'], instrument_data['arr_midMA'], instrument_data['arr_slowMA']
                all_MA_up, all_MA_down, MA_same_direction = False, False, False
                if len(fast) > 1 and len(mid) > 1 and len(slow) > 1:
                    all_MA_up = fast[-1] > fast[-2] and mid[-1] > mid[-2] and slow[-1] > slow[-2]
                    all_MA_down = fast[-1] < fast[-2] and mid[-1] < mid[-2] and slow[-1] < slow[-2]
                    MA_same_direction = all_MA_up or all_MA_down
                    
                    
                # Entry Signal 2: Price cross above or below long term MA
                price_above_longtermMA = instrument_data['arr_close'][-1] >= instrument_data['arr_LongTermMA'][-1] 
                LongTermEMA_rising = False
                price_cross_above_longtermMA = False
                price_cross_below_longtermMA = False
                    
                if len(instrument_data['arr_LongTermMA']) > 1:
                    LongTermEMA_rising = instrument_data['arr_LongTermMA'][-1] >= instrument_data['arr_LongTermMA'][-2]
                    price_cross_above_longtermMA = instrument_data['arr_close'][-1] >= instrument_data['arr_LongTermMA'][-1] and instrument_data['arr_close'][-2] <= instrument_data['arr_LongTermMA'][-2] and instrument_data['arr_LongTermMA'][-1] > instrument_data['arr_LongTermMA'][-2] 
                    price_cross_below_longtermMA = instrument_data['arr_close'][-1] <= instrument_data['arr_LongTermMA'][-1] and instrument_data['arr_close'][-2] >= instrument_data['arr_LongTermMA'][-2] and instrument_data['arr_LongTermMA'][-1] < instrument_data['arr_LongTermMA'][-2] 
                    
                # Entry Signal 3: Pullback and Throwback implementation
                pullback = False
                throwback = False
                if len(instrument_data['arr_close']) > 1:
                    pullback = instrument_data['arr_close'][-1] > instrument_data['arr_midMA'][-1] and instrument_data['arr_close'][-2] < instrument_data['arr_midMA'][-2] and instrument_data['arr_close'][-1] > instrument_data['arr_LongTermMA'][-1] and instrument_data['arr_midMA'][-1] > instrument_data['arr_LongTermMA'][-1]
                    pullbackSlow = instrument_data['arr_close'][-1] > instrument_data['arr_slowMA'][-1] and instrument_data['arr_close'][-2] < instrument_data['arr_slowMA'][-2] and instrument_data['arr_close'][-1] > instrument_data['arr_LongTermMA'][-1] and instrument_data['arr_slowMA'][-1] > instrument_data['arr_LongTermMA'][-1]
                    throwback = instrument_data['arr_close'][-1] < instrument_data['arr_midMA'][-1] and instrument_data['arr_close'][-2] > instrument_data['arr_midMA'][-2] and instrument_data['arr_close'][-1] < instrument_data['arr_LongTermMA'][-1] and instrument_data['arr_midMA'][-1] < instrument_data['arr_LongTermMA'][-1]
                    throwbackSlow = instrument_data['arr_close'][-1] < instrument_data['arr_slowMA'][-1] and instrument_data['arr_close'][-2] > instrument_data['arr_slowMA'][-2] and instrument_data['arr_close'][-1] < instrument_data['arr_LongTermMA'][-1] and instrument_data['arr_slowMA'][-1] < instrument_data['arr_LongTermMA'][-1]
                    pullback, throwback = pullback or pullbackSlow, throwback or throwbackSlow
                
                # Entry Signal 4: Stoch RSI implementation
                K, D = self.stoch_rsi(instrument_data['arr_close'], k = self.K, d = self.D, period = self.general_period)
                instrument_data['K'] = numpy.append(instrument_data['K'], K)
                instrument_data['D'] = numpy.append(instrument_data['D'], D)
                if len(instrument_data['K']) > time_period:
                    instrument_data['K'] = instrument_data['K'][-time_period:]
                    instrument_data['D'] = instrument_data['D'][-time_period:]
                    
                k_crossabove_d = False
                k_crossbelow_d = False
                if len(instrument_data['K']) > 1 and len(instrument_data['D']) > 1:
                    k_crossabove_d = instrument_data['K'][-1] >= instrument_data['D'][-1] and instrument_data['K'][-2] < instrument_data['D'][-2]
                    k_crossbelow_d = instrument_data['K'][-1] <= instrument_data['D'][-1] and instrument_data['K'][-2] > instrument_data['D'][-2]
                
                long_stoch_rsi = k_crossabove_d and (instrument_data['arr_fastMA'][-1] > instrument_data['arr_slowMA'][-1] and instrument_data['arr_slowMA'][-1] > instrument_data['arr_LongTermMA'][-1])
                
                short_stoch_rsi = k_crossbelow_d and (instrument_data['arr_fastMA'][-1] < instrument_data['arr_slowMA'][-1] and instrument_data['arr_slowMA'][-1] < instrument_data['arr_LongTermMA'][-1])
                
                # Filters Calculation
                
                # Calculate the ADXR using talib.ADXR
                adxr = talib.ADXR(instrument_data['highprice'], instrument_data['lowprice'], instrument_data['arr_close'], timeperiod=self.general_period)
                    
                # Caclulate the APO for momentum detection
                apo = talib.APO(instrument_data['arr_close'], self.midperiod, self.slowperiod)
                    
                macd, signal, hist = talib.MACD(instrument_data['arr_close'], self.fastperiod, self.slowperiod, self.midperiod)
                
                rsiFast, rsiGeneral = talib.RSI(instrument_data['arr_close'], self.fastperiod), talib.RSI(instrument_data['arr_close'], self.general_period)       
                # Calculate Aroon values
                aroon_up, aroon_down = talib.AROON(instrument_data['highprice'], instrument_data['lowprice'], timeperiod=self.general_period)
                aroonosc = aroon_up - aroon_down
                    
              
                
                ranging = self.rangingFilter(adxr, aroonosc, MA_same_direction, rsiGeneral)
                bullish = self.momentumFilter(apo, macd, rsiFast, rsiGeneral, aroonosc, price_above_longtermMA, LongTermEMA_rising, all_MA_up, all_MA_down)
                    
                    
                    
                if not numpy.isnan(instrument_data['arr_fastMA'][-1]) and not numpy.isnan(instrument_data['arr_fastMA'][-2]) and not numpy.isnan(instrument_data['arr_slowMA'][-1]) and not numpy.isnan(instrument_data['arr_slowMA'][-2]) and not numpy.isnan(instrument_data['arr_midMA'][-1]) and not numpy.isnan(instrument_data['arr_midMA'][-2]):
                    # send a buy order for Golden Cross (fastMA above slowMA, midMA crosses above slowMA)
                    
                    EMA3_GoldenCross = instrument_data['arr_fastMA'][-1] > instrument_data['arr_slowMA'][-1] and instrument_data['arr_midMA'][-1] > instrument_data['arr_slowMA'][-1] and instrument_data['arr_fastMA'][-2] < instrument_data['arr_slowMA'][-2]
                    EMA3_DeathCross = instrument_data['arr_fastMA'][-1] < instrument_data['arr_slowMA'][-1] and instrument_data['arr_midMA'][-1] < instrument_data['arr_slowMA'][-1] and instrument_data['arr_fastMA'][-2] > instrument_data['arr_slowMA'][-2]
                    
                    
                    if (not ranging and bullish == 1) and (EMA3_GoldenCross or price_cross_above_longtermMA or pullback or long_stoch_rsi):
                        instrument_data['entry_signal'] = 1
                        
                    # send a sell order for Death Cross
                    elif (not ranging and bullish == -1) and (EMA3_DeathCross or price_cross_below_longtermMA or throwback or short_stoch_rsi):
                        instrument_data['entry_signal'] = -1
                        
                    else:
                        instrument_data['entry_signal'] = 0
                        
                else:
                    instrument_data['entry_signal'] = 0
            
                # update stoploss point dynamically
                if self.openOrder:
                    self.update_stoploss(instrument, instrument_data['stoploss'])
            
            # algorithm to rank candidates base on tightness of stoploss to minimize drawdown risk
            count = 0
            candidate = []
            # checking all instruments for entry signals and find total number of entry signals
            for instrument in bd:
                if self.instrument_data[instrument]['entry_signal'] == 1 or self.instrument_data[instrument]['entry_signal'] == -1:
                    count += 1
                    lastprice = self.instrument_data[instrument]['arr_close'][-1]
                    stoploss = self.instrument_data[instrument]['stoploss']
                    stoploss_ratio = stoploss / lastprice
                    candidate.append((stoploss_ratio, instrument))
            candidate.sort()
            
            if count > self.candidate_no:
                candidate = candidate[:self.candidate_no]
                count = self.candidate_no
            
            # TODO: count can be used as market breath    
            availableBalance = ab['availableBalance']
            
            #TODO: checking for existing position, if same instrument have existing position, sell the position before opening new one
            for stoploss_ratio, instrument in candidate: 
                if instrument in self.openOrder and self.openOrder[instrument][buysell] != self.instrument_data[instrument]['entry_signal']:
                    self.closeAllOrder(instrument)
                lastprice = bd[instrument]['lastPrice']
                volume = self.find_positionSize(lastprice, count/self.candidate_no * 1/self.no_instrument * availableBalance * 2)
                direction = self.instrument_data[instrument]['entry_signal']
                stoploss = self.instrument_data[instrument]['stoploss']
                res = self.test_sendOrder(lastprice, direction, 'open', volume, stoploss, instrument)
                    
               

    def on_marketdatafeed(self, md, ab):
        pass

    def on_orderfeed(self, of):
        pass

    def on_dailyPLfeed(self, pl):
        pass

    def on_openPositionfeed(self, op, oo, uo):
        self.openOrder = oo
        self.netOrder = op
    
    # Finder of Stochastic RSI
    def stoch_rsi(self, arr_close, k, d, period):
        rsi = talib.RSI(arr_close, period)
        df = pd.DataFrame(rsi)
        stochastic_rsi = 100 * (df - df.rolling(period).min()) / (df.rolling(period).max() - df.rolling(period).min())
        K = stochastic_rsi.rolling(k).mean()
        D = K.rolling(d).mean().iloc[-1].iloc[0]
        K = K.iloc[-1].iloc[0]
        return K, D 
        # K and D are returned as a array

    def rangingFilter(self, ADXR, AROONOsc, MA_same_direction, rsi):
        lowest_rsi, highest_rsi = min(rsi), max(rsi)
        maxchange_rsi = max(abs(rsi[-1] - lowest_rsi), abs(rsi[-1] - highest_rsi), 0)
        maxchange_ADXR = ADXR[-1] - min(ADXR)
        if (ADXR[-1] < 20) or abs(AROONOsc[-1]) < 20 or 40 < rsi[-1] < 60 :
            return True # ranging market
        else:
            return False
    
    def momentumFilter(self, APO, MACD, RSIFast, RSIGeneral, AROONOsc, price_above_longtermMA, LongTermEMA_rising, all_MA_up, all_MA_down):
        # APO rising check
        APORising = False
        if numpy.isnan(APO[-1]) or numpy.isnan(APO[-2]):
            APORising = False
        elif int(APO[-1]) > int(APO[-2]):
            APORising = True
        
        # macd rising check
        MACDRising = False
        if numpy.isnan(MACD[-1]) or numpy.isnan(MACD[-2]):
            MACDRising = False
        elif int(MACD[-1]) > int(MACD[-2]):
            MACDRising = True
        
        # RSI check (additional)
        RSIFastRising, RSIGeneralRising = False, False
        if numpy.isnan(RSIFast[-1]) or numpy.isnan(RSIFast[-2]) or numpy.isnan(RSIGeneral[-2]) or numpy.isnan(RSIGeneral[-2]):
            RSIFastRising, RSIGeneralRising = False, False
        else:
            if int(RSIFast[-1]) > int(RSIFast[-2]):
                RSIFastRising = True
            if int(RSIGeneral[-1]) > int(RSIGeneral[-2]):
                RSIGeneralRising = True
            
        # aroonosc rising check
        AROON_direction = 0 # not moving
        if numpy.isnan(AROONOsc[-1]) or numpy.isnan(AROONOsc[-2]):
            AROON_direction = 0
        elif int(AROONOsc[-1]) > int(AROONOsc[-2]):
            AROON_direction = 1 # moving upwawrds
        elif int(AROONOsc[-1]) < int(AROONOsc[-2]):
            AROON_direction = -1 # moving downwards
        else:
            AROON_direction = 0 # not moving
        
        AROON_positive = False
        if numpy.isnan(AROONOsc[-1]):
            AROON_positive = False
        elif int(AROONOsc[-1]) > 0:
            AROON_positive = True
            
        if (APORising or APO[-1] > 0) and (RSIFast[-1] > 50 or RSIFastRising or RSIGeneralRising) or (MACDRising or AROON_direction == 1 or AROON_positive) and (price_above_longtermMA or LongTermEMA_rising) and all_MA_up:
            return 1 # Bullish 
            
        elif (not APORising or APO[-1] < 0) and (RSIFast[-1] < 50 or not RSIFastRising or not RSIGeneralRising) and (not MACDRising or AROON_direction == -1 or not AROON_positive) and (not price_above_longtermMA or not LongTermEMA_rising) and all_MA_down:
            return -1 # Bearish
        else:
            return 0 # Neutral
    
    def test_sendOrder(self, lastprice, buysell, openclose, volume, stoploss, instrument):
        order = AlgoAPIUtil.OrderObject()
        order.instrument = instrument
        order.orderRef = 1
        if buysell==1: # buy order
            order.takeProfitLevel = lastprice + self.risk_to_reward_ratio * stoploss
            order.stopLossLevel = lastprice - stoploss
        elif buysell==-1:
            order.takeProfitLevel = lastprice - self.risk_to_reward_ratio * stoploss
            order.stopLossLevel = lastprice + stoploss
        order.volume = volume
        order.openclose = openclose
        order.buysell = buysell
        order.ordertype = 0 #0=market_order, 1=limit_order, 2=stop_order
        self.evt.sendOrder(order)
    
    def closeAllOrder(self, instrument):
        if not self.openOrder:
            return False
        for ID in self.openOrder:
            if self.openOrder[ID]['instrument'] == instrument:
                order = AlgoAPIUtil.OrderObject(
                    tradeID = ID,
                    openclose = 'close',
                )
                self.evt.sendOrder(order)
        return True
    
    # ATR trailing stop implementation
    def update_stoploss(self, instrument, new_stoploss):
        for ID in self.openOrder:
            openPosition = self.openOrder[ID]
            if openPosition['instrument'] == instrument:
                lastprice = self.instrument_data[instrument]['arr_close'][-1]
                if openPosition['buysell'] == 1 and openPosition['stopLossLevel'] < lastprice - new_stoploss: 
                    # for buy ordder, update stop loss if current ATR stop is higher than previous 
                    newsl_level = lastprice - new_stoploss
                    res = self.evt.update_opened_order(tradeID=ID, sl = newsl_level)
                    # update the update stop loss using ATR stop
                elif openPosition['buysell'] == -1 and lastprice + new_stoploss < openPosition['stopLossLevel']: 
                    # for buy ordder, update stop loss if current ATR stop is higher than previous 
                    newsl_level = lastprice + new_stoploss
                    res = self.evt.update_opened_order(tradeID=ID, sl = newsl_level)
                    # update the update stop loss using ATR stop
                    
        
    # utility function to find volume based on available balance
    def find_positionSize(self, lastprice, allowance):
        res = self.evt.getAccountBalance()
        availableBalance = res["availableBalance"]
        ratio = self.allowance_allocation_ratio
        volume = (allowance*ratio) / lastprice
        total =  volume * lastprice
        while total < self.allowance_allocation_ratio * allowance:
            ratio *= 1.05
            volume = (allowance*ratio) / lastprice
            total =  volume * lastprice
        while total > 0.9 * allowance or total > availableBalance:
            ratio *= 0.95
            volume = (allowance*ratio) / lastprice
            total =  volume * lastprice
        return volume
    

