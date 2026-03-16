from src.client.gpt_client import GPTClient
from src.client.kakao_client import KakaoClient
from src.repository.user_repository import UserRepository
from src.repository.chat_session_repository import ChatSessionRepository
from src.repository.chat_state_repository import ChatStateRepository
from uuid import uuid4
from src.service.recommendation.weather_checker import WeatherChecker
from src.service.recommendation.state_checker import StateChecker
from src.service.recommendation.interviewer import Interviewer
from src.service.recommendation.final_reviewer import FinalReviewer
from src.service.recommendation.weight_assigner import WeightAssigner
from src.service.recommendation.location_resolver import LocationResolver
from src.schema.recommendation_schema import ChatResponse

class RecommendationService:
    def __init__(self):
        self.gpt_client = GPTClient()
        self.weather_checker = WeatherChecker()
        self.kakao_client = KakaoClient()

        self.state_checker = StateChecker(self.gpt_client)
        self.interviewer = Interviewer(self.gpt_client)
        self.final_reviewer = FinalReviewer(self.gpt_client)
        self.weight_assigner = WeightAssigner(self.gpt_client)
        self.location_resolver = LocationResolver(self.gpt_client, self.kakao_client)

    async def get_init_message(self, user_uuid: str, lat: float, lon: float) -> ChatResponse:
        """
        산책 경로 추천 챗봇의 초기 메시지를 반환합니다.
        """
        # 사용자의 chat_session 생성
        user_id = UserRepository.get_id_by_uuid(user_uuid)
        thread_id = str(uuid4())
        ChatSessionRepository.save(user_id, thread_id)

        # 날씨 정보 획득
        weather_data, init_message = await self.weather_checker.generate_init_message(lat, lon)

        # 초기 상태 정의
        initial_state = {
            "user_uuid": user_uuid,
            "lat": lat,
            "lon": lon,
            "origin_candidate": None,       # 출발지 후보군
            "destination_candidate": None,  # 목적지 후보군
            "user_context": {
                "is_circular": None,        # 순환 여부 (True: 순환, False: 편도)
                "origin": None,             # 출발지
                "destination": None,        # 목적지
                "purpose": None             # 산책 목적
            },
            "weather_data": weather_data,   # 실시간 기상 정보
            "is_confirmed": False,          # 요약된 산책 조건에 대한 유저의 최종 승인 여부
            "user_prompt": "",              # 유저 프롬프트

            # 워크플로우 상 다음 단계
            # - extraction: 정보 추출 | interview: 추가 질문 | selection: 출발지, 목적지 1택
            # - final_review: 요약 확인 | decision: 승인 판정   | weighting: 가중치 산출
            "next_node": "extraction"
        }

        # Valkey에 초기 상태 저장
        await ChatStateRepository.save_state(
            thread_id=thread_id,
            state=initial_state
        )

        return ChatResponse(
            thread_id=thread_id,
            message=init_message
        )
       
    async def orchestrator(self, thread_id: str, user_prompt: str):
        """
        산책 경로 추천 시스템 오케스트레이터입니다.
        """
        # StateChecker를 통해 상태 업데이트 및 다음 노드 결정
        state = await self.state_checker.update_and_check(thread_id, user_prompt)

        current_node = state.get("next_node")
        context = state.get("user_context")
        weather_data = state.get("weather_data")
        lat = state.get("lat")
        lon = state.get("lon")
        print(lat, lon)

        # 결정된 노드에 따라 서비스 호출
        # CASE 1: 정보가 더 필요할 때
        if current_node == "interview":
            message = await self.interviewer.get_next_question(context)
            state["next_node"] = "extraction"

        # CASE 2: 정보를 다 모은 후, 사용자에게 최종 점검을 받아야 할 때
        elif current_node == "final_review":
            message = await self.final_reviewer.generate_review_message(context)
            locations = await self.location_resolver.location_resolver(context, lat, lon)
            origin_location = locations.get("origin_location")
            destination_location = locations.get("destination_location")
            message += f"""
            출발지와 목적지의 정확한 위치를 확인해주세요! 이곳 중 원하는 장소를 말씀해주시면 산책 경로를 생성해드릴게요!
            출발지: {origin_location.get("place_name")}( {origin_location.get("place_address")} )
            목적지: {destination_location[0].get("place_name")}( {destination_location[0].get("place_address")} )
            """
            state["origin_candidate"] = origin_location  # 정확한 위치 데이터를 넣은 json 형식으로 출발지 업데이트
            state["destination_candidate"] = destination_location  # 정확한 위치 데이터를 넣은 json 형식으로 목적지 업데이트
            state["next_node"] = "decision"

        # CASE 3: 사용자가 만족해서 최종적으로 지도 레이어별 가중치를 결정해야 할 때
        elif current_node == "weighting":
            weights = await self.weight_assigner.get_feature_weights(context, weather_data)
            message = f"모든 분석이 완료되었습니다! 가중치는 {weights}입니다."
        
        # state 업데이트
        await ChatStateRepository.save_state(thread_id, state)
        
        return ChatResponse(
            thread_id=thread_id,
            message=message
        )