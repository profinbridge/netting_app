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
    fetch_time = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    for curr, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker).history(period='1d')
            current_rates[curr] = data['Close'].iloc[-1]
        except:
            backup = {"USD": 1475.0, "EUR": 1580.0, "JPY": 9.5, "CNY": 203.0, "GBP": 1850.0}
            current_rates[curr] = backup.get(curr)
    return current_rates, fetch_time

real_rates, last_update = get_realtime_rates()

# 3. 탭 구성 수정 (사용자 요청 반영)
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
            * **Budget Rate**: 기준 예산 환율 (직접 입력)
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
            for col in ['Date', 'Currency', 'Position', 'Amount', 'Budget Rate', 'Netted', 'Remark1', 'Remark2']:
                if col not in new_data.columns:
                    new_data[col] = 0.0 if col in ['Amount', 'Budget Rate'] else (True if col == 'Netted' else "")
            if st.button("데이터 병합하기"):
                st.session_state['main_df'] = pd.concat([st.session_state['main_df'], new_data], ignore_index=True)
                st.success("데이터가 성공적으로 추가되었습니다.")

    with col_form:
        st.subheader("✍️ 개별 건 직접 입력")
        with st.form("manual_entry", clear_on_submit=True):
            f_date = st.date_input("결제일(예정일)")
            f_curr = st.selectbox("통화 선택", ["USD", "EUR", "JPY", "CNY", "GBP"])
            f_pos = st.selectbox("포지션 구분", ["Long", "Short"])
            f_amt = st.number_input("외화 금액", min_value=0.0)
            f_budget = st.number_input("적용 예산 환율", min_value=0.0, value=0.0)
            if st.form_submit_button("리스트에 추가"):
                new_row = pd.DataFrame([{'Date': f_date.strftime('%Y-%m-%d'), 'Currency': f_curr, 'Position': f_pos, 'Amount': float(f_amt), 'Budget Rate': float(f_budget), 'Netted': True, 'Remark1': "", 'Remark2': ""}])
                st.session_state['main_df'] = pd.concat([st.session_state['main_df'], new_row], ignore_index=True)
                st.info("데이터가 임시 추가되었습니다. 아래 표에서 확인 후 저장하세요.")
                
    if not st.session_state['main_df'].empty:
        st.subheader("📋 전체 데이터 내역 편집")
        edited_df = st.data_editor(st.session_state['main_df'], num_rows="dynamic", use_container_width=True, key="main_data_editor")
        if st.button("💾 변경사항 저장"):
            st.session_state['main_df'] = edited_df.copy()
            st.success("모든 변경사항이 세션에 저장되었습니다.")

# --- Tab 2: 캐시플로우 ---
with tab2:
    df_t2 = st.session_state.get('main_df', pd.DataFrame()).copy()
    if not df_t2.empty:
        st.subheader("⚖️ 통화별 캐시플로우 및 네팅 현황")
        interval = st.radio("📅 집계 주기", ["일별", "주별", "월별"], horizontal=True, key="t2_interval_final")
        df_t2['Date'] = pd.to_datetime(df_t2['Date'])
        rule = {'일별': 'D', '주별': 'W', '월별': 'ME'}[interval]
        
        # 'Netted'가 체크된 데이터만 분석
        net_df = df_t2[df_t2['Netted'] == True].copy()
        
        if not net_df.empty:
            all_currs = net_df['Currency'].unique().tolist()
            sorted_currs = (["USD"] + sorted([c for c in all_currs if c != "USD"])) if "USD" in all_currs else sorted(all_currs)
            usd_krw = real_rates.get("USD", 1475.0)

            grouped = net_df.set_index('Date').groupby([pd.Grouper(freq=rule), 'Currency'])
            rows = []
            for (dt, curr), group in grouped:
                long_v = group[group['Position'].str.strip().str.capitalize() == 'Long']['Amount'].sum()
                short_raw = group[group['Position'].str.strip().str.capitalize() == 'Short']['Amount'].sum()
                short_v = -abs(short_raw) if short_raw != 0 else 0
                net_v = long_v + short_v
                curr_rate = real_rates.get(curr, 0)
                usd_val = (net_v * curr_rate) / usd_krw if curr != "USD" else net_v
                label = dt.strftime('%Y-%m-%d') if interval == '일별' else (dt.strftime('%Y-%U주') if interval == '주별' else dt.strftime('%Y-%m'))
                rows.append({'기간': label, '통화': curr, '유입(Long)': long_v, '유출(Short)': short_v, '순포지션(Net)': net_v, '행_달러환산': usd_val})

            if rows:
                raw_report = pd.DataFrame(rows)
                pivot_df = raw_report.pivot(index='기간', columns='통화', values=['유입(Long)', '유출(Short)', '순포지션(Net)'])
                pivot_df = pivot_df.swaplevel(0, 1, axis=1)
                pivot_df = pivot_df.reindex(sorted_currs, axis=1, level=0).reindex(['유입(Long)', '유출(Short)', '순포지션(Net)'], axis=1, level=1)
                pivot_df[('전체', '달러환산 합계(USD)')] = raw_report.groupby('기간')['행_달러환산'].sum()
                pivot_df = pivot_df.fillna(0)

                sum_values = pivot_df.sum()
                sum_df = pd.DataFrame(sum_values).T
                sum_df.index = ['합계(Total)']
                usd_conv_data = {col: (sum_values[col] * real_rates.get(col[0], 0) / usd_krw if col[0] != "USD" and col[0] != "전체" else sum_values[col]) for col in pivot_df.columns}
                usd_conv_df = pd.DataFrame([usd_conv_data], index=['달러 환산액(USD)'])
                final_df = pd.concat([pivot_df, sum_df, usd_conv_df])

                styled_df = final_df.style.format("{:,.2f}", na_rep="-") \
                    .set_properties(**{'background-color': '#f0f2f6', 'font-weight': 'bold'}, subset=(['합계(Total)'], pd.IndexSlice[:, :])) \
                    .set_properties(**{'color': 'blue', 'font-weight': 'bold'}, subset=(['달러 환산액(USD)'], pd.IndexSlice[:, :]))

                st.markdown(f"#### 📊 {interval} 캐시플로우 요약 보고서")
                st.write(styled_df)
                
                total_val = sum_values[('전체', '달러환산 합계(USD)')]
                st.markdown(f"<p style='text-align:right; color:blue; font-size:24px; font-weight:bold;'>전체 순포지션 합계: $ {total_val:,.2f}</p>", unsafe_allow_html=True)
                
                with st.expander("ℹ️ 외화 환산 기준 정보", expanded=False):
                    st.caption(f"최근 환율 업데이트: {last_update}")
                    rate_cols = st.columns(len(real_rates))
                    for i, (curr, val) in enumerate(real_rates.items()):
                        rate_cols[i].caption(f"**{curr}**: {val:,.2f}")
        else:
            st.info("네팅(Netted) 대상으로 선택된 데이터가 없습니다. 탭 1에서 'Netted' 열을 체크해 주세요.")
    else:
        st.warning("분석할 데이터가 없습니다. 탭 1에서 데이터를 입력하거나 업로드해 주세요.")

# --- Tab 3: 실시간 리스크 시뮬레이션 ---
with tab3:
    if not st.session_state['main_df'].empty:
        st.markdown(f"##### 🕒 실시간 시장 환율 (업데이트: {last_update})")
        info_cols = st.columns(len(real_rates))
        for i, (curr, val) in enumerate(real_rates.items()):
            info_cols[i].metric(f"{curr}/KRW", f"{val:,.2f}")
        st.divider()

        net_df = st.session_state['main_df'][st.session_state['main_df']['Netted'] == True].copy()
        
        if not net_df.empty:
            col_setting, col_graph = st.columns([1, 3])
            
            with col_setting:
                st.subheader("⚙️ 시뮬레이션 설정")
                target_curr = st.selectbox("🎯 분석 통화 선택", net_df['Currency'].unique())
                vol = st.slider("📊 예상 변동성(%)", 1.0, 30.0, 10.0, help="과거 데이터 또는 향후 전망에 따른 연 변동성을 설정하세요.") / 100
                target_rate = st.number_input("🎯 목표 환율", min_value=0.0, value=float(real_rates.get(target_curr, 1400.0)))
                stop_loss = st.number_input("🚫 허용 손실 한도 (KRW)", min_value=0.0, value=5000000.0, step=1000000.0)
                
                st.divider()
                st.caption(f"{target_curr}의 현재 포지션을 기준으로 1,000회의 몬테카를로 시뮬레이션을 수행하여 예상 손익 분포를 계산합니다.")

            with col_graph:
                # 1. 데이터 필터링 및 숫자 변환
                curr_data = net_df[net_df['Currency'] == target_curr].copy()
                curr_data['Amount'] = pd.to_numeric(curr_data['Amount'], errors='coerce').fillna(0)
                curr_data['Budget Rate'] = pd.to_numeric(curr_data['Budget Rate'], errors='coerce').fillna(0)

                # 2. 사용자 정의 로직: [원화 순액 / 외화 순액] 기반 실질 네팅 환율 산출
                long_mask = curr_data['Position'].str.strip().str.capitalize() == 'Long'
                long_amt = curr_data.loc[long_mask, 'Amount'].sum()
                long_krw = (curr_data.loc[long_mask, 'Amount'] * curr_data.loc[long_mask, 'Budget Rate']).sum()

                short_mask = curr_data['Position'].str.strip().str.capitalize() == 'Short'
                short_amt = curr_data.loc[short_mask, 'Amount'].sum()
                short_krw = (curr_data.loc[short_mask, 'Amount'] * curr_data.loc[short_mask, 'Budget Rate']).sum()

                net_pos = long_amt - short_amt
                net_krw_val = long_krw - short_krw

                if net_pos != 0:
                    avg_budget_rate = abs(net_krw_val / net_pos)
                else:
                    avg_budget_rate = real_rates.get(target_curr, 1400.0)

                rate_now = real_rates.get(target_curr, 1400.0)

                # 3. 주요 지표 출력
                m1, m2, m3 = st.columns(3)
                m1.metric("순포지션 (Net)", f"{net_pos:,.2f} {target_curr}")
                m2.metric("평균 예산 환율(BEP)", f"{avg_budget_rate:,.2f}원", help="실질 원화 순액을 외화 순액으로 나눈 손익분기 환율입니다.")
                m3.metric("현재 시장 환율", f"{rate_now:,.2f}원")

                # 4. 몬테카를로 엔진
                n_sims, t_days = 1000, 30
                dt = 1/252
                sims = np.zeros((t_days, n_sims))
                sims[0] = rate_now
                for t in range(1, t_days):
                    sims[t] = sims[t-1] * np.exp((-0.5 * vol**2)*dt + vol * np.sqrt(dt) * np.random.standard_normal(n_sims))
                
                final_pnl = (sims[-1] - avg_budget_rate) * net_pos
                
                fig = px.histogram(final_pnl, 
                                   title=f"{target_curr} 포지션 예상 손익 분포 (30일 후 전망)",
                                   labels={'value': '예상 손익 (KRW)', 'count': '빈도'},
                                   color_discrete_sequence=['#636EFA'],
                                   opacity=0.8)
                fig.add_vline(x=0, line_dash="solid", line_color="black")
                fig.add_vline(x=-stop_loss, line_dash="dash", line_color="red", annotation_text="손실 한도선")
                st.plotly_chart(fig, use_container_width=True)

                # 리스크 요약
                loss_prob = (final_pnl < -stop_loss).mean() * 100
                st.warning(f"⚠️ **리스크 분석**: 설정하신 손실 한도({stop_loss:,.0f}원)를 초과할 확률은 약 **{loss_prob:.1f}%**입니다.")
        else:
            st.info("시뮬레이션을 수행할 네팅 데이터가 없습니다.")