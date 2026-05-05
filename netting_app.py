import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="FX Netting & Risk Simulator", layout="wide")
st.title("📊 FX 포지션 관리 및 몬테카를로 시뮬레이터")

# 2. 세션 상태 초기화
if 'main_df' not in st.session_state:
    st.session_state['main_df'] = pd.DataFrame(columns=[
        'Date', 'Currency', 'Position', 'Amount', 'Budget Rate', 'Netted', 'Remark1', 'Remark2'
    ])

# 실시간 환율 엔진 (USD 기준 환산을 위해 USD 환율 포함)
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

# --- Tab 1: 데이터 관리 및 입력 (가이드 절대 유지) ---
with tab1:
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
    
    # 데이터 업로드 및 직접 입력 로직 (기존과 동일)
    col_up, col_form = st.columns([1, 1])
    with col_up:
        st.subheader("📁 파일 업로드")
        uploaded_file = st.file_uploader("CSV/Excel 파일을 선택하세요", type=['xlsx', 'csv'])
        if uploaded_file:
            if uploaded_file.name.endswith('.csv'):
                new_data = pd.read_csv(uploaded_file)
            else:
                new_data = pd.read_excel(uploaded_file)
            new_data.columns = [c.strip() for c in new_data.columns]
            mapping = {'날짜': 'Date', '통화': 'Currency', '포지션': 'Position', '금액': 'Amount', '예산 환율': 'Budget Rate', '네팅': 'Netted'}
            new_data = new_data.rename(columns=mapping)
            for col in ['Date', 'Currency', 'Position', 'Amount', 'Budget Rate', 'Netted', 'Remark1', 'Remark2']:
                if col not in new_data.columns:
                    new_data[col] = 0.0 if col in ['Amount', 'Budget Rate'] else (True if col == 'Netted' else "")
            if st.button("기존 데이터에 추가하기"):
                st.session_state['main_df'] = pd.concat([st.session_state['main_df'], new_data], ignore_index=True)
                st.success("데이터가 병합되었습니다.")

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
                new_row = pd.DataFrame([{'Date': f_date.strftime('%Y-%m-%d'), 'Currency': f_curr, 'Position': f_pos, 'Amount': f_amt, 'Budget Rate': f_budget, 'Netted': True, 'Remark1': f_remark, 'Remark2': ""}])
                st.session_state['main_df'] = pd.concat([st.session_state['main_df'], new_row], ignore_index=True)
                st.toast("항목 추가 완료")

    st.subheader("📋 전체 데이터 편집")
    if not st.session_state['main_df'].empty:
        edited_df = st.data_editor(st.session_state['main_df'], num_rows="dynamic", use_container_width=True)
        if st.button("💾 변경사항 저장"):
            st.session_state['main_df'] = edited_df
            st.success("저장되었습니다.")

# --- Tab 2: 네팅 분석 요약 (요청하신 달러 환산 로직 적용) ---
with tab2:
    st.subheader("⚖️ 통화별 네팅 포지션 및 달러 환산 요약")
    if not st.session_state['main_df'].empty:
        df_net = st.session_state['main_df'][st.session_state['main_df']['Netted'] == True].copy()
        
        if not df_net.empty:
            # 1. 통화별 Long/Short 합계 계산
            summary = df_net.groupby(['Currency', 'Position'])['Amount'].sum().unstack(fill_value=0)
            for pos in ['Long', 'Short']:
                if pos not in summary.columns: summary[pos] = 0.0
            
            summary['Net Position'] = summary['Long'] - summary['Short']
            
            # 2. 달러 환산액 계산 (행 끝에 추가)
            # 환산 공식: (해당통화/KRW) / (USD/KRW)
            usd_krw = real_rates.get("USD", 1400.0)
            summary['Current Rate(KRW)'] = summary.index.map(lambda x: real_rates.get(x, 0))
            summary['Net Amount (USD)'] = (summary['Net Position'] * summary['Current Rate(KRW)']) / usd_krw
            
            # 3. 테이블 출력 (통화별 합계 포함)
            st.dataframe(
                summary.style.format({
                    'Long': '{:,.2f}', 'Short': '{:,.2f}', 'Net Position': '{:,.2f}',
                    'Current Rate(KRW)': '{:,.2f}', 'Net Amount (USD)': '{:,.2f}'
                }),
                use_container_width=True
            )
            
            # 4. 하단 전체 달러 환산 합계 (Metric)
            total_usd_value = summary['Net Amount (USD)'].sum()
            st.markdown("---")
            col_total1, col_total2 = st.columns(2)
            with col_total1:
                st.metric("전체 포지션 달러 환산 합계", f"$ {total_usd_value:,.2f}")
            with col_total2:
                st.caption(f" 기준 환율 (USD/KRW): {usd_krw:,.2f}원")
        else:
            st.info("네팅 대상 데이터가 없습니다.")

# --- Tab 3: 리스크 시뮬레이션 (기본 유지) ---
with tab3:
    if not st.session_state['main_df'].empty:
        net_df = st.session_state['main_df'][st.session_state['main_df']['Netted'] == True].copy()
        if not net_df.empty:
            target_curr = st.selectbox("💱 분석 대상 통화 선택", net_df['Currency'].unique())
            curr_data = net_df[net_df['Currency'] == target_curr]
            
            total_amt = curr_data['Amount'].sum()
            avg_budget_rate = (curr_data)'