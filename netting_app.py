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

# --- Tab 1: 데이터 관리 및 입력 (가이드 유지) ---
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
            * **Amount**: 외화 금액 (숫자만 입력)
            * **Budget Rate**: 예산 환율 (리스크 분석 기준점)
            * **Netted**: 네팅 포함 여부 (**True**: 포함, **False**: 제외)
            """)
        with col_g2:
            st.markdown("""
            **📍 비고란 및 주의사항**
            * **Remark1/2**: 자유 기재
            * **파일 형식**: 반드시 **CSV (UTF-8)** 형식 저장
            * **대소문자**: Position 항목 'Long', 'Short' 권장
            """)

    st.divider()
    
    col_up, col_form = st.columns([1, 1])
    with col_up:
        st.subheader("📁 파일 업로드")
        uploaded_file = st.file_uploader("CSV/Excel 선택", type=['xlsx', 'csv'])
        if uploaded_file:
            new_data = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            new_data.columns = [c.strip() for c in new_data.columns]
            mapping = {'날짜': 'Date', '통화': 'Currency', '포지션': 'Position', '금액': 'Amount', '예산 환율': 'Budget Rate', '네팅': 'Netted'}
            new_data = new_data.rename(columns=mapping)
            for col in ['Date', 'Currency', 'Position', 'Amount', 'Budget Rate', 'Netted', 'Remark1', 'Remark2']:
                if col not in new_data.columns:
                    new_data[col] = 0.0 if col in ['Amount', 'Budget Rate'] else (True if col == 'Netted' else "")
            if st.button("데이터 추가하기"):
                st.session_state['main_df'] = pd.concat([st.session_state['main_df'], new_data], ignore_index=True)
                st.success("데이터 병합 성공")

    with col_form:
        st.subheader("✍️ 직접 입력")
        with st.form("manual_entry", clear_on_submit=True):
            f_date = st.date_input("날짜")
            f_curr = st.selectbox("통화", ["USD", "EUR", "JPY", "CNY", "GBP"])
            f_pos = st.selectbox("포지션", ["Long", "Short"])
            f_amt = st.number_input("금액", min_value=0.0)
            f_budget = st.number_input("예산 환율", min_value=0.0, value=real_rates.get(f_curr, 1400.0))
            if st.form_submit_button("추가"):
                new_row = pd.DataFrame([{'Date': f_date.strftime('%Y-%m-%d'), 'Currency': f_curr, 'Position': f_pos, 'Amount': f_amt, 'Budget Rate': f_budget, 'Netted': True, 'Remark1': "", 'Remark2': ""}])
                st.session_state['main_df'] = pd.concat([st.session_state['main_df'], new_row], ignore_index=True)

    if not st.session_state['main_df'].empty:
        st.subheader("📋 전체 데이터 편집")
        edited_df = st.data_editor(st.session_state['main_df'], num_rows="dynamic", use_container_width=True)
        if st.button("💾 저장"):
            st.session_state['main_df'] = edited_df
            st.success("저장되었습니다.")

# --- Tab 2: 상세 포지션 내역 및 네팅 현황 (요청하신 로직) ---
# --- Tab 2: 상세 포지션 내역 및 네팅 현황 (수정본) ---
with tab2:
    df_t2 = st.session_state['main_df'].copy()

    if not df_t2.empty:
        st.subheader("⚖️ 상세 포지션 및 네팅 현황")
        
        interval = st.radio("📊 집계 구간 선택", ["일별", "주별", "월별"], horizontal=True, key="t2_interval_v5")
        
        df_t2['Date'] = pd.to_datetime(df_t2['Date'])
        rule = {'일별': 'D', '주별': 'W', '월별': 'ME'}[interval]
        net_df = df_t2[df_t2['Netted'] == True].copy()
        
        if not net_df.empty:
            # 1. 상단 요약 지표 (기존 유지)
            unique_currs = sorted(net_df['Currency'].unique(), key=lambda x: (x != 'USD', x))
            usd_krw = real_rates.get("USD", 1400.0)
            
            # 2. 데이터 집계 및 피벗
            grouped = net_df.set_index('Date').groupby([pd.Grouper(freq=rule), 'Currency'])
            rows = []
            for (dt, curr), group in grouped:
                long_v = group[group['Position'].str.strip().str.capitalize() == 'Long']['Amount'].sum()
                short_v = group[group['Position'].str.strip().str.capitalize() == 'Short']['Amount'].sum()
                net_v = long_v - short_v
                
                # 행별 달러 환산액 계산
                rate = real_rates.get(curr, 0)
                usd_val = (net_v * rate) / usd_krw if curr != "USD" else net_v
                
                if interval == '일별': label = dt.strftime('%Y-%m-%d')
                elif interval == '주별': label = dt.strftime('%Y-%U주')
                else: label = dt.strftime('%Y-%m')
                
                rows.append({
                    '기간': label, '통화': curr, 
                    '유입(Long)': long_v, '유출(Short)': short_v, 
                    '순포지션(Net)': net_v, '달러환산(USD)': usd_val
                })

            if rows:
                raw_report = pd.DataFrame(rows)
                
                # 피벗 생성 (유입, 유출, 순포지션, 달러환산 모두 포함)
                pivot_df = raw_report.pivot(index='기간', columns='통화', values=['유입(Long)', '유출(Short)', '순포지션(Net)', '달러환산(USD)'])
                
                # 컬럼 구조 변경 (통화, 항목)
                pivot_df.columns = pivot_df.columns.swaplevel(0, 1)
                pivot_df = pivot_df.reindex(columns=unique_currs, level=0)
                pivot_df = pivot_df.reindex(['유입(Long)', '유출(Short)', '순포지션(Net)', '달러환산(USD)'], axis=1, level=1)
                pivot_df = pivot_df.fillna(0)

                # --- 수정 핵심: 합계 행 추가 ---
                sum_row = pivot_df.sum().to_frame().T
                sum_row.index = ['합계(Total)']
                final_display_df = pd.concat([pivot_df, sum_row])

                # 스타일링 및 출력
                st.dataframe(
                    final_display_df.style.format("{:,.2f}")
                    .set_properties(**{'background-color': '#f0f2f6'}, subset=(['합계(Total)'], pd.IndexSlice[:, :])),
                    use_container_width=True
                )
                
                # 하단 전체 달러 합계 요약
                total_usd_sum = sum_row.xs('달러환산(USD)', axis=1, level=1).sum(axis=1).iloc[0]
                st.markdown(f"### 🚩 최종 포지션 합계: **$ {total_usd_sum:,.2f}**")
            else:
                st.info("표시할 데이터가 없습니다.")
        else:
            st.info("네팅 대상 데이터가 없습니다.")

# --- Tab 3: 리스크 시뮬레이션 ---
with tab3:
    if not st.session_state['main_df'].empty:
        net_df = st.session_state['main_df'][st.session_state['main_df']['Netted'] == True].copy()
        if not net_df.empty:
            target_curr = st.selectbox("💱 분석 대상 통화 선택", net_df['Currency'].unique())
            curr_data = net_df[net_df['Currency'] == target_curr]
            total_amt = curr_data['Amount'].sum()
            avg_budget_rate = (curr_data['Amount'] * curr_data['Budget Rate']).sum() / total_amt if total_amt > 0 else real_rates.get(target_curr, 1400.0)
            
            rate_now = real_rates.get(target_curr, 1400.0)
            net_pos = curr_data.apply(lambda x: x['Amount'] if x['Position'] == 'Long' else -x['Amount'], axis=1).sum()

            m1, m2, m3 = st.columns(3)
            m1.metric("순포지션", f"{net_pos:,.2f}")
            m2.metric("가중평균 예산 환율", f"{avg_budget_rate:,.2f}원")
            m3.metric("현재 환율", f"{rate_now:,.2f}원")

            vol = st.sidebar.slider("연 변동성(%)", 1.0, 30.0, 10.0) / 100
            n_sims, t_days = 1000, 30
            dt = 1/252
            sims = np.zeros((t_days, n_sims))
            sims[0] = rate_now
            for t in range(1, t_days):
                sims[t] = sims[t-1] * np.exp((-0.5 * vol**2)*dt + vol * np.sqrt(dt) * np.random.standard_normal(n_sims))
            
            final_pnl = (sims[-1] - avg_budget_rate) * net_pos
            st.plotly_chart(px.histogram(final_pnl, title="예상 손익 분포 (예산 대비)"), use_container_width=True)