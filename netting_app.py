import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date

# --- [기본 설정 및 세션 초기화] ---
if 'main_df' not in st.session_state:
    st.session_state['main_df'] = pd.DataFrame([{
        'Date': date(2026, 6, 1), 'Currency': 'USD', 'Position': 'Long', 
        'Amount': 1000000.0, 'Netted': True, 'Remark1': '샘플 데이터', 'Remark2': ''
    }])

tab1, tab2, tab3 = st.tabs(["📥 데이터 관리 및 입력", "⚖️ 네팅 분석 요약", "🧪 실시간 리스크 시뮬레이션"])

# ---------------------------------------------------------
# [Tab 1: 데이터 관리 및 입력] - 사용자님의 원본 가이드 및 로직 완벽 복구
# ---------------------------------------------------------
with tab1:
    st.markdown("### 📘 CSV 파일 작성 및 업로드 가이드")
    # [사용자 요청 사항] 이 가이드 섹션의 내용을 절대적으로 유지합니다.
    with st.expander("👉 CSV 헤더별 상세 작성 규칙 (필독)", expanded=True):
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("""
            **📍 각 항목(Header) 설명**
            * **Date**: 외화 발생일 또는 결제 예정일 (YYYY-MM-DD)
            * **Currency**: 통화코드 (USD, EUR, JPY, CNY, GBP 중 선택)
            * **Position**: 자금 방향 (**Long**: 외화 유입/수출, **Short**: 외화 유출/수입)
            * **Amount**: 외화 금액 (쉼표 없이 숫자만 입력)
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

    # --- [파일 업로드 섹션] ---
    st.markdown("#### 📤 CSV 파일 업로드")
    uploaded_file = st.file_uploader("작성한 CSV 파일을 선택하세요", type=["csv"], key="main_uploader")
    if uploaded_file:
        try:
            up_df = pd.read_csv(uploaded_file)
            if st.button("📁 업로드된 데이터로 교체하기", type="secondary"):
                up_df['Date'] = pd.to_datetime(up_df['Date']).dt.date
                st.session_state['main_df'] = up_df
                st.success("데이터가 성공적으로 로드되었습니다.")
                st.rerun()
        except Exception as e:
            st.error(f"파일 읽기 오류: {e}")

    st.divider()
    
    # --- [데이터 에디터 및 저장 로직] ---
    st.markdown("#### 📝 데이터 직접 편집")
    
    # 데이터 비교 및 정규화 (Remark 컬럼 처리 포함)
    compare_df = st.session_state['main_df'].copy()
    compare_df['Date'] = pd.to_datetime(compare_df['Date']).dt.date
    for c in ['Remark1', 'Remark2']:
        if c in compare_df.columns: compare_df[c] = compare_df[c].astype(str).replace(['nan', 'None', ''], '')

    display_df = compare_df.copy()
    display_df.insert(0, 'No', range(1, len(display_df) + 1))

    edited_df = st.data_editor(
        display_df, num_rows="dynamic", use_container_width=True,
        column_config={
            "No": st.column_config.NumberColumn("No.", disabled=True, width=40),
            "Date": st.column_config.DateColumn("만기일(Maturity)", format="YYYY-MM-DD"),
            "Currency": st.column_config.SelectboxColumn("통화", options=["USD", "EUR", "JPY", "CNY", "GBP"]),
            "Position": st.column_config.SelectboxColumn("구분", options=["Long", "Short"]),
            "Amount": st.column_config.NumberColumn("외화 금액", format="%.2f"),
            "Netted": st.column_config.CheckboxColumn("네팅 포함"),
            "Remark1": st.column_config.TextColumn("비고 1"),
            "Remark2": st.column_config.TextColumn("비고 2")
        },
        key="main_editor_stable"
    )

    actual_edited = edited_df.drop(columns=['No']) if 'No' in edited_df.columns else edited_df
    actual_edited['Date'] = pd.to_datetime(actual_edited['Date']).dt.date
    for c in ['Remark1', 'Remark2']:
        if c in actual_edited.columns: actual_edited[c] = actual_edited[c].astype(str).replace(['nan', 'None', ''], '')

    is_changed = not actual_edited.equals(compare_df)

    if st.button("✅ 변경사항 저장 및 분석 반영", type="primary", disabled=not is_changed):
        st.session_state['main_df'] = actual_edited.copy()
        st.success("저장 완료!")
        st.rerun()

# --- Tab 2: 상세 포지션 및 달러 환산 최종본 (수정본) ---
with tab2:
    df_t2 = st.session_state['main_df'].copy()
    
    # [실시간 엔진] 최신 환율 가져오기
    @st.cache_data(ttl=3600)
    def get_realtime_rates():
        tickers = {"USD": "USDKRW=X", "EUR": "EURKRW=X", "JPY": "JPYKRW=X", "CNY": "CNYKRW=X", "GBP": "GBPKRW=X"}
        current_rates = {}
        for curr, ticker in tickers.items():
            try:
                import yfinance as yf
                data = yf.Ticker(ticker).history(period='1d')
                current_rates[curr] = data['Close'].iloc[-1]
            except:
                backup = {"USD": 1350.0, "EUR": 1450.0, "JPY": 900.0, "CNY": 185.0, "GBP": 1700.0}
                current_rates[curr] = backup.get(curr)
        return current_rates

    real_rates = get_realtime_rates()
    usd_krw = real_rates.get("USD", 1350.0)

    if not df_t2.empty:
        st.subheader("⚖️ 상세 포지션 및 네팅 현황")
        interval = st.radio("📊 집계 구간 선택", ["일별", "주별", "월별"], horizontal=True, key="t2_final_fix")
        
        df_t2['Date'] = pd.to_datetime(df_t2['Date'])
        rule = {'일별': 'D', '주별': 'W', '월별': 'ME'}[interval]
        net_df = df_t2[df_t2['Netted'] == True].copy()
        
        if not net_df.empty:
            # 1. 상단 통화별 요약 지표 (다시 표시)
            unique_currs = sorted(net_df['Currency'].unique(), key=lambda x: (x != 'USD', x))
            curr_cols = st.columns(len(unique_currs))
            for i, curr in enumerate(unique_currs):
                with curr_cols[i]:
                    net_pos = net_df[net_df['Currency'] == curr].apply(
                        lambda x: x['Amount'] if str(x['Position']).strip().capitalize() == 'Long' else -x['Amount'], axis=1
                    ).sum()
                    curr_rate = real_rates.get(curr, 1.0)
                    usd_equiv = (net_pos * curr_rate) / usd_krw if curr != "USD" else net_pos
                    st.metric(f"{curr} 순포지션", f"{net_pos:,.2f}")
                    st.write(f"**💵 USD Eqv:** ${usd_equiv:,.2f}")
            
            st.divider()

            # 2. 데이터 가공
            grouped = net_df.set_index('Date').groupby([pd.Grouper(freq=rule), 'Currency'])
            rows = []
            for (dt, curr), group in grouped:
                long_v = group[group['Position'].str.strip().str.capitalize() == 'Long']['Amount'].sum()
                short_v = group[group['Position'].str.strip().str.capitalize() == 'Short']['Amount'].sum()
                label = dt.strftime('%Y-%m-%d') if interval == '일별' else (dt.strftime('%Y-%W주') if interval == '주별' else dt.strftime('%Y-%m'))
                rows.append({'기간': label, '통화': curr, '유입(Long)': long_v, '유출(Short)': short_v, '순포지션(Net)': long_v - short_v})

            if rows:
                raw_report = pd.DataFrame(rows)
                # 피벗 생성 및 빈 셀 0 처리 (.fillna(0))
                pivot_df = raw_report.pivot(index='기간', columns='통화', values=['유입(Long)', '유출(Short)', '순포지션(Net)']).fillna(0)
                pivot_df.columns = pivot_df.columns.swaplevel(0, 1)
                pivot_df = pivot_df.reindex(columns=unique_currs, level=0)

                # [필수] 맨 오른쪽 '전체통화 달러환산액' 컬럼 계산 및 추가
                def get_row_total_usd(row):
                    total_usd = 0
                    for curr in unique_currs:
                        val = row.get((curr, '순포지션(Net)'), 0)
                        rate = real_rates.get(curr, 1.0)
                        total_usd += (val * rate) / usd_krw
                    return total_usd

                # 컬럼명을 명확히 지정하여 추가
                pivot_df[('Total', 'USD 환산액')] = pivot_df.apply(get_row_total_usd, axis=1)

                # --- 합계 행 계산 ---
                total_series = pivot_df.sum()
                total_row = total_series.to_frame().T
                total_row.index = ['합계(Total)']

                # 달러 환산액 전용 행 (합계 아래 추가)
                usd_val_data = {}
                for curr in unique_currs:
                    rate = real_rates.get(curr, 1.0)
                    net_sum = total_series[(curr, '순포지션(Net)')]
                    usd_val_data[(curr, '유입(Long)')] = 0 # 빈 셀 대신 0
                    usd_val_data[(curr, '유출(Short)')] = 0
                    usd_val_data[(curr, '순포지션(Net)')] = (net_sum * rate) / usd_krw
                
                # 전체 합계 칸 (우측 끝)
                usd_val_data[('Total', 'USD 환산액')] = total_series[('Total', 'USD 환산액')]
                usd_val_row = pd.DataFrame(usd_val_data, index=['└ 달러환산액(USD Eqv)'])

                # 최종 결합
                final_df = pd.concat([pivot_df, total_row, usd_val_row])

                # 스타일링 및 출력
                st.markdown(f"#### 📊 {interval} 상세 포지션 내역 (전체 달러 환산 포함)")
                st.dataframe(
                    final_df.style.format("{:,.2f}")
                    .set_properties(**{'text-align': 'right'})
                    .apply(lambda s: ['background-color: #f8f9fa; font-weight: bold' if s.name == '합계(Total)' else 
                                      ('background-color: #e8f0fe; color: #1a73e8; font-weight: bold' if s.name == '└ 달러환산액(USD Eqv)' else '') for _ in s], axis=1),
                    use_container_width=True
                )
            else:
                st.info("데이터가 없습니다.")

# --- Tab 3: 몬테카를로 시뮬레이션 및 확률 분석 ---
with tab3:
    import numpy as np
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from scipy.stats import norm

    st.subheader("🎲 몬테카를로 환율 리스크 시뮬레이션")

    # 1. 사이드바 설정 (사용자 입력 필드)
    st.sidebar.header("⚙️ 시뮬레이션 설정")
    
    # 분석 통화 선택 및 실시간 환율
    target_curr = st.selectbox("💱 분석 대상 통화 선택", ["USD", "EUR", "JPY", "CNY", "GBP"], key="mc_curr")
    curr_rate_now = real_rates.get(target_curr, 1350.0)
    
    st.sidebar.subheader(f"[{target_curr}] 변동성 및 기준 설정")
    volatility = st.sidebar.slider("📉 연 변동성(Volatility, %)", min_value=1.0, max_value=30.0, value=10.0, step=0.5) / 100
    
    budget_rate = st.sidebar.number_input("💰 예산 환율", value=float(round(curr_rate_now, 1)), step=1.0)
    target_rate = st.sidebar.number_input("🎯 타겟 환율", value=float(round(curr_rate_now - 10, 1)), step=1.0)
    
    st.sidebar.info(f"현재 {target_curr} 실시간 환율: {curr_rate_now:,.2f}원")

    # 2. 몬테카를로 엔진 (Geometric Brownian Motion)
    n_sims = 1000  # 시뮬레이션 횟수
    t_days = 30    # 예측 기간 (일)
    dt = 1 / 252   # 일일 단위 시간
    
    # 순포지션 합계 계산
    sim_net_df = st.session_state['main_df']
    sim_net_df = sim_net_df[(sim_net_df['Currency'] == target_curr) & (sim_net_df['Netted'] == True)]
    total_net_amt = sim_net_df.apply(
        lambda x: x['Amount'] if str(x['Position']).strip().capitalize() == 'Long' else -x['Amount'], axis=1
    ).sum()

    # 시뮬레이션 실행
    # (단순화를 위해 기대수익률 무위험이자율 0 가정 시)
    daily_vol = volatility * np.sqrt(dt)
    sim_results = np.zeros((t_days, n_sims))
    sim_results[0] = curr_rate_now

    for t in range(1, t_days):
        drift = (0 - 0.5 * volatility**2) * dt
        shock = volatility * np.sqrt(dt) * np.random.standard_normal(n_sims)
        sim_results[t] = sim_results[t-1] * np.exp(drift + shock)

    # 3. 시각화 섹션
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"##### 🌤️ {target_curr} 가격 경로 구름 챠트")
        x_axis = np.arange(t_days)
        upper_95 = np.percentile(sim_results, 95, axis=1)
        lower_05 = np.percentile(sim_results, 5, axis=1)
        median_path = np.median(sim_results, axis=1)

        fig_cloud = go.Figure()
        # 구름(신뢰구간) 추가
        fig_cloud.add_trace(go.Scatter(x=np.concatenate([x_axis, x_axis[::-1]]), 
                                       y=np.concatenate([upper_95, lower_05[::-1]]),
                                       fill='toself', fillcolor='rgba(0,100,80,0.2)',
                                       line=dict(color='rgba(255,255,255,0)'), name='90% 신뢰구간'))
        # 중앙 경로 및 기준선
        fig_cloud.add_trace(go.Scatter(x=x_axis, y=median_path, line=dict(color='teal', width=2), name='중앙값'))
        fig_cloud.add_hline(y=budget_rate, line_dash="dash", line_color="red", annotation_text="예산")
        fig_cloud.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=350, showlegend=False)
        st.plotly_chart(fig_cloud, use_container_width=True)

    with col2:
        st.markdown("##### 📊 기말 예상 손익 히스토그램")
        final_rates = sim_results[-1]
        final_profits = (final_rates - budget_rate) * total_net_amt
        
        fig_hist = px.histogram(final_profits, nbins=50, color_discrete_sequence=['#1a73e8'])
        fig_hist.add_vline(x=0, line_width=2, line_color="black")
        fig_hist.update_layout(margin=dict(l=10, r=10, t=30, b=10), height=350, showlegend=False, 
                               xaxis_title="KRW 손익", yaxis_title="빈도")
        st.plotly_chart(fig_hist, use_container_width=True)

    # 4. 확률 구간별 분석 (20% 구간)
    st.markdown("##### 📑 확률 구간별 예측 환율 및 손익 변동액")
    
    percentiles = [10, 30, 50, 70, 90] # 20% 간격 중심점
    analysis_data = []
    
    for p in percentiles:
        rate_at_p = np.percentile(final_rates, p)
        profit_at_p = (rate_at_p - budget_rate) * total_net_amt
        
        status = "🟢 이익" if profit_at_p > 0 else "🔴 손실"
        prob_label = f"하위 {p}% 수준"
        
        analysis_data.append({
            "확률 구간": prob_label,
            "예측 환율": rate_at_p,
            "예상 손익(KRW)": profit_at_p,
            "상태": status
        })

    analysis_df = pd.DataFrame(analysis_data)
    
    st.table(analysis_df.style.format({
        "예측 환율": "{:,.2f}원",
        "예상 손익(KRW)": "{:,.0f}원"
    }).map(lambda x: 'color: red' if "🔴" in str(x) else ('color: green' if "🟢" in str(x) else ''), subset=['상태']))

    st.caption(f"※ 몬테카를로 시뮬레이션 {n_sims}회 수행 결과 (연 변동성 {volatility*100}% 반영)")