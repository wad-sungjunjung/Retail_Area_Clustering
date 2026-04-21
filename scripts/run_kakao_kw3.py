import os, pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from src.collectors.kakao_keyword import KakaoKeywordCollector

load_dotenv()
key = os.environ['KAKAO_REST_API_KEY']
feat = pd.read_parquet('data/processed/area_features.parquet')
col = KakaoKeywordCollector(api_key=key, rate_limit_per_sec=10, radius_m=1500)
cp = Path('data/interim/kakao_kw3.jsonl')
df = col.collect_all(
    feat[['sido','sigungu','eupmyeondong','lon','lat']].reset_index(drop=True),
    ['클럽','바','포차','브런치','디저트'],
    cp
)
df.to_parquet('data/interim/kakao_kw3.parquet', index=False)
print(f'done: {len(df)} dongs, cols={list(df.columns)}')
