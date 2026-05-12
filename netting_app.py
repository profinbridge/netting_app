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
        font-size: 36px !important;
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
    /* 1. 사이드바 내 모든 버튼의 폰트 크기 및 높이 조정 */
    div[data-testid="stSidebar"] button {
        font-size: 12px !important;
        font-weight: 500 !important;
        padding-top: 5px !important;
        padding-bottom: 5px !important;
        min-height: 30px !important;
    }
    
    /* 2. 사이드바 내 도움말(help) 아이콘 크기 조정 */
    div[data-testid="stSidebar"] .stButton svg {
        width: 12px !important;
        height: 12px !important;
    }

    /* 3. 사이드바 내 섹션 타이틀(💡 체험하기 등) 크기 조정 */
    div[data-testid="stSidebar"] .stMarkdown h3 {
        font-size: 14px !important;
        margin-bottom: 10px !important;
    }

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

st.title("📊 FX_RISK 시뮬레이터")

# --- [신규 추가] 체험하기 버튼 및 데이터 로드 로직 ---
st.sidebar.markdown("### 💡 체험하기")

# 버튼 클릭 시 세션 상태에 샘플 데이터 주입
if st.sidebar.button("🚗 수출기업 샘플 데이타 로드", help="실시간 리스크를 시뮬레이션합니다. 데이타 로드 후 아래 **변경사항 저장** 버튼을 클릭하세요"):
    # Tab 1용 데이터
    st.session_state['main_df'] = pd.DataFrame([
        {'Date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'), 'Currency': 'USD', 'Position': 'Long', 'Amount': 700000.0, 'Budget Rate': 1380.0, 'Netted': True, 'Remark1': "미국 수출 대금(1차)", 'Remark2': ""},
        {'Date': (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d'), 'Currency': 'USD', 'Position': 'Long', 'Amount': 500000.0, 'Budget Rate': 1380.0, 'Netted': True, 'Remark1': "미국 수출 대금(2차)", 'Remark2': ""},
        {'Date': (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d'), 'Currency': 'USD', 'Position': 'Short', 'Amount': 200000.0, 'Budget Rate': 1380.0, 'Netted': True, 'Remark1': "부품 수입 결제", 'Remark2': ""}
    ])
    
    # Tab 3용 설정값 (환율 1,450원 기준)
    st.session_state['sim_spot'] = 1450.0
    st.session_state['sim_days'] = 90
    st.session_state['volatility'] = 15.0
    st.session_state['budget_rate'] = 1380.0
    st.session_state['hedge_rate'] = 1430.0
    
    st.sidebar.success("현재 환율 1,450원 예산 환율 1,380원 기준 시나리오 로드 완료!")

    # --- [신규 추가] 수입기업 샘플 버튼 로직 ---
if st.sidebar.button("📦 수입기업 샘플 데이타 로드", help="실시간 리스크를 시뮬레이션합니다. 데이타 로드 후 아래 **변경사항 저장** 버튼을 클릭하세요"):
    # Tab 1용 데이터: 수입 결제 2건 + 소액 수출 네팅
    st.session_state['main_df'] = pd.DataFrame([
        {'Date': (datetime.now() + timedelta(days=20)).strftime('%Y-%m-%d'), 'Currency': 'USD', 'Position': 'Short', 'Amount': 600000.0, 'Budget Rate': 1420.0, 'Netted': True, 'Remark1': "원자재 수입결제(A사)", 'Remark2': ""},
        {'Date': (datetime.now() + timedelta(days=50)).strftime('%Y-%m-%d'), 'Currency': 'USD', 'Position': 'Short', 'Amount': 400000.0, 'Budget Rate': 1420.0, 'Netted': True, 'Remark1': "설비 도입 잔금", 'Remark2': ""},
        {'Date': (datetime.now() + timedelta(days=40)).strftime('%Y-%m-%d'), 'Currency': 'USD', 'Position': 'Long', 'Amount': 100000.0, 'Budget Rate': 1420.0, 'Netted': True, 'Remark1': "샘플 수출 대금 유입", 'Remark2': ""}
    ])
    
    # Tab 3용 설정값 (환율 1,450원 기준 수입 리스크 상황)
    st.session_state['sim_spot'] = 1450.0      # 현재 환율
    st.session_state['sim_days'] = 60        # 분석 기간
    st.session_state['volatility'] = 12.0     # 변동성 12%
    st.session_state['budget_rate'] = 1420.0  # 예산 환율 (이미 넘어서서 손실 구간임)
    st.session_state['hedge_rate'] = 1470.0   # 손절 혹은 추가 헤지 타겟
    
    st.sidebar.success("현재 환율 1,450원 예산 환율 1,420원 기준 시나리오 로드 완료!")

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

tab1, tab2, tab3, tab4 = st.tabs([
    "📥 데이터 입력 및 편집", 
    "📅 캐시플로우", 
    "🧪 실시간 리스크 시뮬레이션",
    "📖 이용 가이드"
])

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
    st.header("🧪 실시간 리스크 시뮬레이션 및 리스크 분석")

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
                sim_spot = st.number_input(
                    "현재 환율 (Spot)", 
                    value=st.session_state.get('sim_spot', cur_usd_spot), # 여기서 결정됩니다!
                    step=1.0
                )
                sim_days = st.slider("분석 기간 (일)", 10, 365, 90)
                volatility = st.slider("시장 변동성 (연 %)", 5.0, 30.0, 10.0) / 100
                r_krw = st.number_input("원화 금리 (%)", value=st.session_state['market_rates']['KRW']*100, format="%.2f") / 100
                r_usd = st.number_input("미국 금리 (%)", value=st.session_state['market_rates']['USD']*100, format="%.2f") / 100

            st.subheader("🚩 위험 분석 설정")
            with st.container(border=True):
                budget_rate = st.number_input(
                    "예산 환율 (Budget Line)", 
                    value=st.session_state.get('budget_rate', 1350.0), 
                    step=1.0
                )
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
                
                # 1. 히스토그램 본체 (범례 제외)
                fig_hist.add_trace(go.Histogram(
                    x=ending_prices, 
                    nbinsx=50, 
                    marker_color='lightgray', 
                    opacity=0.7,
                    showlegend=False # 히스토그램 자체는 범례에서 제외
                ))
                
                # 2. 중앙값 선 (범례 표시)
                fig_hist.add_vline(
                    x=np.median(ending_prices), 
                    line_width=2, 
                    line_color="blue", 
                    name="중앙값(Median)" # 범례에 표시될 이름
                )
                # 범례 전용 가상 트레이스 (vline은 범례에 자동으로 안 잡히므로 추가)
                fig_hist.add_trace(go.Scatter(x=[None], y=[None], mode='lines', line=dict(color='blue', width=2), name='중앙값(Median)'))

                # 3. 예산 환율 선 (범례 표시)
                fig_hist.add_vline(
                    x=budget_rate, 
                    line_dash="dot", 
                    line_color="red", 
                    line_width=2,
                    name="예산 환율(Budget)"
                )
                fig_hist.add_trace(go.Scatter(x=[None], y=[None], mode='lines', line=dict(color='red', width=2, dash='dot'), name='예산 환율(Budget)'))

                # 4. 헤지 환율 선 (범례 표시)
                fig_hist.add_vline(
                    x=hedge_rate, 
                    line_dash="dash", 
                    line_color="green", 
                    line_width=2,
                    name="헤지 목표(Hedge)"
                )
                fig_hist.add_trace(go.Scatter(x=[None], y=[None], mode='lines', line=dict(color='green', width=2, dash='dash'), name='헤지 목표(Hedge)'))

                # 5. 레이아웃 설정 (범례 위치 및 이름표 제거)
                fig_hist.update_layout(
                    height=350, 
                    margin=dict(l=10, r=10, t=30, b=10),
                    legend=dict(
                        orientation="h",       # 가로 방향 범례
                        yanchor="bottom", 
                        y=1.02,                # 그래프 상단에 배치
                        xanchor="right", 
                        x=1
                    ),
                    xaxis_title="만기 환율 (₩)",
                    yaxis_title="빈도수"
                )
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
                    "분포 구간": f"하위 {p}%", "예측 환율": f"₩{price:,.2f}",
                    "환율 변동폭(원)": f"{diff:+,.2f} ({diff_pct:+.2f}%)",
                    "예산 환율과의 갭(원)": f"{price - budget_rate:+,.2f}",
                    "예상 평가손익(원)": pnl_str
                })
            st.table(pd.DataFrame(sensitivity_data))

            # --- 7. 헤지 성과 분석 (Hedge Performance Analysis) ---
            st.divider()
            st.subheader("🛡️ 헤지 성과 분석 (Hedge vs. Unhedged)")
            st.write("") # 빈 행 추가

            # 성과 분석을 위한 가상 시나리오 계산
            # 만기 환율이 중앙값(Median)일 때를 가정
            final_price = np.median(ending_prices)
            
            # 1) 헤지 안 했을 때 손익
            unhedged_pnl = (final_price - budget_rate) * total_usd_pv
            
            # 2) 100% 헤지 했을 때 손익 (헤지 환율로 고정)
            hedged_pnl = (hedge_rate - budget_rate) * total_usd_pv
            
            # 3) 헤지 효율성 (Hedge Effectiveness)
                        
            # (헤지 시 손익 - 미헤지 시 손익) / 예산 대비 노출액 절대값 등으로 환산
            # 여기서는 단순 손익 금액 차이의 비율을 보여줍니다.
            diff_pnl = hedged_pnl - unhedged_pnl
            
            # 개선율 계산 (분모가 0인 경우 대비)
            if unhedged_pnl != 0:
                perf_ratio = (diff_pnl / abs(unhedged_pnl)) * 100
            else:
                perf_ratio = 0.0

            if is_export:
                # 수출: 환율이 헤지환율보다 낮아지면 헤지가 잘한 것(개선), 높으면 기회손실
                if final_price < hedge_rate:
                    efficiency = f"{perf_ratio:+.1f}% 개선"
                else:
                    efficiency = f"{perf_ratio:+.1f}% 기회비용"
            else:
                # 수입: 환율이 헤지환율보다 높아지면 헤지가 잘한 것(개선), 낮으면 기회손실
                if final_price > hedge_rate:
                    efficiency = f"{perf_ratio:+.1f}% 개선"
                else:
                    efficiency = f"{perf_ratio:+.1f}% 기회비용"

            # 성과 지표 요약 (작은 폰트 스타일 유지)
            perf_col1, perf_col2, perf_col3 = st.columns(3)
            
            with perf_col1:
                st.metric("미헤지 시 예상 손익", f"₩{unhedged_pnl:,.0f}", delta=None)
                st.caption("만기 시점 시장환율(Median) 적용")

            with perf_col2:
                st.metric("헤지 실행 시 확정 손익", f"₩{hedged_pnl:,.0f}", delta="확정 손익", delta_color="off")
                st.caption(f"헤지 목표 환율(₩{hedge_rate:,.2f}) 적용")

            with perf_col3:
                st.metric("헤지 기대 효과", efficiency)
                st.caption("")

            # 추가 가이드 (Expander - 작은 폰트 적용됨)
            with st.expander("💡 헤지 성과 분석 활용 팁", expanded=False):
                st.markdown(f"""
                * **분석 취지**: 본 지표는 현재 설정한 헤지 환율(₩{hedge_rate:,.2f})로 모든 포지션을 헤지했을 때, 예산 환율 대비 손익 확정액을 보여줍니다.
                * **의사결정 가이드**: '헤지 기대 효과'가 음수(+)로 나타난다면, 헤지로 인한 기회 비용이 발생함을 의미합니다.
                * **주의**: 위 계산은 단순 만기 시점 환율 비교이며, 실제 시장 상황은 고려되지 않은 수치입니다.
                """)

    else:
        st.info("💡 분석할 데이터가 없습니다. 탭 1에서 데이터를 입력해 주세요.")

with tab4:
# --- [신규 추가] Tab 4 전용 폰트 스타일 ---
    st.markdown("""
        <style>
        /* 가이드 박스(container) 내부의 폰트 크기 조정 */
        [data-testid="stVerticalBlock"] .stMarkdown p {
            font-size: 13.5px !important;
            line-height: 1.6 !important;
            color: #444444 !important;
        }
        /* 불렛 포인트(리스트) 크기 조정 */
        [data-testid="stVerticalBlock"] .stMarkdown li {
            font-size: 13px !important;
            color: #444444 !important;
        }
        /* 섹션 내 작은 제목 크기 조정 */
        [data-testid="stVerticalBlock"] .stMarkdown h3 {
            font-size: 16px !important;
            color: #1F1F1F !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.header("📖 FX_RISK 시뮬레이터 이용 가이드")
    
    col_guide1, col_guide2 = st.columns(2)
    
    with col_guide1:
        with st.container(border=True):
            st.subheader("💡 주요 기능 안내")
            st.markdown("""
            1. **통합 포지션 관리**: 수출(Long)과 수입(Short) 포지션을 한곳에 입력하여 **실질적인 외화 노출액(Net Exposure)**을 산출합니다.
            2. **현가(PV) 분석**: 미래의 외화 금액을 단순히 합산하지 않고, 각 국가의 **무위험 금리를 반영하여 현재 가치**로 환산합니다.
            3. **몬테카를로 시뮬레이션**: 단편적인 선물 환율 전망이 아닌, **기하 브라운 운동(GBM)** 모델을 통해 10,000번 이상의 가상 경로를 생성하여 확률적 리스크를 분석합니다.
            """)
            
    with col_guide2:
        with st.container(border=True):
            st.subheader("🚀 체험하기 (Quick Start)")
            st.markdown("""
            * **STEP 1**: 왼쪽 사이드바의 **[체험하기]** 버튼을 눌러 예시 데이터를 불러오세요.
            * **STEP 2**: **[캐시플로우]** 탭에서 날짜별로 네팅된 현가 포지션을 확인합니다.
            * **STEP 3**: **[리스크 시뮬레이션]** 탭에서 시장 변동성과 예산 환율을 설정하여 우리 회사의 안전 구간을 확인하세요.
            """)

    st.divider()
    st.subheader("🔍 용어 설명")
    with st.expander("현가(Present Value) 할인이 왜 필요한가요?"):
        st.write("3개월 뒤의 100만 불과 오늘 당장의 100만 불은 금리 차이만큼 가치가 다릅니다. 이 시뮬레이터는 정확한 리스크 측정을 위해 모든 미래 현금흐름을 현재 가치로 할인하여 분석합니다.")
    
    with st.expander("몬테카를로 시뮬레이션의 결과는 어떻게 해석하나요?"):
        st.write("중앙값(Median)은 가장 확률 높은 미래 환율이며, 90% 신뢰구간(확률 구름)은 환율이 움직일 수 있는 극단적인 범위를 보여줍니다. 예산 환율 돌파 확률이 높다면 즉각적인 헤지 전략이 필요함을 시사합니다.")

    with st.expander("시장 변동성(Volatility)이란 무엇이며, 왜 설정해야 하나요?"):
        st.markdown("""
        **시장 변동성**은 환율이 일정 기간 동안 얼마나 위아래로 크게 움직이는지를 나타내는 지표입니다.
        
        * **리스크의 크기**: 변동성을 높게 설정할수록(예: 15% 이상) 시뮬레이션 결과의 '확률 구름'이 넓게 퍼집니다. 이는 미래 환율의 불확실성이 크다는 것을 의미하며, 예산 환율을 벗어날 위험도 함께 커집니다.
        * **시뮬레이션에서의 역할**: 본 시뮬레이터는 **기하 브라운 운동(GBM)** 모델을 사용합니다. 이때 변동성은 환율이 무작위로 움직이는 '진폭'을 결정하며, 10,000번의 시뮬레이션이 각기 다른 경로를 그리게 만드는 핵심 변수입니다.
        * **설정 팁**: 평상시에는 8~10% 내외를 사용하지만, 경제 위기나 금리 급변동기에는 15% 이상으로 설정하여 최악의 시나리오(Stress Test)를 점검하는 것이 좋습니다.
        """)