import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 초기화
st.set_page_config(page_title="FX Netting & Risk Simulator", layout="wide")
st.title("📊 FX 포지션 관리 및 몬테카를로 시뮬레이터")

# --- 공통 함수 (Global) ---
def get_forward_rate(spot, r_base, r_quote, days):
    t = max(days, 0) / 365
    return spot * np.exp((r_quote - r_base) * t)

def get_present_value(amount, rate, days):
    t = max(days, 0) / 365
    return amount * np.exp(-rate * t)

if 'main_df' not in st.session_state:
    st.session_state['main_df'] = pd.DataFrame(columns=[
        'Date', 'Currency', 'Position', 'Amount', 'Budget Rate', 'Netted', 'Remark1', 'Remark2'
    ])

if 'market_rates' not in st.session_state:
    st.session_state['market_rates'] = {
        'USD': 0.0525, 'KRW': 0.0350, 'JPY': 0.0010, 'EUR': 0.0400, 'CNY': 0.0250, 'GBP': 0.0500
    }

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

# --- Tab 2: 캐시플로우 (스케줄 기반 PV 합산 방식) ---
with tab2:
    df_t2 = st.session_state.get('main_df', pd.DataFrame()).copy()
    if not df_t2.empty:
        net_df = df_t2[df_t2['Netted'] == True].copy()
        if not net_df.empty:
            st.subheader("⚖️ 통화별 캐시플로우 및 현가(PV) 정밀 검증")
            st.caption(f"📅 환율 데이터 채집 일시: {last_update}")
            
            interval = st.radio("📅 집계 주기", ["일별", "주별", "월별"], horizontal=True)
            net_df['Date'] = pd.to_datetime(net_df['Date'])
            rule = {'일별': 'D', '주별': 'W', '월별': 'ME'}[interval]
            
            curr_m_rates = st.session_state['market_rates']
            spot_usd_krw = float(real_rates.get("USD", 1380.0))
            valuation_date = datetime.now()

            all_currs = net_df['Currency'].unique().tolist()
            sorted_currs = (["USD"] + sorted([c for c in all_currs if c != "USD"])) if "USD" in all_currs else sorted(all_currs)

            # --- 1. 데이터 집계 및 PV 계산 루프 (명칭 통일) ---
            rows = []
            grouped = net_df.set_index('Date').groupby([pd.Grouper(freq=rule), 'Currency'])
            
            for (dt, curr), group in grouped:
                days = max((dt - valuation_date).days, 0)
                l_v = float(group[group['Position'].str.strip().str.capitalize() == 'Long']['Amount'].sum())
                s_v = -abs(float(group[group['Position'].str.strip().str.capitalize() == 'Short']['Amount'].sum()))
                n_v = l_v + s_v
                
                # 금융공학 로직 (현가 할인)
                if curr == 'USD':
                    usd_pv = get_present_value(n_v, curr_m_rates['USD'], days)
                    pv_l = get_present_value(l_v, curr_m_rates['USD'], days)
                    pv_s = get_present_value(s_v, curr_m_rates['USD'], days)
                else:
                    c_spot = float(real_rates.get(curr, 0))
                    s_in_u = c_spot / spot_usd_krw if spot_usd_krw != 0 else 0
                    fwd = get_forward_rate(s_in_u, curr_m_rates.get(curr, 0.02), curr_m_rates['USD'], days)
                    usd_pv = get_present_value(n_v * fwd, curr_m_rates['USD'], days)
                    pv_l = get_present_value(l_v * fwd, curr_m_rates['USD'], days)
                    pv_s = get_present_value(s_v * fwd, curr_m_rates['USD'], days)
                
                # 단순 환산액
                usd_simple = (n_v * float(real_rates.get(curr, 0))) / spot_usd_krw if curr != "USD" else n_v
                
                label = dt.strftime('%Y-%m-%d') if interval == '일별' else (dt.strftime('%Y-%U주') if interval == '주별' else dt.strftime('%Y-%m'))
                
                # [중요] 여기서 사용한 key 이름들이 아래 groupby에서 사용됩니다.
                rows.append({
                    '기간': label, '통화': curr, 
                    '유입(In)': l_v, '유출(Out)': s_v, '순액(Net)': n_v, 
                    'usd_simple': usd_simple,  # 이 이름이 일치해야 함
                    'usd_pv': usd_pv,
                    'pv_l': pv_l, 'pv_s': pv_s
                })

            # --- 2. 테이블 생성 및 스타일링 ---
            if rows:
                raw_report = pd.DataFrame(rows)
                pivot_df = raw_report.pivot(index='기간', columns='통화', values=['유입(In)', '유출(Out)', '순액(Net)'])
                pivot_df = pivot_df.swaplevel(0, 1, axis=1).reindex(sorted_currs, axis=1, level=0).reindex(['유입(In)', '유출(Out)', '순액(Net)'], axis=1, level=1)
                
                total_usd_col = ('Total', 'USD Equivalent')
                # [KeyError 해결] 위에서 정의한 'usd_simple'을 정확히 참조
                pivot_df[total_usd_col] = raw_report.groupby('기간')['usd_simple'].sum()
                pivot_df = pivot_df.fillna(0.0)

                # 합계 행 구성
                sum_values = pivot_df.sum()
                sum_df = pd.DataFrame(sum_values).T
                sum_df.index = ['합계(Grand Total)']
                
                # [요청사항] Grand Total의 최우측 셀 비우기
                sum_df.at['합계(Grand Total)', total_usd_col] = np.nan 

                # 최종 달러 환산 합계 (Spot)
                final_simple_row = pd.Series(0.0, index=pivot_df.columns, dtype=float)
                for curr in sorted_currs:
                    rate = float(real_rates.get(curr, 0))
                    for sub in ['유입(In)', '유출(Out)', '순액(Net)']:
                        orig = sum_values[(curr, sub)]
                        final_simple_row[(curr, sub)] = (orig * rate) / spot_usd_krw if curr != "USD" else orig
                final_simple_row[total_usd_col] = raw_report['usd_simple'].sum()
                
                # 달러환산 PV 금액 (금융공학) - 모든 셀 표시
                final_pv_row = pd.Series(0.0, index=pivot_df.columns, dtype=float)
                for curr in sorted_currs:
                    final_pv_row[(curr, '유입(In)')] = raw_report[raw_report['통화'] == curr]['pv_l'].sum()
                    final_pv_row[(curr, '유출(Out)')] = raw_report[raw_report['통화'] == curr]['pv_s'].sum()
                    final_pv_row[(curr, '순액(Net)')] = raw_report[raw_report['통화'] == curr]['usd_pv'].sum()
                final_pv_row[total_usd_col] = raw_report['usd_pv'].sum()
                
                # 행 통합
                final_display_df = pd.concat([
                    pivot_df, 
                    sum_df, 
                    pd.DataFrame(final_simple_row).T.rename(index={0: '최종 달러 환산 합계 (Spot)'}),
                    pd.DataFrame(final_pv_row).T.rename(index={0: '달러환산 PV 금액 (금융공학)'})
                ])

                # 스타일링 함수 적용
                def apply_final_style(styler):
                    styler.format("{:,.2f}", na_rep="-")
                    # 합계 행 & Total 칼럼 스타일
                    styler.set_properties(**{'background-color': '#F2F2F2', 'font-weight': 'bold'}, 
                                         subset=(['합계(Grand Total)'], pd.IndexSlice[:, :]))
                    styler.set_properties(**{'background-color': '#F2F2F2', 'font-weight': 'bold'}, 
                                         subset=pd.IndexSlice[:, [total_usd_col]])
                    # PV 금액 행 스타일 (파란색 폰트)
                    styler.set_properties(**{'color': '#0000FF', 'font-weight': 'bold', 'background-color': '#E3F2FD'}, 
                                         subset=(['달러환산 PV 금액 (금융공학)'], pd.IndexSlice[:, :]))
                    return styler

                st.dataframe(apply_final_style(final_display_df.style), use_container_width=True)

                # 하단 환율 테이블 및 채집 일시 표시
                st.markdown("---") # 구분선 추가
                st.subheader(f"💱 실시간 시장 지표 (채집: {last_update})") # 타이틀에 시각 표시

                # 테이블 데이터 생성
                rate_data = [
                    {
                        "통화": c, 
                        "환율": f"{float(real_rates.get(c, 0)):,.2f}", 
                        "금리": f"{curr_m_rates.get(c, 0.02)*100:.2f}%"
                    } for c in sorted_currs
                ]

                # 테이블 출력
                st.table(pd.DataFrame(rate_data))

                # (선택사항) 테이블 바로 아래에 작은 글씨로 한 번 더 표시하고 싶을 때
                # st.caption(f"※ 위 데이터는 {last_update} 기준 실시간 시장 환율을 반영하고 있습니다.")

# --- Tab 3: 실시간 리스크 시뮬레이션 (현가 분석 및 몬테카를로) ---
with tab3:
    st.header("🧪 외환 리스크 시뮬레이션 및 포트폴리오 분석")
    
    # 분석 대상 데이터 필터링 (Netted가 True인 데이터만)
    df_netting = st.session_state['main_df'][st.session_state['main_df']['Netted'] == True].copy()
    
    if not df_netting.empty:
        with st.expander("🌐 시장 데이터 및 시뮬레이션 설정", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                # 현물 환율 및 변동성 설정
                current_spot = real_rates.get("USD", 1380.0)
                sim_spot = st.number_input("기준 USD/KRW 환율", value=float(current_spot), key="sim_spot")
                volatility = st.slider("연 변동성 (%)", 5.0, 30.0, 12.0) / 100
            with c2:
                # 금리 설정 (수정 시 탭 2의 PV 계산에도 즉시 반영됨)
                r_usd = st.number_input("USD 이자율", value=st.session_state['market_rates']['USD'], format="%.4f", key="sim_r_usd")
                r_krw = st.number_input("KRW 이자율", value=st.session_state['market_rates']['KRW'], format="%.4f", key="sim_r_krw")
                
                # 세션 상태 업데이트
                st.session_state['market_rates']['USD'] = r_usd
                st.session_state['market_rates']['KRW'] = r_krw
            with c3:
                iter_count = st.select_slider("시뮬레이션 횟수", options=[100, 500, 1000], value=500)
                target_rate = st.number_input("목표(예산) 환율", value=1350.0)

        # --- [로직 확인] 포트폴리오 스케줄별 현가(PV) 계산 ---
        valuation_date = datetime.now()
        portfolio_results = []
        
        for _, row in df_netting.iterrows():
            target_date = pd.to_datetime(row['Date'])
            days = max((target_date - valuation_date).days, 0)
            curr = row['Currency']
            amt = float(row['Amount']) if str(row['Position']).capitalize() == 'Long' else -abs(float(row['Amount']))

            if curr == 'USD':
                # 달러 포지션: 스케줄별 직접 할인
                usd_pv_val = get_present_value(amt, r_usd, days)
                krw_pv_val = usd_pv_val * sim_spot
            else:
                # 이종통화: 선도환율 적용 후 달러 현가화
                curr_spot = float(real_rates.get(curr, 0))
                spot_in_usd = curr_spot / sim_spot if sim_spot != 0 else 0
                fwd_rate = get_forward_rate(spot_in_usd, st.session_state['market_rates'].get(curr, 0.02), r_usd, days)
                usd_pv_val = get_present_value(amt * fwd_rate, r_usd, days)
                krw_pv_val = usd_pv_val * sim_spot

            portfolio_results.append({'USD_PV': usd_pv_val, 'KRW_PV': krw_pv_val})

        df_p = pd.DataFrame(portfolio_results)
        total_usd_pv = df_p['USD_PV'].sum()
        total_krw_pv = df_p['KRW_PV'].sum()
        
        # 포트폴리오 BEP (손익분기점 환율)
        bep = total_krw_pv / total_usd_pv if abs(total_usd_pv) > 0.1 else sim_spot

        # --- 몬테카를로 시뮬레이션 엔진 (GBM 모델) ---
        steps = 90  # 향후 90일 예측
        dt = 1/365
        paths = np.zeros((steps, iter_count))
        paths[0] = sim_spot
        
        for t in range(1, steps):
            rand = np.random.standard_normal(iter_count)
            # 수식: Drift(내외금리차) + Diffusion(변동성)
            drift = (r_krw - r_usd - 0.5 * volatility**2) * dt
            diffusion = volatility * np.sqrt(dt) * rand
            paths[t] = paths[t-1] * np.exp(drift + diffusion)

        # --- 결과 표시 대시보드 ---
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("총 노출액 (USD PV)", f"${total_usd_pv:,.2f}")
        m2.metric("포트폴리오 BEP", f"₩{bep:,.2f}", delta=f"{bep - target_rate:,.2f} (vs 목표)")
        
        # VaR (95% 신뢰수준 최대 손실액)
        ending_prices = paths[-1]
        var_95_price = np.percentile(ending_prices, 5) if total_usd_pv > 0 else np.percentile(ending_prices, 95)
        var_amount = abs(total_usd_pv * (bep - var_95_price))
        m3.metric("VaR (95% 신뢰수준)", f"₩{var_amount:,.0f}", help="90일 내 발생 가능한 최대 예상 손실")

        # 시각화 (Plotly)
        fig = go.Figure()
        x_axis = [valuation_date + timedelta(days=i) for i in range(steps)]
        
        # 확률 구간 표시
        fig.add_trace(go.Scatter(x=x_axis, y=np.percentile(paths, 95, axis=1), line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=x_axis, y=np.percentile(paths, 5, axis=1), fill='tonexty', 
                                 fillcolor='rgba(255, 0, 0, 0.1)', name='신뢰구간 (95%)'))
        
        # 중간 경로 (Median)
        fig.add_trace(go.Scatter(x=x_axis, y=np.median(paths, axis=1), line=dict(color='blue', width=2), name='예상 경로 (Median)'))
        
        # BEP 선 표시
        fig.add_hline(y=bep, line_dash="dash", line_color="green", annotation_text="BEP Line")
        
        fig.update_layout(title="USD/KRW 환율 시뮬레이션 (90일)", xaxis_title="날짜", yaxis_title="환율 (KRW)", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("💡 분석할 데이터가 없습니다. 탭 1에서 데이터를 입력해 주세요.")