import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 설정 및 초기화
st.set_page_config(page_title="FX Netting & Risk Simulator", layout="wide")
import streamlit as st

# [추가] 폰트 크기 일괄 조정 CSS
st.set_page_config(page_title="FX Netting & Risk Simulator", layout="wide")
st.markdown("""
    <style>
    /* 1. 전체 타이틀 (H1) 크기 조정 */
    h1 {
        font-size: 32px !important;
        font-weight: 700 !important;
        padding-bottom: 20px !important;
    }
    /* 2. 섹션 헤더 (H2) 크기 조정 */
    h2, .stMarkdown h2 {
        font-size: 26px !important;
        font-weight: 700 !important;
        padding-top: 15px !important;
        padding-bottom: 10px !important;
    }
    /* 3. 서브헤더 (H3) 및 섹션 타이틀 크기 조정 */
    h3, .stMarkdown h3 {
        font-size: 18px !important;
        font-weight: 600 !important;
        padding-top: 10px !important;
        padding-bottom: 5px !important;
    }
    /* 본문 텍스트 간격 조정 (크기는 유지) */
    .stMarkdown p {
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <style>
    /* --- 기존 헤더 설정 (유지) --- */
    h1 { font-size: 26px !important; }
    h2 { font-size: 22px !important; padding-bottom: 25px !important; }
    h3 { font-size: 17px !important; }

    /* --- Expander 제목(Title) 폰트 사이즈 조정 --- */
    /* p 태그로 감싸진 제목 부분 타겟팅 */
    .stExpander summary p {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #31333F !important;
    }
    
    /* 제목 옆의 아이콘 크기도 살짝 조정 */
    .stExpander summary svg {
        width: 14px !important;
        height: 14px !important;
    }

    /* --- Expander 내부 본문 및 리스트 폰트 사이즈 조정 --- */
    .stExpander div[data-testid="stVerticalBlock"] p,
    .stExpander div[data-testid="stVerticalBlock"] li {
        font-size: 12px !important;
        line-height: 1.4 !important;
        color: #555555 !important;
    }

    /* Expander 전체 높이 살짝 줄이기 */
    .stExpander {
        border-radius: 8px !important;
        margin-bottom: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

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
        'USD': 0.0500, 'KRW': 0.0350, 'JPY': 0.0010, 'EUR': 0.0400, 'CNY': 0.0250, 'GBP': 0.0500
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
    with st.expander("👉 데이터 작성 상세 규칙", expanded=True):
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
            * **파일 업로드**: 파일 업로드 후 **데이터 병합하기** 클릭하면 하단의 데이타 편집창으로 출력됩니다.
            * **저장 필수**: 개별 건 직접 입력 또는 수정 후 반드시 하단의 **[💾 변경사항 저장]** 버튼을 클릭하세요.
            """)

    st.divider()
    col_up, col_form = st.columns([1, 1])
    
    with col_up:
        st.subheader("📁 파일 업로드")
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
        st.subheader("📋 전체 데이터 편집")
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
            st.subheader("⚖️ 통화별 캐시플로우 및 현가(PV) 산출")
            st.write("") # 빈 줄 추가
            
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

# --- Tab 3: 실시간 리스크 시뮬레이션 및 리스크 분석 ---
with tab3:
    st.header("🧪 외환 리스크 시뮬레이션 및 리스크 분석")

    # --- 모델 가정 설명 ---
    with st.expander("ℹ️ 시뮬레이션 모델 가정 및 데이터 출처 안내", expanded=False):
        st.markdown("""
        **1. 환율 데이터 (Real-time):**
        * 현재 시점의 Spot 환율은 `Yahoo Finance`를 통해 실시간으로 업데이트된 데이터를 사용합니다 (현재 **시간별** 채집).
        
        **2. 금리 데이터 (Fixed/User-defined):**
        * 시뮬레이션에 사용된 각 통화별 무위험 금리(Risk-free Rate)는 현재 **고정된 추정값**을 적용합니다. 
        * 금리는 선물환(Forward) 가격 결정 및 현가(PV) 할인에 직접적인 영향을 미치므로, 설정값 변경을 위하여 슬라이더를 사용할 수 있습니다.
        
        **3. 몬테카를로 엔진:**
        * 본 시뮬레이션은 **기하 브라운 운동(GBM)** 모델을 따르며, 연간 변동성(Standard Deviation)을 기반으로 무작위 경로를 생성합니다.
        * 통화별 변동성은 현재 **고정된 추정값**을 적용하므로, 설정값 변경을 위하여 슬라이더를 사용할 수 있습니다.
        """)   
    df_sim = st.session_state['main_df'][st.session_state['main_df']['Netted'] == True].copy()
    st.write("") # 빈 행 추가
    
    if not df_sim.empty:
        col_side, col_main = st.columns([1, 3])

        with col_side:
            st.subheader("🌐 시장 변수 설정")
            with st.container(border=True):
                cur_usd_spot = float(real_rates.get("USD", 1380.0))
                sim_spot = st.number_input("현재 환율 (Spot)", value=cur_usd_spot, step=1.0)
                sim_days = st.slider("분석 기간 (일)", 10, 365, 90)
                volatility = st.slider("시장 변동성 (연 %)", 5.0, 30.0, 10.0) / 100
                r_krw = st.number_input("원화 금리 (%)", value=st.session_state['market_rates']['KRW']*100, format="%.2f") / 100
                r_usd = st.number_input("미국 금리 (%)", value=st.session_state['market_rates']['USD']*100, format="%.2f") / 100

            st.subheader("🚩 위험 분석 설정")
            with st.container(border=True):
                budget_rate = st.number_input("예산 환율 (Budget Line)", value=1350.0, step=1.0)
                hedge_rate = st.number_input("헤지 환율 (Hedge Target)", value=1400.0, step=1.0)
            
            iter_count = st.select_slider("시뮬레이션 횟수", options=[5000, 10000, 20000, 30000, 40000, 50000], value=10000)

        with col_main:
            # --- 1. 포트폴리오 노출액(PV) 계산 ---
            valuation_date = datetime.now()
            total_usd_pv = 0.0
            for _, row in df_sim.iterrows():
                target_date = pd.to_datetime(row['Date'])
                days = max((target_date - valuation_date).days, 0)
                curr = row['Currency']
                amt = float(row['Amount']) if str(row['Position']).capitalize() == 'Long' else -abs(float(row['Amount']))
                if curr == 'USD':
                    total_usd_pv += get_present_value(amt, r_usd, days)
                else:
                    curr_spot = float(real_rates.get(curr, 0))
                    spot_in_usd = curr_spot / sim_spot if sim_spot != 0 else 0
                    fwd_rate = get_forward_rate(spot_in_usd, st.session_state['market_rates'].get(curr, 0.02), r_usd, days)
                    total_usd_pv += get_present_value(amt * fwd_rate, r_usd, days)

            # --- 2. 시뮬레이션 엔진 ---
            steps = sim_days
            dt = 1/365
            paths = np.zeros((steps, iter_count))
            paths[0] = sim_spot
            for t in range(1, steps):
                rand = np.random.standard_normal(iter_count)
                paths[t] = paths[t-1] * np.exp((r_krw - r_usd - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * rand)
            
            ending_prices = paths[-1]
            
            # --- 3. [최종 교정] 포지션별 리스크 및 헤지 로직 ---
            is_export = total_usd_pv >= 0 # 양수 = 수출(Long)

            if is_export:
                # 수출(Long): 환율 하락이 위험, 하락 시 헤지 실행
                # 위험: 만기 시 환율이 예산보다 낮을 확률
                prob_breach = (ending_prices < budget_rate).mean() * 100
                # 헤지: 기간 중 한 번이라도 환율이 헤지 환율 이하로 '하락'할 확률 (Lower Touch)
                reached_hedge = np.any(paths <= hedge_rate, axis=0)
                risk_label, risk_delta = "예산 환율 하회 확률", "Breach Risk"
            else:
                # 수입(Short): 환율 상승이 위험, 상승 시 헤지 실행
                # 위험: 만기 시 환율이 예산보다 높을 확률
                prob_breach = (ending_prices > budget_rate).mean() * 100
                # 헤지: 기간 중 한 번이라도 환율이 헤지 환율 이상으로 '상승'할 확률 (Upper Touch)
                reached_hedge = np.any(paths >= hedge_rate, axis=0)
                risk_label, risk_delta = "예산 환율 상회 확률", "Breach Risk"
            
            prob_reach_hedge = reached_hedge.mean() * 100

            # --- 4. 상단 지표 요약 (USD PV 포함 테두리 박스 그룹화) ---
            with st.container(border=True): # 이 줄을 추가하여 4개 항목을 그룹으로 묶고 테두리 표시
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("순포지션 (USD PV)", f"${total_usd_pv:,.0f}")
                m2.metric(f"{sim_days}일 후 예상 환율", f"₩{np.median(ending_prices):,.2f}")
                m3.metric(risk_label, f"{prob_breach:.1f}%", delta=risk_delta, delta_color="inverse")
                m4.metric("헤지 환율 터치 확률", f"{prob_reach_hedge:.1f}%", delta="Hedge recommended")
 
            # --- 5. 시각화 (기존 스타일 유지) ---
            c_chart1, c_chart2 = st.columns(2)
            with c_chart1:
                st.subheader("📈 환율 경로 예측")
                fig_path = go.Figure()
                x_axis = [valuation_date + timedelta(days=i) for i in range(steps)]
                fig_path.add_trace(go.Scatter(x=x_axis, y=np.percentile(paths, 95, axis=1), line=dict(width=0), showlegend=False))
                fig_path.add_trace(go.Scatter(x=x_axis, y=np.percentile(paths, 5, axis=1), fill='tonexty', fillcolor='rgba(0, 100, 255, 0.1)', name='90% 신뢰구간'))
                fig_path.add_trace(go.Scatter(x=x_axis, y=np.median(paths, axis=1), line=dict(color='blue', width=2), name='Median'))
                fig_path.add_hline(y=budget_rate, line_dash="dot", line_color="red", annotation_text="Budget")
                fig_path.add_hline(y=hedge_rate, line_dash="dash", line_color="green", annotation_text="Hedge")
                fig_path.update_layout(height=350, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_path, use_container_width=True)

            with c_chart2:
                st.subheader("📊 만기 환율 분포")
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Histogram(x=ending_prices, nbinsx=50, marker_color='lightgray', opacity=0.7))
                fig_hist.add_vline(x=np.median(ending_prices), line_width=2, line_color="blue", annotation_text="중앙값")
                fig_hist.add_vline(x=budget_rate, line_dash="dot", line_color="red", line_width=2, annotation_text="예산")
                fig_hist.add_vline(x=hedge_rate, line_dash="dash", line_color="green", line_width=2, annotation_text="헤지")
                fig_hist.update_layout(height=350, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_hist, use_container_width=True)

            # --- 6. 민감도 표 ---
            st.subheader("📉 확률 구간별 예상 손익")
            percentiles = [5, 25, 50, 75, 95]
            sensitivity_data = []
            for p in percentiles:
                price = np.percentile(ending_prices, p)
                diff = price - sim_spot
                diff_pct = (diff / sim_spot) * 100 if sim_spot != 0 else 0
                pnl = (price - budget_rate) * total_usd_pv
                pnl_str = f"₩{pnl:,.0f}" if pnl >= 0 else f"-₩{abs(pnl):,.0f}"
                sensitivity_data.append({
                    "분포 구간": f"하위 {p}%", "예상 환율": f"₩{price:,.2f}",
                    "환율 변동폭(원)": f"{diff:+,.2f} ({diff_pct:+.2f}%)",
                    "예산 환율과의 갭(원)": f"{price - budget_rate:+,.2f}",
                    "예상 평가손익(원)": pnl_str
                })
            st.table(pd.DataFrame(sensitivity_data))

    else:
        st.info("💡 분석할 데이터가 없습니다. 탭 1에서 데이터를 입력해 주세요.")