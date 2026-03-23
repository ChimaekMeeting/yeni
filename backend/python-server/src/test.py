import sys
import os
from dotenv import load_dotenv
import asyncio
import time
import json

# 1. 경로 설정 (ModuleNotFoundError 방지)
current_path = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_path, ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

import streamlit as st
import httpx
import osmnx as ox
import h3
import folium
from streamlit_folium import st_folium
import redis.asyncio as redis # 비동기 Redis/Valkey 라이브러리

load_dotenv()

# --- 설정 ---
BACKEND_URL = "http://localhost:8080/api"

# --- 헬퍼 함수: 비동기 루프 충돌 방지 ---
def run_async(coro):
    """Streamlit 리런 시 발생하는 루프 충돌을 방지하며 비동기 함수 실행"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# --- [핵심] Valkey 상태 직접 조회 (루프 격리형) ---
async def safe_get_state(thread_id):
    """
    함수 호출 시마다 새로운 연결을 맺고 닫아 'Different Loop' 에러를 원천 차단합니다.
    """
    # 1. 함수 내부에서 직접 클라이언트 생성
    VALKEY_URI = os.getenv("VALKEY_URI")
    client = redis.from_url(
        VALKEY_URI,
        decode_responses=True, 
        ssl_cert_reqs=None
    )
    try:
        key = f"chat_state:{thread_id}"
        data = await client.get(key)
        return json.loads(data) if data else None
    finally:
        # 2. 반드시 연결을 명시적으로 닫아줌 (중요!)
        await client.aclose()

# --- 지도 시각화 엔진 (OSMnx + H3) ---
def render_route_map(origin_coord, dest_coord):
    try:
        orig = (origin_coord['lat'], origin_coord['lon'])
        dest = (dest_coord['lat'], dest_coord['lon'])

        # 두 지점의 중앙점 계산 및 도로망 로드
        center_lat, center_lon = (orig[0] + dest[0]) / 2, (orig[1] + dest[1]) / 2
        graph = ox.graph_from_point((center_lat, center_lon), dist=1500, network_type='walk')

        # 최단 경로 탐색
        orig_node = ox.nearest_nodes(graph, orig[1], orig[0])
        dest_node = ox.nearest_nodes(graph, dest[1], dest[0])
        route = ox.shortest_path(graph, orig_node, dest_node, weight='length')
        
        # 좌표 및 H3 격자 변환
        route_coords = [(graph.nodes[node]['y'], graph.nodes[node]['x']) for node in route]
        h3_cells = list(set([h3.latlng_to_cell(lat, lng, 10) for lat, lng in route_coords]))

        # Folium 지도 생성
        m = folium.Map(location=orig, zoom_start=15, tiles="cartodbpositron")
        
        # H3 레이어 추가
        for cell in h3_cells:
            folium.Polygon(
                locations=h3.cell_to_boundary(cell),
                fill=True, fill_color='#3498db', color='#2980b9', fill_opacity=0.2, weight=1
            ).add_to(m)

        # 경로 및 마커 추가
        folium.PolyLine(route_coords, color="#e74c3c", weight=4).add_to(m)
        folium.Marker(orig, icon=folium.Icon(color='green', icon='play')).add_to(m)
        folium.Marker(dest, icon=folium.Icon(color='red', icon='flag')).add_to(m)
        
        return m
    except Exception as e:
        st.error(f"지도 생성 실패: {e}")
        return None

# --- API 통신 함수 (타임아웃 연장) ---
async def call_api(endpoint, payload=None):
    # 백엔드 연산 시간을 고려하여 timeout을 60초로 넉넉하게 설정
    async with httpx.AsyncClient(timeout=60.0) as client:
        if payload:
            response = await client.post(f"{BACKEND_URL}{endpoint}", json=payload)
        else:
            response = await client.post(f"{BACKEND_URL}{endpoint}")
        return response.json()

# --- 세션 초기화 및 메인 UI ---
st.set_page_config(page_title="산책 경로 추천", page_icon="🏃", layout="wide")

if "initialized" not in st.session_state:
    st.session_state.update({"initialized": False, "messages": [], "thread_id": None})

if not st.session_state.initialized:
    with st.status("🚀 서비스 초기화 중...") as s:
        user_data = run_async(call_api("/user/init"))
        u_uuid = user_data.get("user_uuid")
        if u_uuid:
            # 기본 위치(고양시)로 초기화
            init_data = run_async(call_api("/prewalk/init", {"user_uuid": u_uuid, "lat": 37.634496, "lon": 126.832852}))
            st.session_state.thread_id = init_data.get("thread_id")
            st.session_state.messages.append({"role": "assistant", "content": init_data.get("message")})
            st.session_state.initialized = True
            s.update(label="✅ 준비 완료!", state="complete")
            st.rerun()

st.title("🏃 실시간 산책 경로 추천")

# 채팅 로그 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("map_obj"):
            st_folium(msg["map_obj"], width=800, height=450, key=f"hist_{hash(msg['content'])}")

# 사용자 입력 처리
if prompt := st.chat_input("어디로 산책하고 싶으신가요?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        with st.spinner("백엔드 분석 중..."):
            # 1. 의도 분석 API 호출
            api_res = run_async(call_api("/prewalk/intent", {"thread_id": st.session_state.thread_id, "user_prompt": prompt}))
            resp_text = api_res.get("message", "응답 지연 중...")
            placeholder.markdown(resp_text)

            # 2. Valkey에서 실시간 State 직접 획득 (중요)
            state = run_async(safe_get_state(st.session_state.thread_id))
            
            # Valkey 데이터가 없으면 API 응답 본문에서 fallback
            active_data = state if state else api_res
            next_node = active_data.get("next_node")
            user_ctx = active_data.get("user_context", {})

            # 3. 종료 노드일 경우 지도 생성
            current_map = None
            if next_node == "end":
                st.divider()
                origin = user_ctx.get("origin", {}).get("coordinate")
                dest = user_ctx.get("destination", {}).get("coordinate")

                if origin and dest:
                    with st.status("🗺️ 경로 최적화 및 지도 생성 중..."):
                        current_map = render_route_map(origin, dest)
                        if current_map:
                            st_folium(current_map, width=900, height=500, key=f"end_{int(time.time())}")
                else:
                    st.warning("경로 좌표 데이터가 부족합니다.")

    st.session_state.messages.append({"role": "assistant", "content": resp_text, "map_obj": current_map})