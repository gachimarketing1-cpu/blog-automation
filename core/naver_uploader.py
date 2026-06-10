import time
from playwright.sync_api import sync_playwright

WRITE_URL = "https://blog.naver.com/PostWrite.naver"
LOGIN_URL = "https://nid.naver.com/nidlogin.login?mode=form"

TITLE_SELECTORS = [
    ".se-documentTitle [contenteditable]",
    ".se-title-input [contenteditable]",
    "[placeholder='제목'] [contenteditable]",
]
CONTENT_SELECTORS = [
    ".se-main-container [contenteditable]",
    ".se-text-paragraph [contenteditable]",
    ".smartEditor3 [contenteditable]",
]
TAG_SELECTORS = [
    ".tag_input input",
    "input[placeholder*='태그']",
    ".se-tag-input input",
]
PUBLISH_SELECTORS = [
    "button.publish_btn",
    "button[data-action='publish']",
    ".se-publish-btn button",
    "button:has-text('발행')",
    ".btn_publish",
]


def _try_selectors(page, selectors: list, timeout: int = 3000):
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=timeout)
            if el:
                return el
        except Exception:
            continue
    return None


def _type_in_chunks(page, text: str, chunk_size: int = 500):
    for i in range(0, len(text), chunk_size):
        page.keyboard.type(text[i : i + chunk_size], delay=0)


def post_to_naver(
    naver_id: str,
    naver_pw: str,
    title: str,
    content: str,
    tags: str,
) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            # --- Login ---
            page.goto(LOGIN_URL)
            page.wait_for_load_state("networkidle")

            page.fill("#id", naver_id)
            page.fill("#pw", naver_pw)
            page.click("#log\\.login")
            page.wait_for_timeout(4000)

            if "nidlogin" in page.url or "login" in page.url:
                return {
                    "success": False,
                    "error": "로그인 실패. ID/비밀번호를 확인하거나 보안 문자(캡챠)가 발생했을 수 있습니다.",
                }

            # --- Navigate to write page ---
            page.goto(WRITE_URL)
            page.wait_for_timeout(4000)

            # --- Fill title ---
            title_el = _try_selectors(page, TITLE_SELECTORS)
            if title_el:
                title_el.click()
                page.keyboard.press("Control+A")
                _type_in_chunks(page, title)
                page.wait_for_timeout(800)

            # --- Fill content (keyboard.type, no clipboard needed) ---
            content_el = _try_selectors(page, CONTENT_SELECTORS)
            if content_el:
                content_el.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Delete")
                page.wait_for_timeout(300)
                _type_in_chunks(page, content)
                page.wait_for_timeout(1000)

            # --- Fill tags ---
            if tags:
                tag_el = _try_selectors(page, TAG_SELECTORS)
                if tag_el:
                    for tag in tags.split(","):
                        tag_text = tag.strip().lstrip("#")
                        if tag_text:
                            tag_el.click()
                            tag_el.type(tag_text)
                            page.keyboard.press("Enter")
                            page.wait_for_timeout(400)

            # --- Auto publish ---
            publish_el = _try_selectors(page, PUBLISH_SELECTORS, timeout=5000)
            if publish_el:
                publish_el.click()
                page.wait_for_timeout(3000)
                return {"success": True, "url": page.url}
            else:
                return {
                    "success": False,
                    "error": (
                        "발행 버튼을 찾지 못했습니다. "
                        "네이버 에디터가 변경되었거나 로그인 후 추가 인증이 필요할 수 있습니다."
                    ),
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

        finally:
            time.sleep(1)
            try:
                browser.close()
            except Exception:
                pass
