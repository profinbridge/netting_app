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

# 실시간 환율 엔진 (시간 데이터 추가)
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

# 3. 탭 구성
tab1, tab2, tab3 = st.tabs(["📥 데이터 관리 및 입력", "⚖️ 네팅 분석 요약", "🧪 실시간 리스크 시뮬레이션"])

# --- Tab 1: 데이터 관리 및 입력 ---
with tab1:
    st.markdown("### 📘 CSV 파일 작성 및 업로드 가이드")
    with st.expander("👉 CSV 헤더별 상세 작성 규칙 (필독)", expanded=True):
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("""
            **📍 각 항목(Header) 설명**
            * **Date**: 외화 발생일 또는 결제 예정일 (YYYY-MM-DD)
            * **Currency**: 통화코드 (USD, EUR, JPY, CNY, GBP 중 선택)
            * **Position**: 자금 방향 (**Long**: 유입, **Short**: 유출)
            * **Amount**: 외화 금액 (숫자만 입력)
            * **Budget Rate**: 예산 환율 (직접 입력)
            * **Netted**: 네팅 포함 여부 (**True**: 포함)
            """)
        with col_g2:
            st.markdown("""
            **📍 비고란 및 주의사항**
            * **파일 형식**: 반드시 **CSV (UTF-8)** 형식 저장
            * **확정 저장**: 하단의 [변경사항 저장]을 눌러야 분석에 반영됨
            """)

    st.divider()
    col_up, col_form = st.columns([1, 1])
    
    with col_up:
        st.subheader("📁 파일 업로드")
        uploaded_file = st.file_uploader("CSV/Excel 선택", type=['xlsx', 'csv'], key="t1_file_uploader")
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
                st.success("데이터가 병합되었습니다.")

    with col_form:
        st.subheader("✍️ 직접 입력")
        with st.form("manual_entry", clear_on_submit=True):
            f_date = st.date_input("날짜")
            f_curr = st.selectbox("통화", ["USD", "EUR", "JPY", "CNY", "GBP"])
            f_pos = st.selectbox("포지션", ["Long", "Short"])
            f_amt = st.number_input("금액", min_value=0.0)
            f_budget = st.number_input("예산 환율", min_value=0.0, value=0.0)
            if st.form_submit_button("추가"):
                new_row = pd.DataFrame([{'Date': f_date.strftime('%Y-%m-%d'), 'Currency': f_curr, 'Position': f_pos, 'Amount': float(f_amt), 'Budget Rate': float(f_budget), 'Netted': True, 'Remark1': "", 'Remark2': ""}])
                st.session_state['main_df'] = pd.concat([st.session_state['main_df'], new_row], ignore_index=True)
                st.info("추가됨. 아래 [저장]을 누르세요.")
                
    if not st.session_state['main_df'].empty:
        st.subheader("📋 전체 데이터 편집")
        edited_df = st.data_editor(st.session_state['main_df'], num_rows="dynamic", use_container_width=True, key="main_data_editor")
        if st.button("💾 변경사항 저장"):
            st.session_state['main_df'] = edited_df.copy()
            st.success("저장 완료!")

# --- Tab 2: 상세 포지션 내역 및 네팅 현황 ---
with tab2:
    df_t2 = st.session_state.get('main_df', pd.DataFrame()).copy()
    if not df_t2.empty:
        st.subheader("⚖️ 상세 포지션 및 네팅 현황")
        interval = st.radio("📊 집계 구간 선택", ["일별", "주별", "월별"], horizontal=True, key="t2_interval_final")
        df_t2['Date'] = pd.to_datetime(df_t2['Date'])
        rule = {'일별': 'D', '주별': 'W', '월별': 'ME'}[interval]
        net_df = df_t2[df_t2['Netted'] == True].copy()
        
        if not net_df.empty:
            all_currs = net_df['Currency'].unique().tolist()
            sorted_currs = (["USD"] + sorted([c for c in all_currs if c != "USD"])) if "USD" in all_currs else sorted(all_currs)
            usd_krw = real_rates.get("USD", 1475.0)

            # 데이터 집계
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

                # 하단 합계 행
                sum_values = pivot_df.sum()
                sum_df = pd.DataFrame(sum_values).T
                sum_df.index = ['합계(Total)']
                usd_conv_data = {col: (sum_values[col] * real_rates.get(col[0], 0) / usd_krw if col[0] != "USD" and col[0] != "전체" else sum_values[col]) for col in pivot_df.columns}
                usd_conv_df = pd.DataFrame([usd_conv_data], index=['달러 환산액(USD)'])
                final_df = pd.concat([pivot_df, sum_df, usd_conv_df])

                # 스타일 및 폭 설정
                styled_df = final_df.style.format("{:,.2f}", na_rep="-") \
                    .set_properties(**{'background-color': '#f0f2f6', 'font-weight': 'bold'}, subset=(['합계(Total)'], pd.IndexSlice[:, :])) \
                    .set_properties(**{'color': 'blue', 'font-weight': 'bold'}, subset=(['달러 환산액(USD)'], pd.IndexSlice[:, :]))

                column_config = {col: st.column_config.Column(width="large") for col in final_df.columns}
                st.markdown(f"#### 📅 {interval} 상세 내역")
                st.write(styled_df) # 계층 구조 유지를 위해 st.write(styled_df) 사용
                
                total_val = sum_values[('전체', '달러환산 합계(USD)')]
                st.markdown(f"<p style='text-align:right; color:blue; font-size:24px; font-weight:bold;'>최종 합계: $ {total_val:,.2f}</p>", unsafe_allow_html=True)
                
                # [추가] 탭 2 하단 환율 정보
                with st.expander("ℹ️ 달러 환산 적용 환율 및 채집 시간 정보", expanded=False):
                    st.caption(f"데이터 채집 시각: {last_update}")
                    rate_cols = st.columns(len(real_rates))
                    for i, (curr, val) in enumerate(real_rates.items()):
                        rate_cols[i].caption(f"**{curr}**: {val:,.2f}")
    else:
        st.warning("데이터를 먼저 저장해 주세요.")

# --- Tab 3: 리스크 시뮬레이션 ---
with tab3:
    if not st.session_state['main_df'].empty:
        # 상단 실시간 환율 정보 (업데이트 시간 포함)
        st.markdown(f"##### 🕒 실시간 적용 환율 정보 (업데이트: {last_update})")
        info_cols = st.columns(len(real_rates))
        for i, (curr, val) in enumerate(real_rates.items()):
            info_cols[i].metric(f"{curr}/KRW", f"{val:,.2f}")
        st.divider()

        net_df = st.session_state['main_df'][st.session_state['main_df']['Netted'] == True].copy()
        
        if not net_df.empty:
            # 1. 탭 내부 분할 (왼쪽 1: 오른쪽 3 비율)
            col_setting, col_graph = st.columns([1, 3])
            
            with col_setting:
                st.subheader("⚙️ 리스크 설정")
                
                # 분석 대상 통화 선택
                target_curr = st.selectbox("💱 분석 대상 통화", net_df['Currency'].unique())
                
                # [요청 항목 1] 변동성
                vol = st.slider("📊 연 변동성(%)", 1.0, 30.0, 10.0, help="시뮬레이션에 적용할 연간 환율 변동성입니다.") / 100
                
                # [요청 항목 2] 목표 환율
                target_rate = st.number_input("🎯 목표 환율 (Target)", min_value=0.0, value=float(real_rates.get(target_curr, 1400.0)), help="달성하고자 하는 목표 환율을 입력하세요.")
                
                # [요청 항목 3] 손실 한도
                stop_loss = st.number_input("🚫 손실 한도 (Stop-Loss)", min_value=0.0, value=5000000.0, step=1000000.0, help="허용 가능한 최대 손실액(KRW)을 입력하세요.")
                
                st.divider()
                st.caption(f"현재 {target_curr} 포지션을 기준으로 1,000회 시뮬레이션을 수행합니다.")

            with col_graph:
                # 데이터 준비 및 계산
                curr_data = net_df[net_df['Currency'] == target_curr]
                total_amt = curr_data['Amount'].sum()
                avg_budget_rate = (curr_data['Amount'] * curr_data['Budget Rate']).sum() / total_amt if total_amt > 0 else real_rates.get(target_curr, 1400.0)
                rate_now = real_rates.get(target_curr, 1400.0)
                net_pos = curr_data.apply(lambda x: x['Amount'] if x['Position'] == 'Long' else -x['Amount'], axis=1).sum()

                # 주요 지표 요약 (Metric)
                m1, m2, m3 = st.columns(3)
                m1.metric("순포지션", f"{net_pos:,.2f} {target_curr}")
                m2.metric("평균 예산 환율", f"{avg_budget_rate:,.2f}원")
                m3.metric("현재 환율", f"{rate_now:,.2f}원")

                # 몬테카를로 시뮬레이션 엔진
                n_sims, t_days = 1000, 30
                dt = 1/252
                sims = np.zeros((t_days, n_sims))
                sims[0] = rate_now
                for t in range(1, t_days):
                    sims[t] = sims[t-1] * np.exp((-0.5 * vol**2)*dt + vol * np.sqrt(dt) * np.random.standard_normal(n_sims))
                
                # 손익 계산 (예산 환율 대비)
                final_pnl = (sims[-1] - avg_budget_rate) * net_pos
                
                # 시각화 (히스토그램)
                fig = px.histogram(final_pnl, 
                                   title=f"30일 후 {target_curr} 예상 손익 분포 (예산 환율 대비)",
                                   labels={'value': '예상 손익 (KRW)', 'count': '빈도'},
                                   color_discrete_sequence=['#636EFA'],
                                   opacity=0.8)
                
                # 손실 한도(Stop-Loss) 기준선 표시
                fig.add_vline(x=-stop_loss, line_dash="dash", line_color="red", annotation_text="손실 한도")
                # 0원 기준선
                fig.add_vline(x=0, line_dash="solid", line_color="black")
                
                st.plotly_chart(fig, use_container_width=True)

                # 리스크 요약 정보
                loss_prob = (final_pnl < -stop_loss).mean() * 100
                st.warning(f"⚠️ **리스크 알림**: 설정하신 손실 한도({stop_loss:,.0f}원)를 초과할 확률은 약 **{loss_prob:.1f}%**입니다.")