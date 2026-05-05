import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. 페이지 설정
st.set_page_config(page_title="2022 Crisis Simulator | ProFinBridge", layout="wide")

# CSS 스타일 수정
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

st.title("📉 2022 금리 인상기 위기 스트레스 테스트")
st.subheader("ProFinBridge Digital Solution: 과거의 위기 데이터로 현재의 리스크를 계측합니다.")

# 2. 사이드바: 입력창
with st.sidebar:
    st.header("🏢 기업 포지션 설정")
    exposure = st.number_input("월평균 외화 결제액 (USD)", min_value=10000, value=1000000, step=50000)
    budget_rate = st.slider("사장님의 예산 환율 (KRW)", min_value=1150, max_value=1500, value=1250)
    st.markdown("---")
    st.write("💡 **Tip:** 2022년 고점은 1,444원이었습니다.")

# 3. 데이터 엔진
@st.cache_data
def get_historical_data():
    df = yf.download("USDKRW=X", start="2022-01-01", end="2022-12-31")
    return df

data = get_historical_data()

# 👉 [에러 해결!] 여기서 복잡한 표를 1차원 데이터로 꽉 짜줍니다.
close_price = data['Close'].squeeze()

# 4. 분석 로직 (수정됨)
max_rate = float(close_price.max())
max_date = close_price.idxmax().strftime('%Y-%m-%d')
total_loss = (max_rate - budget_rate) * exposure 

# 5. 메인 대시보드 구성
col1, col2, col3 = st.columns(3)
col1.metric("2022년 최고 환율", f"{max_rate:,.2f} 원")
col2.metric("최고점 도달일", max_date)
col3.metric("나의 예산 환율", f"{budget_rate:,.0f} 원")

st.markdown("---")

# 그래프 시각화 (수정됨)
fig = go.Figure()
fig.add_trace(go.Scatter(x=close_price.index, y=close_price, name="USD/KRW", line=dict(color='#1a2a4c', width=3)))
fig.add_hline(y=budget_rate, line_dash="dash", line_color="#fbbf24", annotation_text="나의 예산 환율")
fig.update_layout(title="2022년 환율 추이 및 리스크 구간", template="plotly_white", height=500)
st.plotly_chart(fig, use_container_width=True)

# 6. 리스크 진단 결과 박스
st.error(f"⚠️ **스트레스 테스트 진단:** 2022년과 같은 위기 재발 시, 사장님은 약 **{total_loss/1000000:,.0f}백만 원**의 추가 원가 부담이 발생합니다.")

st.info(f"""
**[뱅커의 제언]**
단순히 환율이 오를 것 같다는 막연한 불안감보다, **{max_rate:,.2f}원**이라는 실제 위기 데이터를 직시해야 합니다. 
현재 포지션에서 선물환 헤지 비율을 30~50%만 유지했어도 위 손실액의 상당 부분을 방어할 수 있었습니다.
""")