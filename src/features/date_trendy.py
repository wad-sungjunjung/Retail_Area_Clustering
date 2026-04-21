def build(ctx):
    """DATE_TRENDY feature 빌더.

    Columns:
        cafe_brunch_density       : 카페·브런치·디저트 POI 밀도
        new_store_ratio           : 최근 2년 신규 개업 매장 비율
        blog_mention_norm         : 네이버 블로그 지역명 게시물 수 (정규화)
        independent_small_ratio   : 독립(비프랜차이즈) 소규모 매장 비율
    """
    raise NotImplementedError
