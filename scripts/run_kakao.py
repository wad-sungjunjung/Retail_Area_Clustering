import os, pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from src.collectors.kakao_poi import KakaoPoiCollector, CATEGORY_CODES

load_dotenv()
key = os.environ['KAKAO_REST_API_KEY']
feat = pd.read_parquet('data/processed/area_features.parquet')
col = KakaoPoiCollector(api_key=key, rate_limit_per_sec=10)
cp = Path('data/interim/kakao_poi.jsonl'); cp.parent.mkdir(parents=True, exist_ok=True)
df = col.collect_all(feat[['sido','sigungu','eupmyeondong','lon','lat']].reset_index(drop=True),
                     list(CATEGORY_CODES.keys()), cp)
df.to_parquet('data/interim/kakao_poi.parquet', index=False)
print(f'done: {len(df)} dongs')
