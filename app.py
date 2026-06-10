import base64
import os
import subprocess
import sys

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


@st.cache_resource(show_spinner=False)
def _install_playwright_browser():
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True,
    )


_install_playwright_browser()

from core.claude_client import analyze_photos, generate_blog_post
from core.naver_uploader import post_to_naver
from core.search import search_restaurant_info

st.set_page_config(page_title="맛집 블로그 자동화", layout="wide", page_icon="🍽️")

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .stTextArea textarea { font-size: 14px; line-height: 1.7; }
    h1 { font-size: 26px !important; }
</style>
""", unsafe_allow_html=True)

st.title("🍽️ 맛집 블로그 자동화")
st.caption("식당명 + 사진 → SEO 최적화 네이버 블로그 글 자동 생성 + 업로드")

# --- Sidebar: Settings ---
with st.sidebar:
    st.header("⚙️ 설정")

    with st.expander("🔑 API 키", expanded=True):
        api_key = st.text_input(
            "Anthropic API Key",
            value=os.getenv("ANTHROPIC_API_KEY", ""),
            type="password",
            help="console.anthropic.com 에서 발급",
        )

    with st.expander("📝 네이버 계정"):
        naver_id = st.text_input("네이버 ID", value=os.getenv("NAVER_ID", ""))
        naver_pw = st.text_input(
            "네이버 비밀번호", value=os.getenv("NAVER_PW", ""), type="password"
        )

    if st.button("✅ 확인", use_container_width=True):
        st.success("이 세션에서 적용됩니다.")

    st.divider()
    st.markdown("**사용법**")
    st.markdown(
        "1. API 키 입력 후 저장\n"
        "2. 식당명·사진·키워드 입력\n"
        "3. 글 생성 버튼 클릭\n"
        "4. 결과 확인 후 네이버 업로드"
    )

# --- Session state ---
if "generated_post" not in st.session_state:
    st.session_state.generated_post = ""
if "photo_analysis" not in st.session_state:
    st.session_state.photo_analysis = ""

# --- Main layout ---
left, right = st.columns([1, 1], gap="large")

with left:
    st.subheader("📝 입력")

    restaurant_name = st.text_input("식당명 *", placeholder="예: 제주 성산갈치맛집")
    title = st.text_input("제목 *", placeholder="블로그 포스팅 제목을 입력하세요")

    col_kw, col_tag = st.columns(2)
    with col_kw:
        keywords = st.text_input("핵심 키워드", placeholder="예: 성산일출봉 아침식사")
    with col_tag:
        tags = st.text_input("태그 (쉼표 구분)", placeholder="예: 제주맛집, 성산갈치")

    photos = st.file_uploader(
        "📸 사진 업로드 (여러 장 가능)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
    )

    if photos:
        preview_cols = st.columns(min(len(photos), 4))
        for col, photo in zip(preview_cols, photos[:4]):
            col.image(photo, use_column_width=True)
        if len(photos) > 4:
            st.caption(f"+ {len(photos) - 4}장 더 업로드됨")

    writing_style = st.text_area(
        "✍️ 글 문체/스타일",
        placeholder=(
            "예: 편안하고 친근한 말투, '요/어요' 체,\n"
            "여행 중 직접 방문한 경험 위주로 자연스럽게..."
        ),
        height=80,
    )

    draft_notes = st.text_area(
        "📋 초안 메모 (선택)",
        placeholder="방문 메모나 초안 내용을 붙여넣으세요. 비워두면 AI가 전부 작성합니다.",
        height=220,
    )

    generate_btn = st.button(
        "✨ 블로그 글 생성하기", type="primary", use_container_width=True
    )

with right:
    st.subheader("🤖 생성 결과")

    if generate_btn:
        if not restaurant_name:
            st.error("식당명을 입력해주세요.")
        elif not api_key:
            st.error("사이드바에서 Anthropic API Key를 입력해주세요.")
        else:
            status = st.status("작업 진행 중...", expanded=True)

            with status:
                st.write("🔍 식당 정보 검색 중...")
                restaurant_info = search_restaurant_info(restaurant_name)

                photo_analysis = ""
                if photos:
                    st.write(f"📸 사진 {len(photos)}장 분석 중...")
                    photo_data = []
                    for photo in photos:
                        raw = photo.read()
                        photo.seek(0)
                        media_type = photo.type if photo.type else "image/jpeg"
                        if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
                            media_type = "image/jpeg"
                        photo_data.append(
                            {
                                "name": photo.name,
                                "data": base64.b64encode(raw).decode(),
                                "media_type": media_type,
                            }
                        )
                    photo_analysis = analyze_photos(photo_data, api_key)
                    st.session_state.photo_analysis = photo_analysis

                st.write("✍️ SEO 최적화 블로그 글 작성 중...")
                post = generate_blog_post(
                    restaurant_name=restaurant_name,
                    title=title,
                    keywords=keywords,
                    tags=tags,
                    restaurant_info=restaurant_info,
                    photo_analysis=photo_analysis,
                    writing_style=writing_style,
                    draft_notes=draft_notes,
                    api_key=api_key,
                )
                st.session_state.generated_post = post
                status.update(label="✅ 생성 완료!", state="complete")

    if st.session_state.photo_analysis:
        with st.expander("📸 사진 분석 결과 보기"):
            st.text(st.session_state.photo_analysis)

    generated = st.text_area(
        "생성된 블로그 글 (직접 수정 가능)",
        value=st.session_state.generated_post,
        height=460,
        placeholder=(
            "왼쪽에서 정보를 입력하고\n"
            "'블로그 글 생성하기' 버튼을 누르면\n"
            "여기에 완성된 글이 나타납니다."
        ),
        key="post_editor",
    )

    if generated != st.session_state.generated_post:
        st.session_state.generated_post = generated

    st.divider()
    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        if st.button("📋 텍스트 전체 보기/복사", use_container_width=True, disabled=not generated):
            st.code(generated, language=None)

    with btn_col2:
        naver_btn = st.button(
            "🚀 네이버 블로그 업로드",
            use_container_width=True,
            type="primary",
            disabled=not generated,
        )

    if naver_btn:
        if not naver_id or not naver_pw:
            st.error("사이드바에서 네이버 ID와 비밀번호를 입력해주세요.")
        elif not generated:
            st.error("먼저 블로그 글을 생성해주세요.")
        else:
            with st.spinner("🚀 네이버 블로그 업로드 중... 브라우저 창이 열립니다"):
                result = post_to_naver(
                    naver_id=naver_id,
                    naver_pw=naver_pw,
                    title=title or restaurant_name,
                    content=generated,
                    tags=tags,
                )

            if result["success"]:
                st.success("✅ 업로드 완료! 네이버 블로그를 확인해주세요.")
                if result.get("url"):
                    st.markdown(f"[👉 포스팅 확인하기]({result['url']})")
            else:
                st.error(f"업로드 실패: {result.get('error', '알 수 없는 오류')}")
                st.info("💡 브라우저가 열려 있다면 직접 사진 추가 후 발행 버튼을 눌러주세요.")
