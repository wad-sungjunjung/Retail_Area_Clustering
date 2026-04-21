"""샘플 feature store.

외부 API/공공 데이터 수집 전이라도 파이프라인을 end-to-end 검증할 수 있도록
대표 읍/면/동 ~40곳에 대해 사전 정규화(0~1)된 feature 값을 하드코딩한다.
실제 운영에서는 src/collectors/* 로 수집한 원천을 src/features/* 로 집계해
동일 스키마의 DataFrame을 생성한다.
"""
from __future__ import annotations

import pandas as pd

SAMPLE_FEATURE_COLUMNS = [
    # PREMIUM
    "premium_industry_ratio", "guide_restaurant_count_norm",
    "franchise_ratio_inverse", "high_price_poi_ratio",
    # DATE_TRENDY
    "cafe_brunch_density", "new_store_ratio",
    "blog_mention_norm", "independent_small_ratio",
    # OFFICE_LUNCH
    "business_density", "office_poi_density",
    "midlow_price_ratio", "bank_density",
    # NIGHTLIFE_DINING
    "entertainment_poi_density", "izakaya_pub_ratio",
    "night_business_ratio", "alcohol_industry_ratio",
    # FAMILY_RESIDENTIAL
    "apt_household_count_norm", "academy_density",
    "residential_land_ratio", "convenience_medical_density",
    # TOURIST_DINING
    "tourist_spot_count", "accommodation_density",
    "foreigner_resident_ratio", "foreign_restaurant_ratio",
    # CAMPUS_CASUAL
    "university_count_3km", "student_count_norm",
    "low_price_industry_ratio", "franchise_ratio",
    # MARKET_STREET
    "traditional_market_flag", "long_established_ratio",
    "small_store_density", "korean_traditional_ratio",
]


def _row(sido, sigungu, dong, **kwargs):
    row = {c: 0.1 for c in SAMPLE_FEATURE_COLUMNS}
    row.update(kwargs)
    row["sido"] = sido
    row["sigungu"] = sigungu
    row["eupmyeondong"] = dong
    return row


# Feature 값은 전국 분포 대비 0~1 스코어로 해석.
SAMPLES = [
    # ──────────────────────────────── PREMIUM 축
    _row("서울특별시", "강남구", "청담동",
         premium_industry_ratio=0.92, guide_restaurant_count_norm=0.90,
         franchise_ratio_inverse=0.85, high_price_poi_ratio=0.90,
         cafe_brunch_density=0.55, blog_mention_norm=0.60, new_store_ratio=0.35,
         independent_small_ratio=0.60, business_density=0.55, office_poi_density=0.40,
         bank_density=0.45, foreigner_resident_ratio=0.45,
         foreign_restaurant_ratio=0.55, accommodation_density=0.40),
    _row("서울특별시", "용산구", "한남동",
         premium_industry_ratio=0.88, guide_restaurant_count_norm=0.82,
         franchise_ratio_inverse=0.80, high_price_poi_ratio=0.82,
         cafe_brunch_density=0.60, blog_mention_norm=0.62, new_store_ratio=0.45,
         independent_small_ratio=0.65, foreigner_resident_ratio=0.70,
         foreign_restaurant_ratio=0.65, accommodation_density=0.45),
    _row("서울특별시", "강남구", "신사동",
         premium_industry_ratio=0.80, guide_restaurant_count_norm=0.72,
         franchise_ratio_inverse=0.70, high_price_poi_ratio=0.78,
         cafe_brunch_density=0.80, blog_mention_norm=0.82, new_store_ratio=0.60,
         independent_small_ratio=0.70, business_density=0.55),
    _row("서울특별시", "강남구", "압구정동",
         premium_industry_ratio=0.85, guide_restaurant_count_norm=0.75,
         franchise_ratio_inverse=0.72, high_price_poi_ratio=0.80,
         cafe_brunch_density=0.65, blog_mention_norm=0.60,
         apt_household_count_norm=0.55, residential_land_ratio=0.45),

    # ──────────────────────────────── DATE_TRENDY 축
    _row("서울특별시", "성동구", "성수동1가",
         cafe_brunch_density=0.92, new_store_ratio=0.88,
         blog_mention_norm=0.95, independent_small_ratio=0.85,
         premium_industry_ratio=0.45, high_price_poi_ratio=0.40,
         franchise_ratio_inverse=0.70),
    _row("서울특별시", "마포구", "연남동",
         cafe_brunch_density=0.88, new_store_ratio=0.82,
         blog_mention_norm=0.85, independent_small_ratio=0.82,
         university_count_3km=0.55, student_count_norm=0.50,
         foreign_restaurant_ratio=0.45, foreigner_resident_ratio=0.50),
    _row("서울특별시", "종로구", "익선동",
         cafe_brunch_density=0.85, new_store_ratio=0.75,
         blog_mention_norm=0.88, independent_small_ratio=0.80,
         tourist_spot_count=0.55, accommodation_density=0.40,
         long_established_ratio=0.45, small_store_density=0.55),

    # ──────────────────────────────── OFFICE_LUNCH 축
    _row("서울특별시", "강남구", "역삼동",
         business_density=0.95, office_poi_density=0.92,
         midlow_price_ratio=0.75, bank_density=0.88,
         premium_industry_ratio=0.55, high_price_poi_ratio=0.55,
         entertainment_poi_density=0.55, izakaya_pub_ratio=0.55,
         night_business_ratio=0.55),
    _row("서울특별시", "중구", "을지로3가",
         business_density=0.85, office_poi_density=0.82,
         midlow_price_ratio=0.80, bank_density=0.80,
         entertainment_poi_density=0.60, izakaya_pub_ratio=0.72,
         night_business_ratio=0.72, alcohol_industry_ratio=0.65,
         long_established_ratio=0.50),
    _row("서울특별시", "영등포구", "여의도동",
         business_density=0.92, office_poi_density=0.95,
         midlow_price_ratio=0.55, bank_density=0.95,
         premium_industry_ratio=0.65, high_price_poi_ratio=0.65,
         guide_restaurant_count_norm=0.55),
    _row("경기도", "성남시 분당구", "삼평동",
         business_density=0.90, office_poi_density=0.88,
         midlow_price_ratio=0.70, bank_density=0.60,
         apt_household_count_norm=0.60, residential_land_ratio=0.45,
         academy_density=0.55, convenience_medical_density=0.55),

    # ──────────────────────────────── NIGHTLIFE 축
    _row("서울특별시", "마포구", "서교동",
         entertainment_poi_density=0.92, izakaya_pub_ratio=0.88,
         night_business_ratio=0.90, alcohol_industry_ratio=0.82,
         cafe_brunch_density=0.75, new_store_ratio=0.65, blog_mention_norm=0.82,
         university_count_3km=0.80, student_count_norm=0.75,
         low_price_industry_ratio=0.55, franchise_ratio=0.55,
         foreigner_resident_ratio=0.45, foreign_restaurant_ratio=0.50),
    _row("서울특별시", "종로구", "종로3가",
         entertainment_poi_density=0.88, izakaya_pub_ratio=0.85,
         night_business_ratio=0.90, alcohol_industry_ratio=0.85,
         traditional_market_flag=0.60, long_established_ratio=0.75,
         small_store_density=0.70, korean_traditional_ratio=0.70,
         tourist_spot_count=0.45),

    # ──────────────────────────────── FAMILY_RESIDENTIAL 축
    _row("서울특별시", "양천구", "목동",
         apt_household_count_norm=0.92, academy_density=0.95,
         residential_land_ratio=0.85, convenience_medical_density=0.80,
         business_density=0.45, midlow_price_ratio=0.55,
         franchise_ratio=0.55),
    _row("서울특별시", "서초구", "반포동",
         apt_household_count_norm=0.90, academy_density=0.88,
         residential_land_ratio=0.80, convenience_medical_density=0.75,
         premium_industry_ratio=0.65, high_price_poi_ratio=0.60,
         guide_restaurant_count_norm=0.55, franchise_ratio_inverse=0.60),
    _row("서울특별시", "노원구", "상계동",
         apt_household_count_norm=0.88, academy_density=0.75,
         residential_land_ratio=0.82, convenience_medical_density=0.70,
         low_price_industry_ratio=0.55, franchise_ratio=0.65),
    _row("경기도", "수원시 영통구", "영통동",
         apt_household_count_norm=0.85, academy_density=0.80,
         residential_land_ratio=0.82, convenience_medical_density=0.70),
    _row("경기도", "고양시 일산동구", "장항동",
         apt_household_count_norm=0.80, academy_density=0.72,
         residential_land_ratio=0.80, convenience_medical_density=0.68),
    _row("인천광역시", "연수구", "송도동",
         apt_household_count_norm=0.85, academy_density=0.78,
         residential_land_ratio=0.75, convenience_medical_density=0.70,
         business_density=0.72, office_poi_density=0.70,
         midlow_price_ratio=0.55),

    # ──────────────────────────────── TOURIST 축
    _row("서울특별시", "중구", "명동",
         tourist_spot_count=0.95, accommodation_density=0.90,
         foreigner_resident_ratio=0.65, foreign_restaurant_ratio=0.78,
         business_density=0.70, franchise_ratio=0.75,
         cafe_brunch_density=0.65),
    _row("서울특별시", "종로구", "인사동",
         tourist_spot_count=0.90, accommodation_density=0.70,
         foreigner_resident_ratio=0.50, foreign_restaurant_ratio=0.55,
         traditional_market_flag=0.55, long_established_ratio=0.80,
         small_store_density=0.75, korean_traditional_ratio=0.78),
    _row("서울특별시", "종로구", "가회동",
         tourist_spot_count=0.92, accommodation_density=0.65,
         foreigner_resident_ratio=0.55, foreign_restaurant_ratio=0.50,
         cafe_brunch_density=0.72, blog_mention_norm=0.75,
         residential_land_ratio=0.50),
    _row("서울특별시", "용산구", "이태원동",
         tourist_spot_count=0.78, accommodation_density=0.75,
         foreigner_resident_ratio=0.92, foreign_restaurant_ratio=0.90,
         entertainment_poi_density=0.82, izakaya_pub_ratio=0.72,
         night_business_ratio=0.82, alcohol_industry_ratio=0.72),
    _row("부산광역시", "해운대구", "우동",
         tourist_spot_count=0.85, accommodation_density=0.88,
         foreigner_resident_ratio=0.55, foreign_restaurant_ratio=0.55,
         premium_industry_ratio=0.55, high_price_poi_ratio=0.60,
         apt_household_count_norm=0.60),
    _row("부산광역시", "중구", "남포동",
         tourist_spot_count=0.80, accommodation_density=0.75,
         foreigner_resident_ratio=0.45, foreign_restaurant_ratio=0.50,
         traditional_market_flag=0.70, long_established_ratio=0.70,
         small_store_density=0.75, korean_traditional_ratio=0.65),
    _row("제주특별자치도", "서귀포시", "중문동",
         tourist_spot_count=0.90, accommodation_density=0.92,
         foreigner_resident_ratio=0.45, foreign_restaurant_ratio=0.45,
         premium_industry_ratio=0.50),

    # ──────────────────────────────── CAMPUS 축
    _row("서울특별시", "서대문구", "신촌동",
         university_count_3km=0.92, student_count_norm=0.90,
         low_price_industry_ratio=0.82, franchise_ratio=0.78,
         entertainment_poi_density=0.75, izakaya_pub_ratio=0.80,
         night_business_ratio=0.75, alcohol_industry_ratio=0.70,
         cafe_brunch_density=0.70),
    _row("서울특별시", "광진구", "화양동",
         university_count_3km=0.88, student_count_norm=0.82,
         low_price_industry_ratio=0.82, franchise_ratio=0.80,
         entertainment_poi_density=0.80, izakaya_pub_ratio=0.82,
         night_business_ratio=0.80, alcohol_industry_ratio=0.72,
         foreign_restaurant_ratio=0.55),
    _row("서울특별시", "성북구", "안암동",
         university_count_3km=0.85, student_count_norm=0.78,
         low_price_industry_ratio=0.78, franchise_ratio=0.72,
         cafe_brunch_density=0.55),

    # ──────────────────────────────── MARKET 축
    _row("서울특별시", "종로구", "종로4가",
         traditional_market_flag=1.00, long_established_ratio=0.90,
         small_store_density=0.92, korean_traditional_ratio=0.88,
         tourist_spot_count=0.70, accommodation_density=0.45,
         foreigner_resident_ratio=0.40, foreign_restaurant_ratio=0.35),
    _row("서울특별시", "마포구", "망원동",
         traditional_market_flag=1.00, long_established_ratio=0.72,
         small_store_density=0.85, korean_traditional_ratio=0.70,
         cafe_brunch_density=0.72, new_store_ratio=0.65,
         blog_mention_norm=0.72, independent_small_ratio=0.75),
    _row("서울특별시", "중구", "을지로4가",
         traditional_market_flag=0.85, long_established_ratio=0.82,
         small_store_density=0.80, korean_traditional_ratio=0.75,
         entertainment_poi_density=0.68, izakaya_pub_ratio=0.72,
         night_business_ratio=0.72, alcohol_industry_ratio=0.65),

    # ──────────────────────────────── GENERAL 축 (혼재/특성 약함)
    _row("서울특별시", "관악구", "봉천동",
         apt_household_count_norm=0.45, residential_land_ratio=0.55,
         convenience_medical_density=0.45, low_price_industry_ratio=0.40,
         franchise_ratio=0.45),
    _row("제주특별자치도", "제주시", "연동",
         business_density=0.35, midlow_price_ratio=0.35,
         accommodation_density=0.35, residential_land_ratio=0.45,
         franchise_ratio=0.35),
    _row("강원특별자치도", "춘천시", "교동",
         residential_land_ratio=0.45, convenience_medical_density=0.35,
         low_price_industry_ratio=0.30, franchise_ratio=0.30,
         long_established_ratio=0.40),
    _row("충청북도", "청주시 상당구", "용암동",
         apt_household_count_norm=0.50, residential_land_ratio=0.55,
         convenience_medical_density=0.45, franchise_ratio=0.40),
    _row("전라남도", "순천시", "조례동",
         apt_household_count_norm=0.35, residential_land_ratio=0.50,
         convenience_medical_density=0.35, franchise_ratio=0.30),
]


def load_sample_features() -> pd.DataFrame:
    df = pd.DataFrame(SAMPLES)
    cols = ["sido", "sigungu", "eupmyeondong"] + SAMPLE_FEATURE_COLUMNS
    return df[cols]
