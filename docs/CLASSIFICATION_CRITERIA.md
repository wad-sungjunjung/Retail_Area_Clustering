# 상권 분류 기준 (v0.4 최종)

**최종 업데이트**: 2026-04-21
**GT 정확도**: 50/63 = 79.4%
**전국 커버리지**: 3,562 읍·면·동

---

## 1. 분류 체계 — 7개 유형 + GENERAL

| 코드 | 이름 | 성격 | 대표 지역 |
|------|------|------|-----------|
| `PREMIUM` | 럭셔리 다이닝 상권 | 파인다이닝·오마카세·한우·프리미엄 일식 | 청담, 한남, 압구정, 신사, 성수 |
| `OFFICE_LUNCH` | 오피스 상권 | 직장인 점심 수요, 회전율 | 여의도, 광화문, 판교 |
| `NIGHTLIFE_DINING` | 유흥 트랜디 상권 | 저녁·야간, 술자리 | 홍대, 강남 유흥가, 종로3가 |
| `FAMILY_RESIDENTIAL` | 대규모 주거 상권 | 아파트 밀집, 가족 외식 | 목동, 반포, 판교, 송도 |
| `TOURIST_DINING` | 관광지 상권 | 관광객·숙박, 유명 전통시장 포함 | 명동, 북촌, 중문, 해운대, 광장시장 |
| `CAMPUS_CASUAL` | 대학가 상권 | 학생, 저가·캐주얼 | 신촌, 건대, 성대, 관악 |
| `GENERAL` | 일반 상권 | 특정 성격 뚜렷하지 않음 (fallback) | 지방 소도시, 동네 시장 |

---

## 2. 데이터 소스

| 소스 | 레코드 | 기여 |
|------|-------|------|
| 소상공인 상가(상권)정보 CSV 2025-12 | 2,591,587 사업자 | 업종 mix, 프랜차이즈, 좌표 |
| 카카오 로컬 API — 카테고리 POI | 32,058 호출 | 학교·관광·지하철·은행·숙박·문화·학원·병원·편의점 |
| 카카오 로컬 API — 키워드 | 32,058 호출 | 대학교(1·2·3km)·아파트·백화점·클럽·바·포차·브런치·디저트 |

---

## 3. Feature 정의

총 50여 개. 주요 feature 그룹:

### 3-1. sbiz 업종 비율 (`_ratio`)
- `premium_industry_ratio`: 경양식·회초밥·한우·복 업종 비중
- `foreign_restaurant_ratio`: 양식·일식·중식·동남아 비중
- `korean_traditional_ratio`: 한식 비중
- `low_price_industry_ratio`: 분식·치킨·피자 비중
- `cafe_ratio`: 카페 비중
- `alcohol_industry_ratio`: 주점 비중
- `night_business_ratio`: 주점+유흥 비중
- `izakaya_pub_ratio`: 이자카야·생맥주 비중
- `franchise_ratio`: 프랜차이즈 비율
- `independent_small_ratio`: 1 − franchise_ratio

### 3-2. sbiz 밀도 (`_density`, 전국 percentile rank)
- `business_density`: 음식점 수
- `premium_density`: 프리미엄 업종 절대 수
- `low_price_density`: 저가 업종 수
- `korean_density`: 한식 수

### 3-3. 카카오 POI 비중 (`_share`, 전국 percentile rank of ratio)
- `bank_share`, `subway_station_share`, `accommodation_share`
- `school_share`, `academy_share`, `hospital_share`
- `tourist_spot_share`, `culture_facility_share`, `convenience_store_share`

### 3-4. 카카오 키워드 카운트 rank (`_count_rank`)
- `university_count_rank`: 3km 내 대학교 수 percentile
- `university_2km_rank`: 2km 내 대학교 수
- `apartment_count_rank`: 3km 내 아파트 수
- `department_store_count_rank`: 3km 내 백화점 수
- `club_count_rank`, `bar_count_rank`, `pocha_count_rank`: 1.5km 반경
- `brunch_count_rank`, `dessert_count_rank`: 1.5km 반경

---

## 4. 분류 파이프라인 (5단계)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Rule Scorer — 각 유형별 가중합 → [0, 1] score            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Rank Assignment — top-3 + threshold_primary/secondary    │
│     • rank1: max score (≥ 0.6 필수)                          │
│     • rank2·3: 차순위 (≥ 0.6 필수)                           │
│     • 미만이면 비움                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Demote Postprocess — 비정상 rank1 강등                    │
│     • CAMPUS: 2km 내 대학 < 2 AND 3km 내 < 3 → 강등           │
│     • TOURIST: AT4 < 3 OR AD5 < 10 → 강등                    │
│     • PREMIUM: prem_ratio<0.12 OR foreign<0.15 → 강등        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Threshold Enforcement — rank1_score < 0.6 → GENERAL       │
│     + rank2/3 > rank1 이상 안정화                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Force Promote (GENERAL → 특정 유형, 명확한 signal 시)      │
│    우선순위: PREMIUM → CAMPUS → NIGHTLIFE → TOURIST         │
│              → FAMILY → OFFICE                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 유형별 판별 기준

### 5-1. PREMIUM (럭셔리 다이닝 상권)

**Rule 가중치** (합계 = 합으로 정규화)

| 가중치 | Feature | 해석 |
|:------:|---------|------|
| +0.29 | department_store_count_rank | 백화점 근접 |
| +0.27 | premium_industry_ratio | 경양식·회초밥·한우 비중 |
| +0.16 | franchise_ratio_inverse | 비프랜차이즈 비율 |
| +0.16 | pocha_count_rank | (약한 양) |
| +0.01 | accommodation_share | 고급 호텔 근접 |
| −0.46 | korean_traditional_ratio | 한식 편중 → PREMIUM 아님 |
| −0.40 | low_price_industry_ratio | 분식 많으면 PREMIUM 아님 |
| −0.39 | university_count_rank | 대학 많으면 CAMPUS 성격 |
| −0.30 | franchise_ratio | 프랜차이즈 많음 |
| −0.05 | culture_facility_share | (약한 음) |

**Demote 조건** (rank1=PREMIUM → 강등):
- `premium_industry_ratio < 0.12` **OR** `foreign_restaurant_ratio < 0.15`

**Force 조건** (GENERAL → PREMIUM 승격):
- `premium_industry_ratio ≥ 0.12` **AND** `foreign_restaurant_ratio ≥ 0.15`

### 5-2. OFFICE_LUNCH (오피스 상권)

| 가중치 | Feature | 해석 |
|:------:|---------|------|
| +0.41 | brunch_count_rank | 오피스 브런치 |
| +0.38 | bank_share | 은행 POI 비중 (핵심) |
| +0.22 | business_density | 음식점 밀도 |
| +0.11 | subway_station_share | 지하철역 |
| +0.06 | club_count_rank | (약한) |
| +0.06 | apartment_count_rank | (약한) |
| −0.50 | university_count_rank | 대학 → CAMPUS |
| −0.29 | premium_industry_ratio | 고급 → PREMIUM |
| −0.25 | tourist_spot_share | 관광 → TOURIST |
| −0.25 | pocha_count_rank | 포차 많으면 NIGHTLIFE |
| −0.08 | korean_traditional_ratio | 한식 → MARKET |

**Force 조건** (GENERAL → OFFICE 승격):
- `bank_share ≥ 0.9` **AND** `subway_station_share ≥ 0.8` **AND** `business_density ≥ 0.9`

### 5-3. NIGHTLIFE_DINING (유흥 트랜디 상권)

| 가중치 | Feature | 해석 |
|:------:|---------|------|
| +0.30 | pocha_count_rank | 포차 (핵심) |
| +0.30 | club_count_rank | 클럽 |
| +0.20 | entertainment_poi_density | 유흥 POI |
| +0.19 | alcohol_industry_ratio | 주점 비중 |
| +0.16 | bar_count_rank | 바 |
| +0.15 | hospital_share | (약한) |
| +0.07 | school_share | (약한) |
| +0.05 | night_business_ratio | 야간업종 |
| −0.32 | academy_share | 학원 → FAMILY |
| −0.32 | apartment_count_rank | 아파트 → FAMILY |
| −0.24 | cafe_ratio | 카페 → DATE (구 유형) |
| −0.13 | bank_share | 은행 → OFFICE |

**Force 조건** (GENERAL → NIGHTLIFE 승격):
- `club_count_rank ≥ 0.95` **AND** `alcohol_industry_ratio ≥ 0.10`

### 5-4. FAMILY_RESIDENTIAL (대규모 주거 상권)

| 가중치 | Feature | 해석 |
|:------:|---------|------|
| +0.48 | academy_share | 학원 밀집 (핵심) |
| +0.34 | apartment_count_rank | 아파트 |
| +0.26 | hospital_share | 병원 |
| +0.13 | brunch_count_rank | (약한) |
| +0.05 | school_share | 학교 |
| −0.45 | tourist_spot_share | 관광 → TOURIST |
| −0.40 | premium_industry_ratio | 고급 → PREMIUM |
| −0.32 | bank_share | 은행 → OFFICE |
| −0.31 | entertainment_poi_density | 유흥 → NIGHTLIFE |
| −0.25 | university_count_rank | 대학 → CAMPUS |
| −0.09 | club_count_rank | (약한) |
| −0.08 | convenience_store_share | (약한 음, 의외) |

**Force 조건** (GENERAL → FAMILY 승격):
- `apartment_count_rank ≥ 0.9` **AND** `academy_share ≥ 0.5`

### 5-5. TOURIST_DINING (관광지 상권)

| 가중치 | Feature | 해석 |
|:------:|---------|------|
| +0.50 | accommodation_share | 숙박 비중 (핵심) |
| +0.40 | tourist_spot_share | 관광지 POI |
| +0.07 | academy_share | (약한, 의외) |
| +0.04 | university_count_rank | (약한) |
| −0.50 | foreign_restaurant_ratio | (음수, hill climb 학습 결과) |
| −0.32 | korean_traditional_ratio | 한식 → MARKET/시골 |
| −0.26 | apartment_count_rank | 주거 → FAMILY |
| −0.06 | culture_facility_share | (약한 음) |
| −0.03 | cafe_ratio | (약한 음) |

**Demote 조건** (rank1=TOURIST → 강등):
- `kakao_AT4_count < 3` **OR** `kakao_AD5_count < 10`

**Force 조건** (GENERAL → TOURIST 승격):
- `tourist_spot_share ≥ 0.55` **AND** `accommodation_share ≥ 0.70`

### 5-6. CAMPUS_CASUAL (대학가 상권)

| 가중치 | Feature | 해석 |
|:------:|---------|------|
| +0.50 | university_count_rank | 3km 내 대학 (핵심) |
| +0.19 | low_price_density | 분식·저가 업종 밀도 |
| +0.11 | franchise_ratio | 대학가 프랜차이즈 많음 |
| +0.10 | university_2km_rank | 2km 내 대학 |
| +0.06 | low_price_industry_ratio | 저가 업종 비중 |
| +0.06 | accommodation_share | (약한) |
| −0.42 | apartment_count_rank | 아파트 → FAMILY |
| −0.21 | tourist_spot_share | 관광 → TOURIST |
| −0.11 | bank_share | 은행 → OFFICE |
| −0.08 | premium_industry_ratio | 고급 → PREMIUM |
| −0.02 | cafe_ratio | (약한 음) |

**Demote 조건** (rank1=CAMPUS → 강등):
- `2km 내 대학 < 2` **AND** `3km 내 대학 < 3`

**Force 조건** (GENERAL → CAMPUS 승격):
- `2km 내 대학교 ≥ 2`

### 5-7. GENERAL (일반 상권)

**자동 배정** — 다음 중 하나 이상 해당 시:
- rank1 score < 0.6 (어느 유형도 뚜렷하지 않음)
- Rule score top 유형이 Demote 조건 발동 후 rank2 없음
- 모든 Force 조건 미달

---

## 6. Rank 배정 규칙

| Rank | 조건 | 설명 |
|------|------|------|
| rank1 | score ≥ 0.6 | 주 분류. 미달 시 GENERAL |
| rank2 | score ≥ 0.6 | 보조 분류 (복합 상권). 미달 시 비움 |
| rank3 | score ≥ 0.6 | 삼순위. 미달 시 비움 |

**초접전 (margin 작음) 은 그대로 유지** — 복합 상권 신호로 해석.
**모든 유형 점수가 낮음** → GENERAL.

---

## 7. 검증 지표 (GT 63곳)

| 카테고리 | GT | Top-1 정확도 |
|----------|:---:|:-----:|
| PREMIUM | 6 | 6/6 (100%) |
| OFFICE_LUNCH | 10 | 8/10 (80%) |
| NIGHTLIFE_DINING | 11 | 9/11 (82%) |
| FAMILY_RESIDENTIAL | 10 | 9/10 (90%) |
| TOURIST_DINING | 16 | 11/16 (69%) |
| CAMPUS_CASUAL | 10 | 7/10 (70%) |
| **합계** | **63** | **50/63 (79.4%)** |

---

## 8. 전국 분포 (최종)

| 유형 | 동 수 | 비중 |
|------|----:|----:|
| FAMILY_RESIDENTIAL | 929 | 26.1% |
| TOURIST_DINING | 849 | 23.8% |
| GENERAL | 806 | 22.6% |
| OFFICE_LUNCH | 615 | 17.3% |
| CAMPUS_CASUAL | 189 | 5.3% |
| NIGHTLIFE_DINING | 143 | 4.0% |
| PREMIUM | 31 | 0.9% |

---

## 9. 산출물

| 파일 | 내용 |
|------|------|
| `data/processed/area_commercial_type.csv` | 매핑 테이블 (CSV) |
| `data/processed/area_commercial_type.parquet` | 동일 + all_scores |
| `data/processed/area_features.parquet` | feature store (50+ 컬럼) |
| `data/processed/area_map_polygon.html` | 폴리곤 지도 (매칭 99.9%) |
| `data/processed/area_map.html` | 마커 지도 |
| `config/feature_weights.yaml` | 가중치 |
| `config/config.yaml` | 파라미터 (α, threshold) |
| `config/categories.yaml` | 유형 정의 |
| `src/evaluation/ground_truth.py` | 검증용 GT 63곳 |

---

## 10. 제외된 유형

| 유형 | 제외 이유 |
|------|----------|
| DATE_TRENDY | sbiz/카카오 feature 만으로 변별 불가 (카페·브런치 서울 전반 높음). 네이버 블로그·SNS 데이터 없음 |
| MARKET_STREET | 유명 전통시장(광장·남대문 등) → TOURIST, 동네 시장 → GENERAL 로 편입 |
| BUSINESS_DINING | 접대·비즈니스 판별에 내부 데이터 필요 (법인카드·리드타임 등) |
| LANDMARK | 야구장·경기장·놀이공원 등은 TOURIST로 통합 (카카오 AT4 포함되지 않는 일부는 현재 FAMILY/OFFICE로 분류) |

---

## 11. 재현 방법

```bash
# 데이터 준비
cp .env.example .env   # KAKAO_REST_API_KEY 입력
# 소상공인 CSV 다운로드 후 config.yaml 의 sbiz_csv_dir 에 배치

pip install -r requirements.txt

# 1. Feature build
python main.py features

# 2. 분류 (postprocess + force 전체 적용)
python main.py classify

# 3. 지도 생성
python run_area_map.py
python run_map.py

# 4. GT 평가
python -c "
from pathlib import Path
from src.evaluation.evaluator import evaluate, summary
df = evaluate(Path('config/feature_weights.yaml'),
              Path('data/processed/area_features.parquet'))
summary(df)
"
```

---

## 12. Hill Climb 재학습

가중치 재학습 필요 시:

```python
from pathlib import Path
import pandas as pd, yaml
from src.evaluation.hill_climb import climb_with_random_restarts
from src.evaluation.auto_tune import save_weights

feat = pd.read_parquet('data/processed/area_features.parquet')
with open('config/feature_weights.yaml') as f: init = yaml.safe_load(f)
best, hits = climb_with_random_restarts(init, feat,
                                        n_restarts=10, n_iters=2000)
save_weights(best, Path('config/feature_weights.yaml'))
```

- `weight_clip=0.5` 기본 (overfitting 방지)
- Random restart 10회 × 2,000 iteration
