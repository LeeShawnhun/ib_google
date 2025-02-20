from dataclasses import Field
import json
import re
from pydantic import BaseModel, Field
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.customaudience import CustomAudience

class SeedRequest(BaseModel):
    access_token: str
    account_id: int
    campaign_id: int
    seed_name: str
    country_code: str = Field(default="KR", min_length=2, max_length=2)
    ratio: float = Field(default=0.1, ge=0.01, le=0.1)

def extract_error_message(e):
    try:
        if hasattr(e, 'api_error_message'):
            # api_error_message 메서드 호출
            error_msg = e.api_error_message()

            print(error_msg)
            
            return error_msg
    
    except Exception as decode_error:
        print(f"디코딩 오류: {decode_error}")  # 디버깅용
        return f"오류 메시지 처리 중 문제가 발생했습니다: {str(e)}"

    # 디버깅을 위한 테스트 코드
    except Exception as e:
        if hasattr(e, 'api_error_message'):
            error_msg = e.api_error_message()  # 메서드 호출
            print("Error message:", error_msg)
            print("Type:", type(error_msg))
            
            error_message = extract_error_message(e)
            print("Extracted message:", error_message)

# 유사 타겟 생성
def create_lookalike_audience(access_token, seed_name, ad_account_id, campaign_id, ratio=0.10, country = "KR"):

    status = ""

    try:
        FacebookAdsApi.init(access_token=access_token)

        lookalike = CustomAudience(parent_id=f'act_{ad_account_id}')
        lookalike.update({
            CustomAudience.Field.name: f'{seed_name}',
            CustomAudience.Field.subtype: CustomAudience.Subtype.lookalike,
            CustomAudience.Field.lookalike_spec: {
                'origin_ids': [campaign_id],
                'starting_ratio': 0.00,
                'ratio': ratio,
                'conversion_type': 'campaign_conversions',
                'country': country
            },
        })

        # remote_create() 호출 추가
        lookalike.remote_create()

        # ID 확인
        if hasattr(lookalike, 'get_id'):
            audience_id = lookalike.get_id()
            if audience_id:
                status = f"유사 타겟 생성 완료! ID: {audience_id}"            
            
        else:    
            status = "유사 타겟 생성 실패: ID를 받지 못했습니다"

        return status

    except Exception as e:
        if hasattr(e, 'api_error_message'):
            status = extract_error_message(e)

        return status

