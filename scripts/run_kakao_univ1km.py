import os, json, pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from src.collectors.kakao_keyword import KakaoKeywordCollector

load_dotenv()
key = os.environ['KAKAO_REST_API_KEY']
feat = pd.read_parquet('data/processed/area_features.parquet')
col = KakaoKeywordCollector(api_key=key, rate_limit_per_sec=10, radius_m=1000)  # 1km
out_path = Path('data/interim/kakao_university_sc4_1km.jsonl')
existing = {}
if out_path.exists():
    with open(out_path,'r',encoding='utf-8') as f:
        for l in f:
            r = json.loads(l); existing[(r['sido'],r['sigungu'],r['eupmyeondong'])] = r

cnt = len(existing)
print(f'resume {cnt}')
with open(out_path,'a',encoding='utf-8') as f:
    for _, r in feat[['sido','sigungu','eupmyeondong','lon','lat']].reset_index(drop=True).iterrows():
        k = (r.sido, r.sigungu, r.eupmyeondong)
        if k in existing: continue
        n = col.count('대학교', float(r.lon), float(r.lat), category_group_code='SC4') if pd.notna(r.lon) else 0
        rec = {'sido':r.sido,'sigungu':r.sigungu,'eupmyeondong':r.eupmyeondong,'kakao_univ_sc4_1km':n or 0}
        f.write(json.dumps(rec,ensure_ascii=False)+'\n'); f.flush()
        cnt += 1
        if cnt % 200 == 0: print(f'[univ1km] {cnt}/{len(feat)}')

rows=[]
with open(out_path) as f:
    for l in f: rows.append(json.loads(l))
pd.DataFrame(rows).to_parquet('data/interim/kakao_university_sc4_1km.parquet', index=False)
print(f'done: {len(rows)}')
