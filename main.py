import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import ccxt
import time
from datetime import datetime, timedelta

# --- 페이지 설정 ---
st.set_page_config(layout="wide", page_title="실시간 주식/암호화폐 가격 시각화")

st.title("📈 실시간 주식/암호화폐 가격 시각화 앱")

# --- 사이드바 설정 ---
st.sidebar.header("설정")

# --- 데이터 가져오기 함수 ---

@st.cache_data(ttl=60) # 60초마다 캐시 갱신
def get_stock_data(ticker, period="1d", interval="1m"):
    try:
        data = yf.download(ticker, period=period, interval=interval)
        # Ensure data is not empty and has required columns
        if not data.empty and all(col in data.columns for col in ['Open', 'High', 'Low', 'Close']):
            return data
        else:
            st.sidebar.warning(f"yfinance로 {ticker} 데이터를 가져왔으나, 필수 컬럼(Open, High, Low, Close)이 없거나 데이터가 비어 있습니다.")
            return pd.DataFrame()
    except Exception as e:
        st.sidebar.error(f"주식 데이터를 가져오는 데 실패했습니다: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=30) # 30초마다 캐시 갱신
def get_crypto_data(symbol, exchange_id='binance'):
    try:
        exchange = getattr(ccxt, exchange_id)()
        ohlcv = exchange.fetch_ohlcv(symbol, '1m') # 1분봉 데이터
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        # Ensure data is not empty and has required columns
        if not df.empty and all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            return df
        else:
            st.sidebar.warning(f"ccxt로 {symbol} 데이터를 가져왔으나, 필수 컬럼(open, high, low, close)이 없거나 데이터가 비어 있습니다.")
            return pd.DataFrame()
    except Exception as e:
        st.sidebar.error(f"암호화폐 데이터를 가져오는 데 실패했습니다: {e}")
        return pd.DataFrame()

# --- 주식 섹션 ---
st.sidebar.subheader("주식 설정")
stock_ticker = st.sidebar.text_input("주식 티커 입력 (예: AAPL, MSFT, TSLA)", "AAPL").upper()
stock_period = st.sidebar.selectbox("조회 기간 (주식)", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"])
stock_interval = st.sidebar.selectbox("인터벌 (주식)", ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "3mo"], index=0) # 1m이 1일 기간에만 가능

st.header("주식 시장")
if st.button(f"{stock_ticker} 주식 가격 불러오기"):
    if stock_period == "1d" and stock_interval not in ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"]:
        st.warning("1일 기간 선택 시 1분 미만 인터벌을 선택해야 합니다. 자동으로 '1m'으로 변경합니다.")
        stock_interval = "1m"
    if stock_period != "1d" and stock_interval == "1m":
        st.warning("1일 초과 기간 선택 시 1분 인터벌은 지원되지 않습니다. '1h' 또는 '1d' 이상으로 변경하세요.")

    stock_data = get_stock_data(stock_ticker, period=stock_period, interval=stock_interval)

    # --- 주식 차트 그리기 ---
    st.subheader(f"{stock_ticker} 주가 차트")
    if not stock_data.empty:
        fig_stock = go.Figure(data=[go.Candlestick(x=stock_data.index,
                                                     open=stock_data['Open'],
                                                     high=stock_data['High'],
                                                     low=stock_data['Low'],
                                                     close=stock_data['Close'])])
        fig_stock.update_layout(xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_stock, use_container_width=True)
    else:
        st.info("주식 데이터를 가져오지 못했습니다. 임시 차트를 표시합니다.")
        # 임시 데이터로 차트 생성 (앱이 깨지지 않게)
        dummy_data = pd.DataFrame({
            'Open': [100, 102, 101, 103, 102],
            'High': [103, 104, 103, 105, 104],
            'Low': [99, 100, 99, 101, 100],
            'Close': [102, 101, 102, 102, 103]
        }, index=pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05']))
        fig_stock_dummy = go.Figure(data=[go.Candlestick(x=dummy_data.index,
                                                      open=dummy_data['Open'],
                                                      high=dummy_data['High'],
                                                      low=dummy_data['Low'],
                                                      close=dummy_data['Close'])])
        fig_stock_dummy.update_layout(xaxis_rangeslider_visible=False, title="데이터 없음 (임시 차트)")
        st.plotly_chart(fig_stock_dummy, use_container_width=True)


    # --- 주식 현재 가격 표시 (강력한 오류 방지 로직) ---
    st.subheader(f"{stock_ticker} 현재 가격")
    current_price = None # 초기값 설정
    if not stock_data.empty and 'Close' in stock_data.columns and not stock_data['Close'].empty:
        # 마지막 유효한 숫자 값 찾기
        valid_prices = stock_data['Close'].dropna()
        if not valid_prices.empty:
            current_price = valid_prices.iloc[-1]

    if isinstance(current_price, (int, float)): # 숫자인 경우에만 포맷팅
        st.metric(label=f"{stock_ticker} 현재 가격", value=f"${current_price:,.2f}")
    else:
        st.info(f"{stock_ticker} 현재 가격 정보를 가져올 수 없습니다. (가격 데이터 유효성 문제)")
        st.metric(label=f"{stock_ticker} 현재 가격", value="N/A") # 오류 시 'N/A' 표시


# --- 암호화폐 섹션 ---
st.sidebar.subheader("암호화폐 설정")
crypto_symbol = st.sidebar.text_input("암호화폐 심볼 입력 (예: BTC/USDT, ETH/USDT)", "BTC/USDT").upper()
exchange_list = [exchange_id for exchange_id in ccxt.exchanges if hasattr(getattr(ccxt, exchange_id), 'fetch_ohlcv')]
selected_exchange = st.sidebar.selectbox("거래소 선택", exchange_list, index=exchange_list.index('binance') if 'binance' in exchange_list else 0)

st.header("암호화폐 시장")
if st.button(f"{crypto_symbol} 암호화폐 가격 불러오기"):
    crypto_data = get_crypto_data(crypto_symbol, exchange_id=selected_exchange)

    # --- 암호화폐 차트 그리기 ---
    st.subheader(f"{crypto_symbol} 가격 차트 ({selected_exchange})")
    if not crypto_data.empty:
        fig_crypto = go.Figure(data=[go.Candlestick(x=crypto_data.index,
                                                     open=crypto_data['open'],
                                                     high=crypto_data['high'],
                                                     low=crypto_data['low'],
                                                     close=crypto_data['close'])])
        fig_crypto.update_layout(xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_crypto, use_container_width=True)
    else:
        st.info("암호화폐 데이터를 가져오지 못했습니다. 임시 차트를 표시합니다.")
        # 임시 데이터로 차트 생성 (앱이 깨지지 않게)
        dummy_data_crypto = pd.DataFrame({
            'open': [30000, 30500, 30200, 30800, 30600],
            'high': [30600, 30800, 30500, 31000, 30900],
            'low': [29800, 30200, 30000, 30400, 30500],
            'close': [30500, 30200, 30400, 30600, 30800]
        }, index=pd.to_datetime(['2024-01-01 00:00', '2024-01-01 01:00', '2024-01-01 02:00', '2024-01-01 03:00', '2024-01-01 04:00']))
        fig_crypto_dummy = go.Figure(data=[go.Candlestick(x=dummy_data_crypto.index,
                                                           open=dummy_data_crypto['open'],
                                                           high=dummy_data_crypto['high'],
                                                           low=dummy_data_crypto['low'],
                                                           close=dummy_data_crypto['close'])])
        fig_crypto_dummy.update_layout(xaxis_rangeslider_visible=False, title="데이터 없음 (임시 차트)")
        st.plotly_chart(fig_crypto_dummy, use_container_width=True)


    # --- 암호화폐 현재 가격 표시 (강력한 오류 방지 로직) ---
    st.subheader(f"{crypto_symbol} 현재 가격")
    current_crypto_price = None # 초기값 설정
    if not crypto_data.empty and 'close' in crypto_data.columns and not crypto_data['close'].empty:
        # 마지막 유효한 숫자 값 찾기
        valid_crypto_prices = crypto_data['close'].dropna()
        if not valid_crypto_prices.empty:
            current_crypto_price = valid_crypto_prices.iloc[-1]

    if isinstance(current_crypto_price, (int, float)): # 숫자인 경우에만 포맷팅
        st.metric(label=f"{crypto_symbol} 현재 가격", value=f"${current_crypto_price:,.2f}")
    else:
        st.info(f"{crypto_symbol} 현재 가격 정보를 가져올 수 없습니다. (가격 데이터 유효성 문제)")
        st.metric(label=f"{crypto_symbol} 현재 가격", value="N/A") # 오류 시 'N/A' 표시


# --- 자동 새로고침 (선택 사항) ---
st.sidebar.markdown("---")
st.sidebar.subheader("자동 새로고침")
auto_refresh = st.sidebar.checkbox("자동 새로고침 사용 (주식/암호화폐 데이터)", value=False)
refresh_interval = st.sidebar.slider("새로고침 간격 (초)", 30, 300, 60, 30)

if auto_refresh:
    st.info(f"데이터가 {refresh_interval}초마다 자동으로 새로고침됩니다.")
    # st.rerun() 대신 time.sleep을 사용하면 Streamlit Cloud에서 특정 조건에서
    # 무한 루프처럼 동작할 수 있으므로, 실제 운영 환경에서는 주의해야 합니다.
    # 단순 시연 목적이라면 괜찮지만, 실제 앱에서는 다른 자동 새로고침 메커니즘을 고려할 수 있습니다.
    time.sleep(refresh_interval)
    st.rerun() # time.sleep 후 rerun을 호출하여 다음 턴에 다시 실행되도록 함

# --- 푸터 ---
st.markdown("---")
st.markdown("개발자: [당신의 GitHub 프로필 링크] | 데이터 출처: yfinance, CCXT")
