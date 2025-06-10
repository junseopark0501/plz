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
        return data
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
        return df
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

    if not stock_data.empty:
        st.subheader(f"{stock_ticker} 주가 차트")
        fig_stock = go.Figure(data=[go.Candlestick(x=stock_data.index,
                                                    open=stock_data['Open'],
                                                    high=stock_data['High'],
                                                    low=stock_data['Low'],
                                                    close=stock_data['Close'])])
        fig_stock.update_layout(xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_stock, use_container_width=True)

        st.subheader(f"{stock_ticker} 현재 가격")
        if 'Close' in stock_data.columns and not stock_data['Close'].empty:
            current_price = stock_data['Close'].iloc[-1]
            st.metric(label=f"{stock_ticker} 현재 가격", value=f"${current_price:,.2f}")
        else:
            st.info("현재 가격 정보를 가져올 수 없습니다.")

    else:
        st.info("주식 데이터를 가져올 수 없습니다. 티커와 기간을 확인해주세요.")

# --- 암호화폐 섹션 ---
st.sidebar.subheader("암호화폐 설정")
crypto_symbol = st.sidebar.text_input("암호화폐 심볼 입력 (예: BTC/USDT, ETH/USDT)", "BTC/USDT").upper()
exchange_list = [exchange_id for exchange_id in ccxt.exchanges if hasattr(getattr(ccxt, exchange_id), 'fetch_ohlcv')]
selected_exchange = st.sidebar.selectbox("거래소 선택", exchange_list, index=exchange_list.index('binance') if 'binance' in exchange_list else 0)

st.header("암호화폐 시장")
if st.button(f"{crypto_symbol} 암호화폐 가격 불러오기"):
    crypto_data = get_crypto_data(crypto_symbol, exchange_id=selected_exchange)

    if not crypto_data.empty:
        st.subheader(f"{crypto_symbol} 가격 차트 ({selected_exchange})")
        fig_crypto = go.Figure(data=[go.Candlestick(x=crypto_data.index,
                                                     open=crypto_data['open'],
                                                     high=crypto_data['high'],
                                                     low=crypto_data['low'],
                                                     close=crypto_data['close'])])
        fig_crypto.update_layout(xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_crypto, use_container_width=True)

        st.subheader(f"{crypto_symbol} 현재 가격")
        if 'close' in crypto_data.columns and not crypto_data['close'].empty:
            current_crypto_price = crypto_data['close'].iloc[-1]
            st.metric(label=f"{crypto_symbol} 현재 가격", value=f"${current_crypto_price:,.2f}")
        else:
            st.info("현재 가격 정보를 가져올 수 없습니다.")
    else:
        st.info("암호화폐 데이터를 가져올 수 없습니다. 심볼과 거래소를 확인해주세요.")

# --- 자동 새로고침 (선택 사항) ---
st.sidebar.markdown("---")
st.sidebar.subheader("자동 새로고침")
auto_refresh = st.sidebar.checkbox("자동 새로고침 사용 (주식/암호화폐 데이터)", value=False)
refresh_interval = st.sidebar.slider("새로고침 간격 (초)", 30, 300, 60, 30)

if auto_refresh:
    st.info(f"데이터가 {refresh_interval}초마다 자동으로 새로고침됩니다.")
    st.rerun() # Streamlit 앱을 새로고침하여 데이터를 다시 가져옴
    time.sleep(refresh_interval) # 다음 새로고침까지 대기

# --- 푸터 ---
st.markdown("---")
st.markdown("개발자: [당신의 GitHub 프로필 링크] | 데이터 출처: yfinance, CCXT")
