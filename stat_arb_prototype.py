
from AlgoAPI import AlgoAPIUtil, AlgoAPI_Backtest
from datetime import datetime, timedelta
import statsmodels.api as sm

class AlgoEvent:
    def __init__(self):
        self.lasttradetime = datetime(2000,1,1)
        self.orderPairCnt = 0 
        self.osOrder = {}
        self.arrSize = 5
        self.myTakeProfit = 5
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
                # kick out the oldest observation if array size is too long
                if len(self.arr_closeY)>self.arrSize:
                    self.arr_closeY = self.arr_closeY[-self.arrSize:]
                if len(self.arr_closeX)>self.arrSize:
                    self.arr_closeX = self.arr_closeX[-self.arrSize:]
                # fit linear regression
                Y = self.arr_closeY
                X = self.arr_closeX
                X = sm.add_constant(X)   #add this line if you want to include intercept in the regression
                model = sm.OLS(Y, X)
                results = model.fit()
                self.evt.consoleLog(results.summary())
                coeff_b, tvalue, mse = results.params[-1], results.tvalues, results.mse_resid
                # compute current residual, e = Y - b*X
                diff = self.arr_closeY[-1] - coeff_b*self.arr_closeX[-1]
                
                if diff>0.1*mse:  # regard Y as overpriced, X as underpriced
                    self.orderPairCnt += 1
                    self.openOrder(-1, self.myinstrument_Y, self.orderPairCnt, 1)  #short Y
                    if coeff_b>0:
                        self.openOrder(1, self.myinstrument_X, self.orderPairCnt, abs(round(coeff_b,2)))   #long X
                    else:
                        self.openOrder(-1, self.myinstrument_X, self.orderPairCnt, abs(round(coeff_b,2)))   #short X
                elif diff<-0.1*mse:  # regard Y as underpriced, X as overpriced
                    self.orderPairCnt += 1
                    self.openOrder(1, self.myinstrument_Y, self.orderPairCnt, 1)  #long Y
                    if coeff_b>0:
                        self.openOrder(-1, self.myinstrument_X, self.orderPairCnt, abs(round(coeff_b,2)))   #short X
                    else:
                        self.openOrder(1, self.myinstrument_X, self.orderPairCnt, abs(round(coeff_b,2)))   #long X

            # check condition for close position
            myPair = self.matchPairTradeID()
            if len(myPair)>0:
                for tradeID, tradeID2 in myPair.items():
                    # detail for tradeID
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
                    pairPL = Volume1*buysell1*(bd[instrument1]['lastPrice'] - openprice1) + Volume2*buysell2*(bd[instrument2]['lastPrice'] - openprice2) 
                    # close the pair orders
                    if pairPL > self.myTakeProfit:
                        self.closeOrder(tradeID)
                        self.closeOrder(tradeID2)


    def matchPairTradeID(self):
        myPair = {}
        for tradeID in self.osOrder:
            orderRef = self.osOrder[tradeID]['orderRef']
            for tradeID2 in self.osOrder:
                orderRef2 = self.osOrder[tradeID2]['orderRef']
                if orderRef==orderRef2 and tradeID!=tradeID2 and tradeID not in myPair:
                    myPair[tradeID] = tradeID2
                    break
        return myPair

    def closeOrder(self, tradeID):
        order = AlgoAPIUtil.OrderObject(
            tradeID = tradeID,
            openclose = 'close'
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
        acdate = pl['Acdate']
        PL_instru1 = pl[self.myinstrument_X]['TotalPL']
        PL_instru2 = pl[self.myinstrument_Y]['TotalPL']
        TotalPL = pl['TotalPL']

    def on_openPositionfeed(self, op, oo, uo):
        self.osOrder = oo


