"""유형별 feature 빌더.

각 모듈은 build(ctx) -> pd.DataFrame 시그니처를 제공하며,
반환 DataFrame은 (sido, sigungu, eupmyeondong) 키 + 유형별 feature 컬럼을 가진다.
"""
