import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static  # 렌더링 최적화를 위해 변경
import os

# 페이지 설정
st.set_page_config(page_title="지진 위험도 예측 및 시각화", layout="wide")

st.title("🌍 지진 위험도 예측 및 위치 시각화 서비스")
st.markdown("위도와 경도를 입력하여 주변의 지진 데이터를 분석하고 위험도를 예측합니다.")

# 위험도 사전 및 색상 정의
risk_dict = {0: '높음', 1: '낮음', 2: '중간'}
colors = {0: 'red', 1: 'blue', 2: 'green'}

# 대용량 데이터 로드 캐싱 처리 및 가벼운 샘플 미리 추출
@st.cache_data
def load_data():
    if os.path.exists('earthquakes.csv'):
        df = pd.read_csv('earthquakes.csv')
        
        # 지도 시각화용 5000개 샘플을 로딩 시점에 딱 한 번만 미리 뽑아둡니다 (속도 대폭 향상)
        sample_size = min(5000, len(df))
        df_sample = df.sample(sample_size, random_state=42)
        
        return df, df_sample
    else:
        st.error("데이터 파일(earthquakes.csv)을 찾을 수 없습니다. 경로를 확인해주세요.")
        return None, None

df_new, df_sample = load_data()

if df_new is not None:
    # 좌측 입력창 / 우측 결과창 분할 레이아웃
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📍 위치 입력")
        
        # Session State가 아닌 일반 number_input으로도 렉 없이 작동하도록 구조 변경
        lat = st.number_input("위도 입력 (-90.0 ~ 90.0)", min_value=-90.0, max_value=90.0, value=37.5, step=0.1)
        lon = st.number_input("경도 입력 (-180.0 ~ 180.0)", min_value=-180.0, max_value=180.0, value=127.0, step=0.1)
        
        predict_button = st.button("위험도 예측 및 지도 표시", type="primary")
            
    with col2:
        st.subheader("📊 분석 결과 및 지도 시각화")
        
        # 버튼을 누른 순간에만 무거운 연산이 실행되도록 제한하여 평소 입력 렉을 제거
        if predict_button:
            try:
                # 1. 주변 지진 검색 (경계 조건 최적화)
                near_df = df_new[
                    (df_new['위도'] >= lat - 5) & (df_new['위도'] <= lat + 5) & 
                    (df_new['경도'] >= lon - 5) & (df_new['경도'] <= lon + 5)
                ]
                
                if not near_df.empty and 'cluster' in near_df.columns:
                    cluster_ratio = near_df['cluster'].value_counts(normalize=True)
                    main_cluster = cluster_ratio.idxmax()
                    risk_level = risk_dict[main_cluster]
                    
                    if main_cluster == 0:
                        st.error(f"🚨 **위험도 결과: {risk_level}** (주변에 위험 군집 발생 빈도가 높습니다.)")
                    elif main_cluster == 2:
                        st.warning(f"⚠️ **위험도 결과: {risk_level}** (주변에 중간 수준의 위험 군집이 존재합니다.)")
                    else:
                        st.success(f"✅ **위험도 결과: {risk_level}** (주변 위험도가 비교적 낮습니다.)")
                        
                    st.write("**주변 군집 세부 비율:**")
                    for c_idx, ratio in cluster_ratio.items():
                        st.write(f"- {risk_dict[c_idx]} (군집 {c_idx}): {ratio*100:.1f}%")
                else:
                    st.info("ℹ️ 입력하신 위치 주변(±5도)에 기존 지진 데이터(또는 cluster 정보)가 없습니다.")
            
            except KeyError as e:
                st.error(f"⚠️ 컬럼명 오류 발생: {e}. 'earthquakes.csv' 내부의 실제 컬럼명이 '위도', '경도', 'cluster' 인지 확인해주세요.")
            
            # 2. 지도 생성 (입력된 위치 중심)
            m = folium.Map(location=[lat, lon], zoom_start=4)
            
            # 캐싱된 샘플 데이터를 사용하여 루프 속도 최적화
            if 'cluster' in df_sample.columns:
                for idx, row in df_sample.iterrows():
                    cluster = row['cluster']
                    if cluster in colors:
                        folium.CircleMarker(
                            location=[row['위도'], row['경도']],
                            radius=3,
                            color=colors[cluster],
                            fill=True,
                            fill_color=colors[cluster]
                        ).add_to(m)
                
            # 사용자가 입력한 위치에 검은색 별 모양 마커 추가
            folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color='black', icon='star', icon_color='white'),
                popup=f"입력 위치 ({lat}, {lon})"
            ).add_to(m)
            
            # 3. 고속 정적 렌더러 사용 (화면 흐려짐 및 먹통 현상 해결의 핵심)
            folium_static(m, width=800, height=500)
        else:
            st.info("👈 좌측에서 위도와 경도를 입력한 후 버튼을 눌러주세요.")
