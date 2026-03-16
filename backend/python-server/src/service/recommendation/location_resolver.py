from langchain_core.output_parsers import JsonOutputParser
import asyncio

class LocationResolver:
    def __init__(self, gpt_client, kakao_client):
        self.gpt_client = gpt_client
        self.kakao_client = kakao_client
        self.parser = JsonOutputParser()

    async def get_response(self, location_text: str):
        """
        사용자의 응답을 기반으로 정확한 위치를 파악하기 위해 어떤 인자를 가지고 어떤 함수를 호출해야 하는지 파악합니다.
        """
        return await self.gpt_client.get_response(
            prompt_name="function_calling",
            input_data={
                "location_text": location_text,
                "format_instructions": self.parser.get_format_instructions()
            },
            output_parser=self.parser
        )
    
    async def get_place_info(self, function, query: str, lat: float, lon: float):
        """
        kakao api를 기반으로 출발지와 목적지의 정확한 위치를 파악합니다.
        """
        print(function, query)
        response = await function(query, lat, lon)
        documents = response.get("documents")
        MAX_RANGE = min(3, len(documents))

        results = []
        for i in range(MAX_RANGE):
            results.append({
                "place_address": documents[i].get("address_name"),
                "place_name": documents[i].get("place_name"),
                "place_lat": documents[i].get("y"),
                "place_lon": documents[i].get("x")
            })

        return results

    async def location_resolver(self, context: dict, lat: float, lon: float):
        """
        수집된 정보를 기반으로 출발지와 목적지의 정확한 위치를 파악합니다.
        """
        is_circular = context.get("is_circular")
        origin = context.get("origin")
        destination = origin if is_circular else context.get("destination")

        # 순환
        if is_circular:
            origin_location = await self.get_response(origin)
        # 편도
        else:
            origin_location, destination_location = await asyncio.gather(
                self.get_response(origin),
                self.get_response(destination)
            )

        # 정확한 위치를 알아내기 위해 호출해야 하는 함수 목록
        function_map = {
            "get_address_from_keyword": self.kakao_client.get_address_from_keyword,
            "get_address_from_category": self.kakao_client.get_address_from_category
        }

        # 함수 매핑
        origin_function = function_map.get(origin_location.get("function"))
        origin_query = origin_location.get("query")
        if not is_circular:
            destination_function = function_map.get(destination_location.get("function"))
            destination_query = destination_location.get("query")

        # 출발지가 현 지점인 경우
        is_here = origin_location.get("is_here")

        print(origin_location)
        print(destination_location)

        # 순환 & 출발지가 현 지점인 경우
        if is_circular and is_here:
            origin_location = await self.kakao_client.get_address_from_coords(lat, lon)
            destination_location = origin_location
        # 순환 & 출발지가 다른 장소인 경우
        elif is_circular and not is_here:
            origin_location = await self.get_place_info(origin_function, origin_query, lat, lon)
            destination_location = origin_location
        # 편도 & 출발지가 현 지점인 경우
        elif not is_circular and is_here:
            origin_location, destination_location = await asyncio.gather(
                self.kakao_client.get_address_from_coords(lat, lon),
                self.get_place_info(destination_function, destination_query, lat, lon)
            )
        # 편도 & 출발지가 다른 장소인 경우
        else:
            origin_location, destination_location = await asyncio.gather(
                self.get_place_info(origin_function, origin_query, lat, lon),
                self.get_place_info(destination_function, destination_query, lat, lon)
            )

        return {
            "is_circular": is_circular,
            "origin_location": origin_location,
            "destination_location": destination_location
        }
    
"""
{
    'is_circular': False,
    'origin_location': {'place_address': '경기 고양시 덕양구 화정동 1098', 'place_name': '현 위치', 'place_lat': 37.6346, 'place_lon': 126.8328},
    'destination_location': [
        {'place_address': '경기 고양시 덕양구 화정동 973', 'place_name': '스타벅스 화정역', 'place_lat': '37.6334117518072', 'place_lon': '126.832895109647'},
        {'place_address': '경기 고양시 덕양구 화정 동 970-5', 'place_name': '스타벅스 화정점', 'place_lat': '37.6334855139605', 'place_lon': '126.831544510036'},
        {'place_address': '경기 고양시 덕양구 화정동 689-19', 'place_name': '스타벅스 화 정호국로점', 'place_lat': '37.64177535211692', 'place_lon': '126.82958149505166'}
    ]
}
"""