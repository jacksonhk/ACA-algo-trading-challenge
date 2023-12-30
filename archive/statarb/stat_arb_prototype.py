

from AlgoAPI import AlgoAPIUtil, AlgoAPI_Backtest
from datetime import datetime, timedelta
import talib
import statsmodels.api as sm
import matplotlib.pyplot as plt
import numpy as np

class AlgoEvent:
    def __init__(self):
        self.lasttradetime = datetime(2000,1,1)
        self.orderPairCnt = 0 
        self.osOrder = {}
        self.arrSize = 120
        self.myTakeProfitupper = 1
        self.myTakeProfitlower = -1
        self.myStopLoss = -1
        self.arr_closeY = []
        self.arr_closeX = []
        self.count = 0
        
        

    def start(self, mEvt):
        self.myinstrument_Y = mEvt['subscribeList'][0]
        self.myinstrument_X = mEvt['subscribeList'][1]
        self.evt = AlgoAPI_Backtest.AlgoEvtHandler(self, mEvt)
        self.evt.start()
        

    def on_bulkdatafeed(self, isSync, bd, ab):
        
        
        if isSync:
            # fill the entire initial array with data before actual trading the algo
            if not self.count > self.arrSize:
                self.count += 1
                self.arr_closeY.append(bd[self.myinstrument_Y]['lastPrice'])
                self.arr_closeX.append(bd[self.myinstrument_X]['lastPrice'])
                return
            
            if bd[self.myinstrument_Y]['timestamp'] >= self.lasttradetime + timedelta(hours = 24):
                self.lasttradetime = bd[self.myinstrument_Y]['timestamp']
                # collect observations
                self.arr_closeY.append(bd[self.myinstrument_Y]['lastPrice'])
                self.arr_closeX.append(bd[self.myinstrument_X]['lastPrice'])
                
                # TODO: wrong calculation???, we should do OLS on return instead of lastPrice
                
                
                # kick out the oldest observation if array size is too long
                if len(self.arr_closeY)>self.arrSize:
                    self.arr_closeY = self.arr_closeY[-self.arrSize:]
                if len(self.arr_closeX)>self.arrSize:
                    self.arr_closeX = self.arr_closeX[-self.arrSize:]
                # fit linear regression
                Y = self.arr_closeY
                X = self.arr_closeX
                X = sm.add_constant(X)   #add this line if you want to include intercept in the regression // should not add since the mean is irrelevant in stat arb
                model = sm.OLS(Y, X)
                results = model.fit()
                self.evt.consoleLog(results.summary())
                coeff_b, tvalue, mse = results.params[-1], results.tvalues, results.mse_resid
                # compute current residual, e = Y - b*X
                
                if coeff_b:
                    hedge_ratio = coeff_b
                else:
                    hedge_ratio = bd[self.myinstrument_X]['lastPrice'] / bd[self.myinstrument_Y]['lastPrice']
                
                available_balance = ab['availableBalance']
                Y_ratio = 0.475
                Y_position = (available_balance*Y_ratio) / bd[self.myinstrument_Y]['lastPrice']
                X_position = Y_position * abs(round(hedge_ratio, 10))
                total = X_position * bd[self.myinstrument_X]['lastPrice'] + available_balance*Y_ratio
                while total < 0.8 * available_balance:
                    Y_ratio *= 1.05
                    Y_position = (available_balance*Y_ratio) / bd[self.myinstrument_Y]['lastPrice']
                    X_position = Y_position * abs(round(hedge_ratio, 10))
                    total = X_position * bd[self.myinstrument_X]['lastPrice'] + available_balance*Y_ratio
                while total > available_balance:
                    Y_ratio *= 0.95
                    Y_position = (available_balance*Y_ratio) / bd[self.myinstrument_Y]['lastPrice']
                    X_position = Y_position * abs(round(hedge_ratio, 10))
                    total = X_position * bd[self.myinstrument_X]['lastPrice'] + available_balance*Y_ratio
                
                    
                    
                spread_ratio = np.array(self.arr_closeY) / np.array(self.arr_closeX)
                
                z_array = (spread_ratio - np.full(self.arrSize, np.mean(spread_ratio)))/ np.full(self.arrSize, np.std(spread_ratio))
                
                cur_spread_ratio = spread_ratio[-1] 
                z_score = (cur_spread_ratio - np.mean(spread_ratio)) / np.std(spread_ratio) 
                self.cur_z_score = z_score
                
                z_upper_threshold = np.mean(z_array) + 2 * np.std(z_array) 
                z_lower_threshold = np.mean(z_array) - 2 * np.std(z_array) 
                
                # dynamic z value threshold to capture near term extremum
                # complement absolute z-score
                
                
                # required position in Y to hedge X = position of X * hedge ratio
                
                # TODO: logic to check if there is currently open position, if yes, do not trade
                if len(self.osOrder) == 0:
                    # logic to check the hedge ratio
                    if z_score > z_upper_threshold or z_score > 2:  # regard Y as overpriced, X as underpriced
                        self.orderPairCnt += 1 # increment number of pair by 1
                        self.myTakeProfitupper = (z_upper_threshold + z_lower_threshold) / 2 + 0.5*np.std(z_array) # take profit when revert to mean
                        self.myTakeProfitlower = (z_upper_threshold + z_lower_threshold) / 2 - 0.5*np.std(z_array)
                        self.openOrder(-1, self.myinstrument_Y, str(self.orderPairCnt), Y_position)  #short Y
                        self.openOrder(1, self.myinstrument_X, str(self.orderPairCnt), X_position)   #long X
                        return
                        ###if coeff_b>0:
                            ###self.openOrder(1, self.myinstrument_X, self.orderPairCnt, X_position)   #long X
                        #else:
                            #self.openOrder(-1, self.myinstrument_X, self.orderPairCnt, X_position)   #short X
                            
                    if z_score < z_lower_threshold or z_score < -2:  # regard Y as underpriced, X as overpriced
                        self.orderPairCnt += 1 # increment number of pair by 1
                        self.myTakeProfitupper = (z_upper_threshold + z_lower_threshold) / 2 + 0.5*np.std(z_array) # take profit when revert to mean
                        self.myTakeProfitlower = (z_upper_threshold + z_lower_threshold) / 2 - 0.5*np.std(z_array)
                        self.openOrder(1, self.myinstrument_Y, str(self.orderPairCnt), Y_position)  #long Y
                        self.openOrder(-1, self.myinstrument_X, str(self.orderPairCnt), X_position)   #short X
                        return
                        #if coeff_b>0:
                            #self.openOrder(-1, self.myinstrument_X, self.orderPairCnt, X_position)   #short X
                        #else:
                            #self.openOrder(1, self.myinstrument_X, self.orderPairCnt, X_position)  #long X

            # check condition for close position
            myPair = self.matchPairTradeID()
            if len(myPair)>0:
                for tradeID, tradeID2 in myPair.items():
                    # detail for tradeID
                    if tradeID in self.osOrder or tradeID2 in self.osOrder:
                        instrument1 = self.osOrder[tradeID]['instrument']
                        buysell1 = self.osOrder[tradeID]['buysell']
                        openprice1 = self.osOrder[tradeID]['openprice']
                        Volume1 = self.osOrder[tradeID]['Volume']
                        # detail for tradeID2
                        instrument2 = self.osOrder[tradeID2]['instrument']
                        buysell2 = self.osOrder[tradeID2]['buysell']
                        openprice2 = self.osOrder[tradeID2]['openprice']
                        Volume2 = self.osOrder[tradeID2]['Volume']
                        
                        # compute total PL for this pair
                        # pair 1 - pair 2
                        pairPL = Volume1*buysell1*(bd[instrument1]['lastPrice'] - openprice1) + Volume2*buysell2*(bd[instrument2]['lastPrice'] - openprice2) 
                        
                        position_value = abs(Volume1*buysell1*openprice1) + abs(Volume2*buysell2*openprice2) # position value
                        pairPL_percent = (pairPL / position_value) * 100.0 # PnL %
                        
                        # close the pair orders
                        
                        #TODO: better TakeProfit logic
                        
                        # Take Profit Logic
                        # update to z-score
                        
                        # consider z-value reverting to the range near mean to take profit
                        if self.myTakeProfitlower < self.cur_z_score < self.myTakeProfitupper:
                            self.closeOrder(tradeID, instrument1, self.opOrder[instrument1]['netVolume'])
                            self.closeOrder(tradeID2, instrument2, self.opOrder[instrument2]['netVolume'])
                            self.clearNakedPosition()
   

                        
                        # Stop Loss Logic
                        elif pairPL_percent < self.myStopLoss:
                            self.closeOrder(tradeID, instrument1, self.opOrder[instrument1]['netVolume'])
                            self.closeOrder(tradeID2, instrument2, self.opOrder[instrument2]['netVolume'])
                            self.clearNakedPosition()
                    
                    else:
                        # error handling log
                        error_msg = f"The following tradeID does not exist: {tradeID}, {tradeID2}"
                        self.evt.consoleLog(error_msg)
            

                

    def matchPairTradeID(self):
        myPair = {}
        for tradeID in self.osOrder:
            orderRef = self.osOrder[tradeID]['orderRef']
            for tradeID2 in self.osOrder:
                orderRef2 = self.osOrder[tradeID2]['orderRef']
                if orderRef==orderRef2 and tradeID is not tradeID2 and tradeID not in myPair and tradeID2 not in myPair:
                    myPair[tradeID] = tradeID2 
                    break
        return myPair

    def closeOrder(self, tradeID, instrument, volume):
        open_position = self.osOrder[tradeID]
        
        if open_position['instrument'] != instrument:
            return
        
        if self.opOrder[instrument]['netVolume'] <= volume:
            volume = self.opOrder[instrument]['netVolume']
        
        order = AlgoAPIUtil.OrderObject(
            tradeID = tradeID,
            openclose = 'close',
            instrument = instrument,
            volume = volume
        )
        self.evt.sendOrder(order)

    def openOrder(self, buysell, instrument, orderRef, volume):
        order = AlgoAPIUtil.OrderObject(
            instrument=instrument,
            orderRef=orderRef,
            volume=volume,
            openclose='open',
            buysell=buysell,
            ordertype=0       #0=market_order, 1=limit_order, 2=stop_order
        )
        self.evt.sendOrder(order)

    def on_marketdatafeed(self, md, ab):
        pass

    def on_orderfeed(self, of):
        pass

    def on_dailyPLfeed(self, pl):
        self.clearNakedPosition()
    
    def on_openPositionfeed(self, op, oo, uo):
        self.osOrder = oo
        self.opOrder = op
        volX = self.opOrder[self.myinstrument_X]['netVolume']
        volY = self.opOrder[self.myinstrument_Y]['netVolume']
        if volX == 0 and volY == 0:
            self.osOrder = {}
    
    def clearNakedPosition(self):
        if len(self.osOrder) % 2 == 1:
            volX = self.opOrder[self.myinstrument_X]['netVolume']
            volY = self.opOrder[self.myinstrument_Y]['netVolume']
            if volX > 0:
                self.orderPairCnt += 1
                self.openOrder(-1, self.myinstrument_X, self.orderPairCnt, abs(volX))
            elif volX < 0:
                self.orderPairCnt += 1
                self.openOrder(1, self.myinstrument_X, self.orderPairCnt, abs(volX))
            if volY > 0:
                self.orderPairCnt += 1
                self.openOrder(-1, self.myinstrument_Y, self.orderPairCnt, abs(volY))
            elif volY < 0:
                self.orderPairCnt += 1
                self.openOrder(1, self.myinstrument_Y, self.orderPairCnt, abs(volY))
            self.osOrder = {}
        elif self.orderPairCnt > 1:
            volX = self.opOrder[self.myinstrument_X]['netVolume']
            volY = self.opOrder[self.myinstrument_Y]['netVolume']
            if volX and volY:
                return
            elif volX:
                if volX > 0:
                    self.orderPairCnt += 1
                    self.openOrder(-1, self.myinstrument_X, self.orderPairCnt, abs(volX))
                elif volX < 0:
                    self.orderPairCnt += 1
                    self.openOrder(1, self.myinstrument_X, self.orderPairCnt, abs(volX))
            elif volY:
                if volY > 0:
                    self.orderPairCnt += 1
                    self.openOrder(-1, self.myinstrument_Y, self.orderPairCnt, abs(volY))
                elif volY < 0:
                    self.orderPairCnt += 1
                    self.openOrder(1, self.myinstrument_Y, self.orderPairCnt, abs(volY))
            self.osOrder = {}
    # TODO (Done): use z-score instead of diff for open position logic
        #TODO b.: adjust z-score threshold from 1.0 to others;
    # TODO(urgent1): set rule to invest in fixed portion of portfolio 
    # idea: get fixed portion of portfolio. Then calculate hedge ratio, than calculate the each position as a % of the fixed portfion of portfolio
    # TODO2(urgent2): set rule to stop opening new position if there is existing positions
    
    
    # TODO3(done)_need opmtization: Stop loss logic (do this first)
    # TODO4: z-score graph and price graph using plt
    # TODO5(urgent): better takeprofit using z-score
    # TODO6: stop loss during the 5 mins break (now only recalculate every time)
    
    # TODO7: handle case of insufficient balance
    #BUG1: duplicate action to close order (solved): solution: set timedelta to hours = 24









