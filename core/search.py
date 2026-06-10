def search_restaurant_info(restaurant_name: str) -> str:
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    f"{restaurant_name} 메뉴 가격 주소 영업시간",
                    region="kr-kr",
                    max_results=5,
                )
            )

        if not results:
            return ""

        parts = [f"[{r['title']}]\n{r['body']}" for r in results]
        return "\n\n".join(parts)

    except Exception as e:
        return f"검색 실패: {e}"
