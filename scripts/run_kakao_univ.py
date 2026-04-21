"""대학교 keyword + SC4 카테고리 필터 재수집."""
import os, json, time
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from src.collectors.kakao_keyword import KakaoKeywordCollector

load_dotenv()
key = os.environ['KAKAO_REST_API_KEY']
feat = pd.read_parquet('data/processed/area_features.parquet')
col = KakaoKeywordCollector(api_key=key, rate_limit_per_sec=10, radius_m=3000)

out_path = Path('data/interim/kakao_university_sc4.jsonl')
existing = {}
if out_path.exists():
    with open(out_path,'r',encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            key_ = (rec['sido'], rec['sigungu'], rec['eupmyeondong'])
            existing[key_] = rec

out_path.parent.mkdir(parents=True, exist_ok=True)
cnt = len(existing)
print(f'resume from {cnt}')
with open(out_path, 'a', encoding='utf-8') as f:
    for idx, r in feat[['sido','sigungu','eupmyeondong','lon','lat']].reset_index(drop=True).iterrows():
        key_ = (r.sido, r.sigungu, r.eupmyeondong)
        if key_ in existing: continue
        n = col.count('대학교', float(r.lon), float(r.lat),
                      category_group_code='SC4') if pd.notna(r.lon) else 0
        rec = {'sido': r.sido, 'sigungu': r.sigungu, 'eupmyeondong': r.eupmyeondong,
               'kakao_univ_sc4': n or 0}
        f.write(json.dumps(rec, ensure_ascii=False)+'\n'); f.flush()
        cnt += 1
        if cnt % 200 == 0:
            print(f'[univ] {cnt}/{len(feat)}')

# to parquet
rows = []
with open(out_path) as f:
    for line in f:
        rows.append(json.loads(line))
pd.DataFrame(rows).to_parquet('data/interim/kakao_university_sc4.parquet', index=False)
print(f'done: {len(rows)}')
