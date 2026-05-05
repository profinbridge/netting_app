import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from scipy.stats import norm

# 1. 페이지 설정
st.set_page_config(page_title="FX Netting & Risk Simulator", layout="wide")
st.title("📊 FX 포지션 관리 및 몬테카를로 시뮬레이터")

# 2. 세션 상태 초기화
if 'main_df' not in st.session_state:
    st.session_state['main_df'] = pd.DataFrame(columns=[
        'Date', 'Currency', 'Position', 'Amount', 'Budget Rate', 'Netted', 'Remark1', 'Remark2'
    ])

# 실시간 환율 엔진
@st.cache_data(ttl=3600)
def get_realtime_rates():
    tickers = {"USD": "USDKRW=X", "EUR": "EURKRW=X", "JPY": "JPYKRW=X", "CNY": "CNYKRW=X", "GBP": "GBPKRW=X"}
    current_rates = {}
    for curr, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker).history(period='1d')
            current_rates[curr] = data['Close'].iloc[-1]
        except:
            backup = {"USD": 1475.0, "EUR": 1580.0, "JPY": 9.5, "CNY": 203.0, "GBP": 1850.0}
            current_rates[curr] = backup.get(curr)
    return current_rates

real_rates = get_realtime_rates()

# 3. 탭 구성
tab1, tab2, tab3 = st.tabs(["📥 데이터 관리 및 입력", "⚖️ 네팅 분석 요약", "🧪 실시간 리스크 시뮬레이션"])

# --- Tab 1: 데이터 관리 및 입력 ---
with tab1:
    # [사용자 요청 사항] 가이드 섹션 절대 유지
    st.markdown("### 📘 CSV 파일 작성 및 업로드 가이드")
    with st.expander("👉 CSV 헤더별 상세 작성 규칙 (필독)", expanded=True):
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("""
            **📍 각 항목(Header) 설명**
            * **Date**: 외화 발생일 또는 결제 예정일 (YYYY-MM-DD)
            * **Currency**: 통화코드 (USD, EUR, JPY, CNY, GBP 중 선택)
            * **Position**: 자금 방향 (**Long**: 외화 유입/수출, **Short**: 외화 유출/수입)
            * **Amount**: 외화 금액 (쉼표 없이 숫자만 입력)
            * **Budget Rate**: 예산 환율 (리스크 분석의 기준점)
            * **Netted**: 네팅 포함 여부 (**True**: 분석에 포함, **False**: 제외)
            """)
        with col_g2:
            st.markdown("""
            **📍 비고란 및 주의사항**
            * **Remark1 (비고 1)**: 자유 기재 (거래처명, 프로젝트명 등)
            * **Remark2 (비고 2)**: 자유 기재 (증빙 및 기타 참고사항 등)
            * **파일 형식**: 반드시 **CSV (UTF-8)** 형식으로 저장하세요.
            * **대소문자**: Position 항목의 'Long', 'Short' 첫 글자는 대문자를 권장합니다.
            """)

    st.divider()
    
    col_up, col_form = st.columns([1, 1])
    with col_up:
        st.subheader("📁 파일 업로드")
        uploaded_file = st.file_uploader("CSV/Excel 파일을 선택하세요", type=['xlsx', 'csv'])
        if uploaded_file:
            if uploaded_file.name.endswith('.csv'):
                new_data = pd.read_csv(uploaded_file)
            else:
                new_data = pd.read_excel(uploaded_file)
            
            # 칼럼 매핑
            new_data.columns = [c.strip() for c in new_data.columns]
            mapping = {'날짜': 'Date', '통화': 'Currency', '포지션': 'Position', '금액': 'Amount', '예산 환율': 'Budget Rate', '네팅': 'Netted'}
            new_data = new_data.rename(columns=mapping)
            
            # 필수 칼럼 보장
            for col in ['Date', 'Currency', 'Position', 'Amount', 'Budget Rate', 'Netted', 'Remark1', 'Remark2']:
                if col not in new_data.columns:
                    new_data[col] = 0.0 if col in ['Amount', 'Budget Rate'] else (True if col == 'Netted' else "")
            
            if st.button("기존 데이터에 추가하기"):
                st.session_state['main_df'] = pd.concat([st.session_state['main_df'], new_data], ignore_index=True)
                st.success("데이터가 성공적으로 병합되었습니다.")

    with col_form:
        st.subheader("✍️ 개별 항목 직접 입력")
        with st.form("manual_entry", clear_on_submit=True):
            f_date = st.date_input("날짜")
            f_curr = st.selectbox("통화", ["USD", "EUR", "JPY", "CNY", "GBP"])
            f_pos = st.selectbox("포지션", ["Long", "Short"])
            f_amt = st.number_input("금액", min_value=0.0)
            f_budget = st.number_input("예산 환율", min_value=0.0, value=real_rates.get(f_curr, 1400.0))
            f_remark = st.text_input("비고 (Remark1)")
            
            if st.form_submit_button("추가"):
                new_row = pd.DataFrame([{
                    'Date': f_date.strftime('%Y-%m-%d'), 'Currency': f_curr, 'Position': f_pos, 
                    'Amount': f_amt, 'Budget Rate': f_budget, 'Netted': True, 'Remark1': f_remark, 'Remark2': ""
                }])
                st.session_state['main_df'] = pd.concat([st.session_state['main_df'], new_row], ignore_index=True)
                st.toast("항목이 추가되었습니다.")

    st.subheader("📋 전체 데이터 편집")
    if not st.session_state['main_df'].empty:
        edited_df = st.data_editor(
            st.session_state['main_df'], num_rows="dynamic", use_container_width=True,
            column_config={"Position": st.column_config.SelectboxColumn(options=["Long", "Short"]), "Netted": "네팅 포함"}
        )
        c1, c2 = st.columns([1, 5])
        if c1.button("💾 저장"):
            st.session_state['main_df'] = edited_df
            st.success("저장 완료")
        if c2.button("🗑️ 전체 초기화"):
            st.session_state['main_df'] = pd.DataFrame(columns=['Date', 'Currency', 'Position', 'Amount', 'Budget Rate', 'Netted', 'Remark1', 'Remark2'])
            st.rerun()

# --- Tab 2: 네팅 분석 요약 ---
with tab2:
    if not st.session_state['main_df'].empty:
        df_net = st.session_state['main_df'][st.session_state['main_df']['Netted'] == True].copy()
        if not df_net.empty:
            summary = df_net.groupby(['Currency', 'Position'])['Amount'].sum().unstack(fill_value=0)
            for col in ['Long', 'Short']:
                if col not in summary: summary[col] = 0.0
            summary['Net Position'] = summary['Long'] - summary['Short']
            st.dataframe(summary.style.format("{:,.2f}"), use_container_width=True)
        else:
            st.info("네팅 대상 데이터가 없습니다.")

# --- Tab 3: 리스크 시뮬레이션 (가중평균 예산환율) ---
with tab3:
    if not st.session_state['main_df'].empty:
        net_df = st.session_state['main_df'][st.session_state['main_df']['Netted'] == True].copy()
        target_curr = st.selectbox("💱 분석 대상 통화 선택", net_df['Currency'].unique())
        
        curr_data = net_df[net_df['Currency'] == target_curr]
        
        # 가중평균 예산 환율 계산
        total_amt = curr_data['Amount'].sum()
        if total_amt > 0:
            avg_budget_rate = (curr_data['Amount'] * curr_data['Budget Rate']).sum() / total_amt
        else:
            avg_budget_rate = real_rates.get(target_curr, 1400.0)

        rate_now = real_rates.get(target_curr, 1400.0)
        net_pos = curr_data.apply(lambda x: x['Amount'] if x['Position'] == 'Long' else -x['Amount'], axis=1).sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("순포지션", f"{net_pos:,.2f}")
        m2.metric("가중평균 예산 환율", f"{avg_budget_rate:,.2f}원")
        m3.metric("현재 환율", f"{rate_now:,.2f}원")

        # 시뮬레이션 엔진
        vol = st.sidebar.slider("연 변동성(%)", 1.0, 30.0, 10.0) / 100
        n_sims, t_days = 1000, 30
        dt = 1/252
        sims = np.zeros((t_days, n_sims))
        sims[0] = rate_now
        for t in range(1, t_days):
            sims[t] = sims[t-1] * np.exp((-0.5 * vol**2)*dt + vol * np.sqrt(dt) * np.random.standard_normal(n_sims))
        
        final_pnl = (sims[-1] - avg_budget_rate) * net_pos

        # 시각화
        c1, c2 = st.columns(2)
        with c1:
            fig_path = go.Figure()
            fig_path.add_trace(go.Scatter(y=np.median(sims, axis=1), name="중앙값", line=dict(color='blue')))
            fig_path.add_hline(y=avg_budget_rate, line_dash="dash", line_color="red", annotation_text="예산기준")
            st.plotly_chart(fig_path, use_container_width=True)
        with c2:
            fig_hist = px.histogram(final_pnl, nbins=50, title="예상 손익 분포")
            fig_hist.add_vline(x=0, line_color="black")
            st.plotly_chart(fig_hist, use_container_width=True)