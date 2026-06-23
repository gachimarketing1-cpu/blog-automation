import base64
import time

from google import genai
from google.genai import types

WORKING_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
]


def get_available_models(api_key: str) -> list[str]:
    return WORKING_MODELS


def _generate_with_fallback(client, models: list[str], **kwargs) -> str:
    last_err = None
    for model in models:
        try:
            return client.models.generate_content(model=model, **kwargs).text
        except Exception as e:
            last_err = e
            time.sleep(1)
    raise last_err


def analyze_photos(photo_data: list, api_key: str, model: str) -> str:
    client = genai.Client(api_key=api_key)

    parts = []
    for i, photo in enumerate(photo_data[:10], 1):
        parts.append(types.Part.from_bytes(
            data=base64.b64decode(photo["data"]),
            mime_type=photo["media_type"],
        ))
        parts.append(f"[사진 {i}번]")

    parts.append(
        "위 사진들을 번호 순서대로 분석해주세요. 각 사진에 대해:\n"
        "- 어떤 메뉴나 음식인지\n"
        "- 외관, 색감, 플레이팅\n"
        "- 분위기나 공간 (해당되는 경우)\n"
        "- 블로그 글에 활용할 만한 특이사항\n\n"
        "블로그 글 작성에 바로 활용할 수 있도록 구체적이고 생생하게 묘사해주세요."
    )

    models = [model] + [m for m in WORKING_MODELS if m != model]
    return _generate_with_fallback(client, models, contents=parts)


def generate_blog_post(
    restaurant_name: str,
    title: str,
    keywords: str,
    tags: str,
    restaurant_info: str,
    photo_analysis: str,
    writing_style: str,
    draft_notes: str,
    api_key: str,
    model: str,
) -> str:
    client = genai.Client(api_key=api_key)

    system_prompt = """당신은 대한민국 최고의 맛집 블로그 전문 작가입니다.
2026년 네이버 D.I.A+(다이아플러스) 알고리즘과 C-Rank에 최적화된 블로그 글을 작성합니다.

## 핵심 원칙
- 직접 방문한 것처럼 생생하고 구체적으로 작성
- 맛, 식감, 향, 서비스, 분위기를 구체적으로 묘사
- 핵심 키워드를 자연스럽게 5회 내외 배치 (제목, 첫 문단, 소제목, 결론)
- 실용 정보(주소, 영업시간, 주차, 가격)를 구조화해서 상단 배치
- 각 섹션마다 소제목 사용
- 해시태그는 본문 맨 끝에 10개 이내
- 글 길이: 2,500~3,500자
- 사진 위치는 <사진 N> 태그로 표시"""

    user_prompt = f"""다음 정보를 바탕으로 네이버 블로그 포스팅을 작성해주세요.

## 입력 정보
- 식당명: {restaurant_name}
- 제목: {title or restaurant_name + " 맛집 리뷰"}
- 핵심 키워드: {keywords or restaurant_name}
- 태그: {tags}

## 검색된 식당 정보
{restaurant_info or "검색 정보 없음 (식당명 기반으로 작성해주세요)"}

## 사진 분석
{photo_analysis or "사진 없음"}

## 문체/스타일
{writing_style or "편안하고 친근한 말투, '요/어요' 체, 여행 중 방문한 경험 위주"}

## 초안/메모
{draft_notes or "없음"}

---
완성된 네이버 블로그 포스팅을 작성해주세요."""

    models = [model] + [m for m in WORKING_MODELS if m != model]
    return _generate_with_fallback(
        client,
        models,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
        contents=user_prompt,
    )
