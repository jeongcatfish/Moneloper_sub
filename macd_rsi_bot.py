import threading
from datetime import datetime, timedelta
from binance_f import RequestClient
from binance_f.model import *
import talib.abstract as ta
import numpy as np
#from File_class import File_class
from binance_f.constant.test import *
from binance_f.base.printobject import *
from time import sleep
from datetime import datetime
from keys import keys

class bot:
    def __init__(self):
        self. keys = keys()
        self.request_client = RequestClient(api_key=self.keys.get_key(), secret_key=self.keys.get_secret_key())
        self.init_variable()
        self.main()

    def init_variable(self):
        self.macd_golden_cross = False
        self.macd_dead_corss = False
        self.macd_Is_above_zero = False
        self.atr_over_top = False
        self.rsi_over_top = False
        self.rsi_over_bottom = False
        self.current_position = "none"
        #self.atr_over_bottom = False
        #self.atr_toucH_middle = False #atr이 bitcoin에서 좋은모습을 보이지 못하고 rsi로 충분히 대처가 가능할 것 같다 일단 빼자..

        self.dead_line_value = 0 # 이 값에 닿으면 손절한다.
        self.dead_line_percent = 0.007 # 코인 가격이 구매 했을 때 가격보다 2%차이가 나면 손절
        self.purchased_price = 0 # 구입 가격
        self.cut = False #지지선 넘는 신호

    def main(self):
        #self.post_order("BUY")
        self.memo_trading("trading test for memo")
        update_15m = threading.Thread(target=self.update_candle_stick_15m)
        trading = threading.Thread(target=self.thread_trading)
        update_15m.start()
        trading.start()
    def thread_trading(self):
        while True:
            if self.cut == True: # 어떤 포지션이든 손절
                print(f'[cut] purchased price : {self.purchased_price} price : {self.now_price}')
                print(f'[lose] purchased price : {self.purchased_price} price : {self.now_price}')
                self.current_position = "none"
                self.purchased_price = 0

            if self.current_position == "none": #포지션이 없을 때
                if self.macd_golden_cross: #롱 매수
                    self.purchased_price = self.now_price
                    self.dead_line_value = self.purchased_price-(self.purchased_price * self.dead_line_percent)
                    print(f'[buy_in long trade] price : {self.purchased_price}  dead_line : {self.dead_line_value} current_position : {self.current_position}')
                    self.memo_trading(f'[buy_in long trade] price : {self.purchased_price}  dead_line : {self.dead_line_value} time : {datetime.now()}  current_position : {self.current_position}')
                    self.current_position = "macd_long"
                # elif self.macd_dead_corss: #숏 매도
                #     self.purchased_price = self.now_price
                #     self.dead_line_value = self.purchased_price+(self.purchased_price * self.dead_line_percent)
                #     print(f'[buy_in short trade] price : {self.purchased_price}  dead_line : {self.dead_line_value} current_position : {self.current_position}')
                #     self.memo_trading(f'[buy_in short trade] price : {self.purchased_price}  dead_line : {self.dead_line_value} time : {datetime.now()}  current_position : {self.current_position}')
                #     self.current_position = "macd_short"

            elif self.current_position == "macd_long": #포지션 정리
                if self.rsi_over_top:
                    print(f'[sell_out short trade] purchased price : {self.purchased_price} price : {self.now_price}')
                    if self.purchased_price > self.now_price:
                        self.memo_trading(f'[lose] purchased price : {self.purchased_price} price : {self.now_price}  time : {datetime.now()}')
                    else:
                        self.memo_trading(f'[win] purchased price : {self.purchased_price} price : {self.now_price}  time : {datetime.now()}')
                    self.init_variable()
            # elif self.current_position == "macd_short": #포지션 정리
            #     if self.rsi_over_bottom:
            #         if self.purchased_price < self.now_price:
            #             print(f'[win] purchased price : {self.purchased_price} price : {self.now_price}  time : {datetime.now()}')
            #         else:
            #             print(f'[lose] purchased price : {self.purchased_price} price : {self.now_price}  time : {datetime.now()}')
            #         self.init_variable()
            sleep(1)

    #1초에 한 번 15분봉 데이터를 불러옴
    def update_candle_stick_15m(self):
        while True:
            try:
                self.candle_stick_list = self.request_client.get_candlestick_data(symbol="BTCUSDT",
                                                                                    interval=CandlestickInterval.MIN15,
                                                                                    startTime=None,
                                                                                    endTime=self.request_client.get_servertime(),
                                                                                    limit=50)
                trash_Arr = []
                for stick in self.candle_stick_list:
                    trash_Arr.append(float(stick.close))
                self.candle_stick_15m_np_array = np.array(trash_Arr, dtype='f8')
                self.now_price = float(self.candle_stick_list[-1].close)

                self.check_macd_signal() #macd 시그널 확인
                self.check_rsi_signal() #rsi 시그널 확인
            except Exception as e:
                print(f'에러 : {e}')
            sleep(1)

    def check_macd_signal(self):
        macd_list, macdsignal_list, macd_hist_list = ta.MACD(self.candle_stick_15m_np_array, fastperiod=12, slowperiod=26, signalperiod=9)
        macd = float(macd_list[-1])
        macdsignal = float(macdsignal_list[-1])
        macd_hist = float(macd_hist_list[-1])
        macd_hist_pre = float(macd_hist_list[-2])

        if self.dead_line_value == 0:
            # macd 값이 0선 아래에 있을 때
            if macd < 0 and macdsignal < 0:
                self.macd_Is_above_zero = False
            # macd 값이 0선 위에 있을 때
            elif macd > 0 and macdsignal > 0:
                self.macd_Is_above_zero = True
            # 골든 크로스 되었을 때
            if macd > macdsignal and self.macd_Is_above_zero == False and macd_hist_pre < 0 and macd_hist > 0:
                self.macd_golden_cross = True
                self.macd_dead_corss = False
            # 데드 크로스 되었을 때
            elif macd < macdsignal and self.macd_Is_above_zero == True:
                self.macd_golden_cross = False
                self.macd_dead_corss = True
        elif self.dead_line_value != 0: #포지션 가지고 있고
            if self.current_position == "macd_long": #현재 포지션이 롱이고
                if self.dead_line_value < self.now_price: #데드라인 보다 높은 가격에 위치해 있고
                    if macd < macdsignal and macd > 0: # 데드크로스 나고 0선 보다 위에 있으면
                        self.macd_golden_cross = False
                        self.macd_dead_corss = True
                elif self.dead_line_value > self.now_price: #데드라인 보다 낮은 가격에 위치해 있으면 손절
                    self.macd_golden_cross = False
                    self.macd_dead_corss = False
                    self.cut = True
            #숏 있던거 지움.

        print(f'macd : {macd} macd_signal : {macdsignal} macd_hist {macd_hist}  price : {self.now_price}')

    def check_rsi_signal(self):
        rsi = float(ta.RSI(self.candle_stick_15m_np_array, timperiod=14)[-1])
        low = 30
        high = 70

        if rsi > low and rsi < high: # 중간 값 횡보 중..
            self.rsi_status = "middle"
            self.rsi_over_top = False
            self.rsi_over_bottom = False
        if rsi > high and self.rsi_status == "middle": #rsi 70 상단돌파
            self.rsi_status = "high"
            self.rsi_over_top = True
            self.rsi_over_bottom = False
        if rsi < low and self.rsi_status == "middle": #rsi 30 하단돌파
            self.rsi_status == "low"
            self.rsi_over_top = False
            self.rsi_over_bottom = True



    def post_order(self, side, order_type="MARKET", quantity=0.001):
        if side == "BUY" and order_type == "MARKET":
            result = self.request_client.post_order(symbol="BTCUSDT", side=OrderSide.BUY,
                                                    ordertype=OrderType.MARKET, quantity=quantity)
        elif side == "SELL" and order_type == "MARKET":
            result = self.request_client.post_order(symbol="BTCUSDT", side=OrderSide.SELL,
                                                    ordertype=OrderType.MARKET, quantity=quantity)
        #self.my_money = self.get_balance()

    def memo_trading(self, data):
        f = open("C:/Users/admin/Documents/trading_test.txt", 'a')
        f.write(f'{data}\n')
        f.close()
if __name__ == "__main__" :
    my_bot = bot()

