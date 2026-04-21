import os, pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from src.collectors.kakao_keyword import KakaoKeywordCollector

load_dotenv()
key = os.environ['KAKAO_REST_API_KEY']
feat = pd.read_parquet('data/processed/area_features.parquet')
col = KakaoKeywordCollector(api_key=key, rate_limit_per_sec=10, radius_m=3000)
cp = Path('data/interim/kakao_kw.jsonl')
df = col.collect_all(
    feat[['sido','sigungu','eupmyeondong','lon','lat']].reset_index(drop=True),
    ['대학교','아파트','백화점'],  # 대학(CAMPUS), 아파트(FAMILY), 백화점(SHOPPING/PREMIUM)
    cp
)
df.to_parquet('data/interim/kakao_kw.parquet', index=False)
print(f'done: {len(df)} dongs, cols={list(df.columns)}')
