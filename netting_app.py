import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

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
    fetch_time = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    for curr, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker).history(period='1d')
            current_rates[curr] = data['Close'].iloc[-1]
        except:
            backup = {"USD": 1400.0, "EUR": 1500.0, "JPY": 9.0, "CNY": 195.0, "GBP": 1750.0}
            current_rates[curr] = backup.get(curr)
    return current_rates, fetch_time

real_rates, last_update = get_realtime_rates()

# 3. 탭 구성
tab1, tab2, tab3 = st.tabs(["📥 데이터 입력 및 편집", "📅 캐시플로우", "🧪 실시간 리스크 시뮬레이션"])

# --- Tab 1: 데이터 입력 및 편집 ---
with tab1:
    st.markdown("### 📘 데이터 입력 및 편집 가이드")
    with st.expander("👉 데이터 작성 및 편집 규칙 (필독)", expanded=True):
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("""
            **📍 주요 항목 설명**
            * **Date**: 발생일 또는 결제 예정일 (YYYY-MM-DD)
            * **Currency**: 통화코드 (USD, EUR, JPY, CNY, GBP)
            * **Position**: **Long**(유입/수출), **Short**(유출/수입)
            * **Amount**: 외화 원금
            * **Budget Rate**: 기준 예산 환율
            """)
        with col_g2:
            st.markdown("""
            **📍 편집 및 저장 주의사항**
            * **Netted**: 이 항목이 **True**인 데이터만 탭 2와 탭 3의 분석 대상에 포함됩니다.
            * **저장 필수**: 수정 후 반드시 하단의 **[💾 변경사항 저장]** 버튼을 클릭하세요.
            """)

    st.divider()
    col_up, col_form = st.columns([1, 1])
    
    with col_up:
        st.subheader("📁 대량 데이터 업로드")
        uploaded_file = st.file_uploader("CSV 또는 Excel 파일 선택", type=['xlsx', 'csv'], key="t1_file_uploader")
        if uploaded_file:
            new_data = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            new_data.columns = [c.strip() for c in new_data.columns]
            mapping = {'날짜': 'Date', '통화': 'Currency', '포지션': 'Position', '금액': 'Amount', '예산 환율': 'Budget Rate', '네팅': 'Netted'}
            new_data = new_data.rename(columns=mapping)
            if st.button("데이터 병합하기"):
                st.session_state['main_df'] = pd.concat([st.session_state['main_df'], new_data], ignore_index=True)
                st.success("데이터가 추가되었습니다.")

    with col_form:
        st.subheader("✍️ 개별 건 직접 입력")
        with st.form("manual_entry", clear_on_submit=True):
            f_date = st.date_input("결제일(예정일)")
            f_curr = st.selectbox("통화 선택", ["USD", "EUR", "JPY", "CNY", "GBP"])
            f_pos = st.selectbox("포지션 구분", ["Long", "Short"])
            f_amt = st.number_input("외화 금액", min_value=0.0)
            f_budget = st.number_input("적용 예산 환율", min_value=0.0, value=1350.0)
            if st.form_submit_button("리스트에 추가"):
                new_row = pd.DataFrame([{'Date': f_date.strftime('%Y-%m-%d'), 'Currency': f_curr, 'Position': f_pos, 'Amount': float(f_amt), 'Budget Rate': float(f_budget), 'Netted': True, 'Remark1': "", 'Remark2': ""}])
                st.session_state['main_df'] = pd.concat([st.session_state['main_df'], new_row], ignore_index=True)
                st.info("데이터가 임시 추가되었습니다.")
                
    if not st.session_state['main_df'].empty:
        st.subheader("📋 전체 데이터 내역 편집")
        edited_df = st.data_editor(st.session_state['main_df'], num_rows="dynamic", use_container_width=True)
        if st.button("💾 변경사항 저장"):
            st.session_state['main_df'] = edited_df.copy()
            st.success("변경사항이 저장되었습니다.")

# --- Tab 2: 캐시플로우 (모든 셀 달러 환산 및 환율 정보 표시) ---
with tab2:
    df_t2 = st.session_state.get('main_df', pd.DataFrame()).copy()
    
    if not df_t2.empty:
        net_df = df_t2[df_t2['Netted'] == True].copy()
        
        if not net_df.empty:
            st.subheader("⚖️ 통화별 캐시플로우 및 달러 환산 분석")
            
            # 상단에 환율 정보 간략히 표시
            st.caption(f"📢 최근 환율 업데이트: {last_update} (Yahoo Finance 기준)")
            
            interval = st.radio("📅 집계 주기", ["일별", "주별", "월별"], horizontal=True, key="t2_final_complete")
            
            net_df['Date'] = pd.to_datetime(net_df['Date'])
            rule = {'일별': 'D', '주별': 'W', '월별': 'ME'}[interval]
            
            usd_krw_rate = float(real_rates.get("USD", 1380.0))
            all_currs = net_df['Currency'].unique().tolist()
            sorted_currs = (["USD"] + sorted([c for c in all_currs if c != "USD"])) if "USD" in all_currs else sorted(all_currs)

            # 1. 데이터 집계
            rows = []
            grouped = net_df.set_index('Date').groupby([pd.Grouper(freq=rule), 'Currency'])
            
            for (dt, curr), group in grouped:
                long_v = float(group[group['Position'].str.strip().str.capitalize() == 'Long']['Amount'].sum())
                short_v = -abs(float(group[group['Position'].str.strip().str.capitalize() == 'Short']['Amount'].sum()))
                net_v = long_v + short_v
                
                curr_rate = float(real_rates.get(curr, 0))
                if curr == "USD":
                    usd_val = net_v
                else:
                    usd_val = (net_v * curr_rate) / usd_krw_rate if usd_krw_rate != 0 else 0.0
                
                label = dt.strftime('%Y-%m-%d') if interval == '일별' else (dt.strftime('%Y-%U주') if interval == '주별' else dt.strftime('%Y-%m'))
                rows.append({'기간': label, '통화': curr, '유입(In)': long_v, '유출(Out)': short_v, '순액(Net)': net_v, 'usd_val': usd_val})

            if rows:
                raw_report = pd.DataFrame(rows)
                pivot_df = raw_report.pivot(index='기간', columns='통화', values=['유입(In)', '유출(Out)', '순액(Net)'])
                pivot_df = pivot_df.swaplevel(0, 1, axis=1)
                pivot_df = pivot_df.reindex(sorted_currs, axis=1, level=0).reindex(['유입(In)', '유출(Out)', '순액(Net)'], axis=1, level=1)
                
                total_usd_col = ('Total', 'USD Equivalent')
                pivot_df[total_usd_col] = raw_report.groupby('기간')['usd_val'].sum()
                pivot_df = pivot_df.fillna(0.0)

                # 2. 합계 행 구성
                sum_values = pivot_df.sum()
                sum_df = pd.DataFrame(sum_values).T
                sum_df.index = ['합계(Grand Total)']

                # 3. [요청 반영] 모든 셀을 달러 가치로 환산한 최종 행 생성
                final_row = pd.Series(0.0, index=pivot_df.columns, dtype=float)
                
                for curr in sorted_currs:
                    curr_rate = float(real_rates.get(curr, 0))
                    # 해당 통화의 합계 원금들 가져오기
                    orig_in = sum_values[(curr, '유입(In)')]
                    orig_out = sum_values[(curr, '유출(Out)')]
                    orig_net = sum_values[(curr, '순액(Net)')]
                    
                    if curr == "USD":
                        final_row[(curr, '유입(In)')] = orig_in
                        final_row[(curr, '유출(Out)')] = orig_out
                        final_row[(curr, '순액(Net)')] = orig_net
                    else:
                        # 달러 환산 로직 적용
                        final_row[(curr, '유입(In)')] = (orig_in * curr_rate) / usd_krw_rate if usd_krw_rate != 0 else 0
                        final_row[(curr, '유출(Out)')] = (orig_out * curr_rate) / usd_krw_rate if usd_krw_rate != 0 else 0
                        final_row[(curr, '순액(Net)')] = (orig_net * curr_rate) / usd_krw_rate if usd_krw_rate != 0 else 0
                
                # 전체 합계액 열도 채우기
                final_row[total_usd_col] = sum_values[total_usd_col]
                
                final_row_df = pd.DataFrame(final_row).T
                final_row_df.index = ['최종 달러 환산 합계 (USD)']
                
                # 데이터 통합
                final_display_df = pd.concat([pivot_df, sum_df, final_row_df])

                # 4. 스타일링
                def style_v4(styler):
                    styler.format("{:,.2f}")
                    # USD Equivalent 열 전체 강조
                    styler.set_properties(**{'color': '#1E90FF', 'font-weight': 'bold'}, subset=[total_usd_col])
                    # Grand Total 행 배경색
                    styler.set_properties(**{'background-color': '#f0f2f6', 'font-weight': 'bold'}, 
                                         subset=(['합계(Grand Total)'], pd.IndexSlice[:, :]))
                    # [요청 반영] 최종 달러 환산 행 전체를 파란색 테마로 강조
                    styler.set_properties(**{'background-color': '#E1F5FE', 'color': '#1E90FF', 'font-weight': 'bold'}, 
                                         subset=(['최종 달러 환산 합계 (USD)'], pd.IndexSlice[:, :]))
                    return styler

                st.dataframe(style_v4(final_display_df.style), use_container_width=True)
                
                # 5. [요청 반영] 환율 정보 테이블 표시
                st.divider()
                st.markdown(f"### 💱 실시간 적용 환율 정보 (업데이트: {last_update})")
                rate_data = []
                for c, r in real_rates.items():
                    rate_data.append({"통화": c, "현재 환율(KRW)": r, "1 USD 대비 가치": round(r/usd_krw_rate, 4) if c != "USD" else 1.0})
                st.table(pd.DataFrame(rate_data))

        else:
            st.info("Netted 항목을 체크하고 저장해주세요.")
    else:
        st.warning("데이터가 없습니다.")
        
# --- Tab 3: 실시간 리스크 시뮬레이션 ---
with tab3:
    def run_tab3_complete(df_netting):
        st.header("🧪 외환 리스크 시뮬레이션 및 현가 분석")
        with st.expander("🌐 시장 데이터 및 시뮬레이션 설정", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                spot_usd_krw = st.number_input("USD/KRW 현물환율", value=real_rates.get("USD", 1380.0))
                volatility = st.slider("연 변동성 (%)", 5.0, 30.0, 12.0) / 100
            with c2:
                rate_usd = st.number_input("USD 이자율", value=0.0525, format="%.4f")
                rate_krw = st.number_input("KRW 이자율", value=0.0350, format="%.4f")
            with c3:
                iter_count = st.select_slider("시뮬레이션 횟수", options=[100, 500, 1000], value=500)
                target_rate = st.number_input("목표 환율", value=1320.0)

        market_rates = {'USD': rate_usd, 'KRW': rate_krw, 'JPY': 0.0010, 'EUR': 0.0400}
        current_spot = {'USD/KRW': spot_usd_krw, 'EUR/USD': 1.08, 'USD/JPY': 155.0}
        valuation_date = datetime.now()

        def get_forward_rate(spot, r_base, r_quote, days):
            t = max(days, 0) / 365
            return spot * np.exp((r_quote - r_base) * t)

        def get_present_value(amount, rate, days):
            t = max(days, 0) / 365
            return amount * np.exp(-rate * t)

        portfolio_results = []
        for _, row in df_netting.iterrows():
            target_date = pd.to_datetime(row['Date'])
            days = (target_date - valuation_date).days
            curr = row['Currency']
            amt = row['Amount'] if str(row['Position']).capitalize() == 'Long' else -abs(row['Amount'])

            if curr == 'USD':
                usd_fwd = amt
            elif curr == 'JPY':
                fwd = get_forward_rate(1/current_spot['USD/JPY'], market_rates['JPY'], market_rates['USD'], days)
                usd_fwd = amt * fwd
            elif curr == 'EUR':
                fwd = get_forward_rate(current_spot['EUR/USD'], market_rates['EUR'], market_rates['USD'], days)
                usd_fwd = amt * fwd
            else:
                usd_fwd = (amt * real_rates.get(curr, 0)) / spot_usd_krw

            pv_usd = get_present_value(usd_fwd, market_rates['USD'], days)
            pv_krw = pv_usd * spot_usd_krw

            portfolio_results.append({'만기일': target_date.date(), '통화': curr, '원금': amt, 'USD 현가(PV)': pv_usd, 'KRW 현가(PV)': pv_krw, '잔존일수': days})

        df_p = pd.DataFrame(portfolio_results)
        total_usd, total_krw = df_p['USD 현가(PV)'].sum(), df_p['KRW 현가(PV)'].sum()
        bep = total_krw / total_usd if total_usd != 0 else 0

        # Monte Carlo
        steps = 90
        paths = np.zeros((steps, iter_count))
        paths[0] = spot_usd_krw
        dt = 1/365
        for t in range(1, steps):
            rand = np.random.standard_normal(iter_count)
            drift = (rate_krw - rate_usd - 0.5 * volatility**2) * dt
            diffusion = volatility * np.sqrt(dt) * rand
            paths[t] = paths[t-1] * np.exp(drift + diffusion)

        m1, m2, m3 = st.columns(3)
        m1.metric("Exposure (PV USD)", f"${total_usd:,.2f}")
        m2.metric("Portfolio BEP", f"₩{bep:,.2f}")
        m3.metric("VaR (95%)", f"₩{abs(bep - np.percentile(paths[-1], 5)) * abs(total_usd):,.0f}")

        fig = go.Figure()
        x_ax = [valuation_date + timedelta(days=i) for i in range(steps)]
        fig.add_trace(go.Scatter(x=x_ax, y=np.percentile(paths, 95, axis=1), mode='lines', line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=x_ax, y=np.percentile(paths, 5, axis=1), mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(255, 0, 0, 0.1)', name='Risk Zone'))
        fig.add_trace(go.Scatter(x=x_ax, y=np.median(paths, axis=1), mode='lines', line=dict(color='blue'), name='Median'))
        fig.add_hline(y=bep, line_dash="dash", annotation_text="BEP")
        st.plotly_chart(fig, use_container_width=True)

    net_data = st.session_state['main_df'][st.session_state['main_df']['Netted'] == True]
    if not net_data.empty:
        run_tab3_complete(net_data)
    else:
        st.info("분석할 데이터를 체크해주세요.")