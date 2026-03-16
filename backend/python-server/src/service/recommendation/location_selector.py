# from langchain_core.output_parsers import JsonOutputParser
# from typing import List

# class LocationSelector:
#     def __init__(self, gpt_client):
#         self.gpt_client = gpt_client
#         self.parser = JsonOutputParser()
    
#     async def get_response(
#         self,
#         user_prompt: str,
#         context: dict,
#         origin_candidate: 
#     ):
#         """
#         사용자 답변을 기반으로 출발지와 목적지를 선택합니다.
#         """
#         question = await self.gpt_client.get_response(
#             prompt_name="select_location",
#             input_data={
#                 "context": context,
#             },
#             output_parser=self.parser
#             # "user_prompt", "context", "origin_candidate", "destination_candidate", "format_instructions"
#         )

#         return question