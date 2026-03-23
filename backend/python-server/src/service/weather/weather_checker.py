from src.client.weather_client import WeatherClient
from typing import Dict, Tuple, Any
import textwrap

class WeatherChecker:
    def __init__(self):
        self.weather_client = WeatherClient()
        self.init_message = textwrap.dedent("""
            현재 위치를 중심으로 최적의 산책로를 추천해 드릴게요.
            원하시는 산책 조건을 말씀해 주시겠어요?
            1. 코스 종류: 순환 vs 편도
            2. 도착 지점: (편도 선택 시) 목적지 명칭
            3. 산책 테마: 운동, 데이트, 반려동물 동반 등
        """).strip()

    async def check_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        날씨를 검색합니다.
        """
        return await self.weather_client.get_weather(lat, lon)
    
    def get_weather_message(self, weather_item: Dict[str, Any]) -> str:
        """
        날씨별 적절한 메시지를 생성합니다. 
        """
        # https://openweathermap.org/weather-conditions

        messages = {
            # 2xx: Thunderstorm (천둥번개)
            "Thunderstorm": "천둥번개가 치고 있어요. ⚡ 안전을 위해 외출을 자제해 주세요.",
    
            # 3xx: Drizzle (이슬비)
            "Drizzle": "부슬부슬 이슬비가 내립니다. 🌧️ 가벼운 우산이 필요할 것 같아요.",
    
            # 5xx: Rain (비)
            500: "가벼운 비가 내리고 있어요. 🌦️ 작은 우산을 챙기세요.",
            501: "보통 수준의 비가 옵니다. ☔ 우산 꼭 챙겨서 나가세요.",
            502: "비가 세차게 내리고 있어요. 🌊 가급적 실내에 머무르시는 건 어떨까요?",
            503: "매우 강한 비가 쏟아집니다. 🚫 외출 시 주의가 필요해요.",
            504: "기기묘묘한 폭우가 내립니다. ⚠️ 안전에 유의하세요.",
            511: "차가운 어는 비가 내려요. ❄️ 길이 매우 미끄러우니 조심하세요!",
            "Rain": "비가 내리고 있습니다. ☔ 우산을 챙겨주세요.", # 기본 비 메시지

            # 6xx: Snow (눈)
            600: "가벼운 눈이 날리고 있어요. ❄️ 포근한 산책이 되겠네요.",
            601: "눈이 내리고 있습니다. ☃️ 길이 미끄러울 수 있으니 발밑을 조심하세요.",
            602: "눈이 많이 쌓이고 있어요. 🌨️ 따뜻하게 입고 나가세요!",
            "Snow": "하얀 눈이 내리고 있네요. ❄️ 안전 산책하세요!",

            # 7xx: Atmosphere (대기 상태 - 문자열로 들어옴)
            "Mist": "안개가 끼어 시야가 흐릿해요. 🌫️ 천천히 걸어보세요.",
            "Smoke": "연기가 자욱합니다. 🌫️ 호흡기 건강에 유의하세요.",
            "Haze": "실안개(연무)가 끼어 있어요. 🌫️ 차분한 분위기의 산책이 되겠네요.",
            "Dust": "먼지가 바람에 날리고 있어요. 😷 마스크를 꼭 착용하세요.",
            "Fog": "짙은 안개로 시야가 좋지 않습니다. 🌫️ 평소보다 주의해서 걸으세요.",
            "Sand": "모래바람이 불고 있습니다. 🏜️ 눈과 호흡기를 보호하세요.",
            "Ash": "화산재가 날리고 있습니다. 🌋 가급적 외출을 피하세요.",
            "Squall": "갑작스러운 돌풍(스콜)이 붑니다. 🌬️ 소지품을 잘 챙기세요!",
            "Tornado": "토네이도 경보! 🌪️ 즉시 안전한 곳으로 대피하세요.",

            # 800: Clear (맑음)
            "Clear": "날씨가 매우 맑습니다. ☀️ 기분 좋게 산책하기 딱 좋은 날이에요.",

            # 80x: Clouds (구름)
            801: "구름이 조금 있네요. 🌤️ 걷기 딱 적당한 날씨입니다.",
            802: "구름이 흩어져 있는 흐린 날씨입니다. ☁️",
            803: "구름이 많이 끼어 있습니다. ☁️ 햇볕이 없어 걷기엔 편할 거예요.",
            804: "하늘이 온통 흐립니다. ☁️ 차분하게 산책을 즐겨보세요.",
            "Clouds": "구름이 낀 날씨입니다. ☁️"
        }

        weather_id = weather_item.get("id")
        weather_main = weather_item.get("main")

        if weather_id in messages:
            return messages[weather_id]
        return messages.get(weather_main, "산책하기 참 쾌적한 날씨입니다. 🌿")
    
    async def generate_init_message(self, lat: float, lon: float) -> Tuple[dict, str]:
        """
        초기 메시지를 조립하여 반환합니다.
        """
        # 날씨 검색
        weather_data = await self.check_weather(lat, lon)
        condition = weather_data["weather"][0]

        # 문구 생성
        weather_desc = self.get_weather_message(condition)

        return weather_data, f"{weather_desc}\n\n{self.init_message}"