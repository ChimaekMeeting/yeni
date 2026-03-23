### 개요
사용자의 현재 상황(위치, 기상 정보)과 개인적 취향을 반영한 지능형 산책 경로 추천 서비스입니다. 단순한 경로 안내를 넘어, LLM(GPT-4o-mini)이 사용자와 대화하며 최적의 산책 조건을 도출합니다.

### 파일트리
```
.
├── README.md
├── requirements.txt
└── src
    ├── api
    │   ├── prewalk.py
    │   └── user.py
    ├── client
    │   ├── gpt_client.py
    │   ├── kakao_client.py
    │   └── weather_client.py
    ├── database
    │   ├── postgresql.py
    │   └── valkey.py
    ├── entity
    │   ├── base.py
    │   ├── chat_session.py
    │   ├── user.py
    │   └── user_preference_context.py
    ├── prompt
    │   ├── extraction.yaml
    │   ├── interview.yaml
    │   ├── location_routing.yaml
    │   ├── location_selection.yaml
    │   ├── map_generation.yaml
    │   ├── plan_routing.yaml
    │   ├── plan_summarization.yaml
    │   └── weight_assign.yaml
    ├── repository
    │   ├── chat_session_repository.py
    │   ├── chat_state_repository.py
    │   ├── user_preference_context_repository.py
    │   └── user_repository.py
    ├── schema
    │   ├── prewalk_schema.py
    │   └── user_schema.py
    ├── service
    │   ├── common
    │   │   └── string_converter.py
    │   ├── core
    │   │   └── state_checker.py
    │   ├── map
    │   ├── node
    │   │   ├── interviewer.py
    │   │   ├── location_searcher.py
    │   │   ├── plan_summarizer.py
    │   │   └── weight_assigner.py
    │   ├── prewalk_orchestrator.py
    │   ├── router                                                                                                     
    │   │   ├── location_router.py
    │   │   └── plan_router.py
    │   ├── user_service.py
    │   └── weather
    │       └── weather_checker.py
    ├── main.py
    └── test.py
```

### 실행 방법
```
# python-server 폴더로 접근
cd backend
cd python-server

# 가상환경 실행
python -m venv .venv
source .venv/Scripts/activate

# 라이브러리 설치
pip install --upgrade pip
pip install -r requirements.txt

# 코드 실행
python -m src.main

# swagger-ui url
http://127.0.0.1:8000/docs
```

### api 설명
| 분류 | 기능 | 메서드 | 엔드포인트 | 설명 |
| :---: | :---: | :---: | :---: | :---: |
| User | 사용자 초기화 | POST | `/api/user/init` | 유저 생성 및 초기 세션 설정 |
| Recommendation | 대화 시작 | POST | `/api/recommendation/init` | 날씨 기반 초기 인사말 및 상태 생성 |
| Recommendation | 대화 진행 | POST | `/api/recommendation/intent` | 유저 의도 분석 및 단계별 응답 반환 |
