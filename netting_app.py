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

# --- Tab 2: 상세 포지션 내역 및 네팅 현황 ---
with tab2:
    df_t2 = st.session_state['main_df'].copy()

    if not df_t2.empty:
        st.subheader("⚖️ 상세 포지션 및 네팅 현황")
        
        interval = st.radio("📊 집계 구간 선택", ["일별", "주별", "월별"], horizontal=True, key="t2_interval_final_v7")
        
        df_t2['Date'] = pd.to_datetime(df_t2['Date'])
        rule = {'일별': 'D', '주별': 'W', '월별': 'ME'}[interval]
        net_df = df_t2[df_t2['Netted'] == True].copy()
        
        if not net_df.empty:
            # 1. 상단 통화별 요약 (순포지션 + 달러 환산액 추가)
            unique_currs = sorted(net_df['Currency'].unique(), key=lambda x: (x != 'USD', x))
            usd_krw = real_rates.get("USD", 1475.0)
            
            st.markdown("#### 📑 통화별 요약 지표")
            curr_summary_cols = st.columns(len(unique_currs))
            for i, curr in enumerate(unique_currs):
                with curr_summary_cols[i]:
                    c_data = net_df[net_df['Currency'] == curr]
                    l_sum = c_data[c_data['Position'].str.capitalize() == 'Long']['Amount'].sum()
                    s_sum = c_data[c_data['Position'].str.capitalize() == 'Short']['Amount'].sum()
                    n_sum = l_sum - s_sum
                    
                    # 통화별 달러 환산액 계산
                    c_rate = real_rates.get(curr, 0)
                    c_usd_val = (n_sum * c_rate) / usd_krw if curr != "USD" else n_sum
                    
                    st.metric(f"{curr} 순포지션", f"{n_sum:,.2f}")
                    st.caption(f"💵 달러환산: $ {c_usd_val:,.2f}") # 아랫줄 추가 표시

            st.divider()

            # 2. 데이터 집계 로직
            grouped = net_df.set_index('Date').groupby([pd.Grouper(freq=rule), 'Currency'])
            rows = []
            for (dt, curr), group in grouped:
                long_v = group[group['Position'].str.strip().str.capitalize() == 'Long']['Amount'].sum()
                short_v = group[group['Position'].str.strip().str.capitalize() == 'Short']['Amount'].sum()
                net_v = long_v - short_v
                
                curr_rate = real_rates.get(curr, 0)
                usd_val = (net_v * curr_rate) / usd_krw if curr != "USD" else net_v
                
                label = dt.strftime('%Y-%m-%d') if interval == '일별' else (dt.strftime('%Y-%U주') if interval == '주별' else dt.strftime('%Y-%m'))
                rows.append({'기간': label, '통화': curr, '유입(Long)': long_v, '유출(Short)': short_v, '순포지션(Net)': net_v, '행_달러환산': usd_val})

            if rows:
                raw_report = pd.DataFrame(rows)
                pivot_df = raw_report.pivot(index='기간', columns='통화', values=['유입(Long)', '유출(Short)', '순포지션(Net)'])
                pivot_df.columns = pivot_df.columns.swaplevel(0, 1)
                pivot_df = pivot_df.reindex(columns=unique_currs, level=0)
                pivot_df = pivot_df.reindex(['유입(Long)', '유출(Short)', '순포지션(Net)'], axis=1, level=1)
                
                # 행 끝 달러환산 합계 컬럼
                pivot_df[('전체', '달러환산 합계(USD)')] = raw_report.groupby('기간')['행_달러환산'].sum()
                pivot_df = pivot_df.fillna(0)

                # 3. 하단 행 추가 (합계 행 + 달러 환산액 행)
                sum_row = pivot_df.sum().to_frame().T
                sum_row.index = ['합계(Total)']
                
                # 달러 환산액 행 생성
                usd_conv_row = sum_row.copy()
                usd_conv_row.index = ['달러 환산액(USD)']
                for curr in unique_currs:
                    rate = real_rates.get(curr, 0)
                    # 각 통화별 순포지션 합계를 달러로 환산
                    net_total = sum_row.get((curr, '순포지션(Net)'), [0])[0]
                    usd_conv_row.at['달러 환산액(USD)', (curr, '순포지션(Net)')] = (net_total * rate / usd_krw) if curr != "USD" else net_total
                    # 유입/유출 칸은 비움 (선택 사항)
                    usd_conv_row.at['달러 환산액(USD)', (curr, '유입(Long)')] = np.nan
                    usd_conv_row.at['달러 환산액(USD)', (curr, '유출(Short)')] = np.nan
                
                final_df = pd.concat([pivot_df, sum_row, usd_conv_row])

                # 4. 스타일링 및 출력
                st.markdown(f"#### 📅 {interval} 상세 내역")
                
                def style_final(df):
                    return df.style.format("{:,.2f}", na_rep="-") \
                        .set_properties(**{'background-color': '#f0f2f6', 'font-weight': 'bold'}, subset=(['합계(Total)'], pd.IndexSlice[:, :])) \
                        .set_properties(**{'color': 'blue', 'font-weight': 'bold'}, subset=(['달러 환산액(USD)'], pd.IndexSlice[:, :]))

                st.dataframe(style_final(final_df), use_container_width=True)
                
                # 최종 강조 텍스트
                total_val = sum_row[('전체', '달러환산 합계(USD)')].iloc[0]
                st.markdown(f"<p style='text-align:right; color:blue; font-size:24px; font-weight:bold;'>최종 합계: $ {total_val:,.2f}</p>", unsafe_allow_html=True)
            else:
                st.info("데이터가 없습니다.")

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