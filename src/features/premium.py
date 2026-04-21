def build(ctx):
    """PREMIUM feature 빌더.

    Columns:
        premium_industry_ratio       : 파인다이닝/오마카세/한정식 등 고가 업종 비율
        guide_restaurant_count_norm  : 미쉐린·블루리본 선정 수 (동별, 정규화)
        franchise_ratio_inverse      : 1 - 프랜차이즈 비율
        high_price_poi_ratio         : (옵션) 공개 크롤링 가격대 상위 비율
    """
    raise NotImplementedError
