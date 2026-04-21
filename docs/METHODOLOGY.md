# 상권 분류 방법론 (Methodology v0.4)

본 문서는 `Retail_Area_Clustering` 이 읍/면/동 단위 상권 유형을 분류하는 방법론·
이론적 배경을 설명한다.

> **구체적 가중치·Threshold·Force 규칙은
> [CLASSIFICATION_CRITERIA.md](./CLASSIFICATION_CRITERIA.md) 참조.**

---

## 0. 파이프라인 개요

```
 ┌──────────────┐   ┌──────────────────┐   ┌───────────────┐   ┌──────────────┐
 │ 외부 공공   │ → │ 동 단위 Feature  │ → │ Rule Scoring  │ → │ Top 1/2/3    │
 │ 데이터 수집 │   │ Store (50+ cols) │   │ + Postprocess │   │ 상권 분류    │
 └──────────────┘   └──────────────────┘   └───────────────┘   └──────────────┘
       │                   │                       │                  │
  collectors/          features/               scoring/         data/processed/
                                                                 area_commercial_type
```

- 분류 단위: **시/도 > 시/군/구 > 읍/면/동**
- 유형: **7종 + GENERAL**
- 출력: 각 동당 **Top 1·2·3 카테고리 + Confidence 스코어**
- 데이터: **외부 공공 데이터만** 사용 (캐치테이블 내부 데이터 미사용 전제)
- GT 정확도: **50/63 = 79.4%** (검증용 대표 상권 63곳 기준)

---

## 1. 상권 유형 정의 (v0.4)

| 코드 | 상권명 | 핵심 성격 | 대표 지역 |
|------|--------|-----------|-----------|
| `PREMIUM` | 고급 외식 상권 | 객단가 상위, 파인다이닝·한우·프리미엄 일식 | 청담, 한남, 압구정, 신사, 성수 |
| `OFFICE_LUNCH` | 오피스 점심 상권 | 업무지구 직장인 수요, 회전율 높은 캐주얼 | 여의도, 광화문, 판교, 가산디지털 |
| `NIGHTLIFE_DINING` | 유흥 결합 상권 | 저녁·야간, 술자리 | 홍대, 강남 유흥가, 종로3가, 이태원 |
| `FAMILY_RESIDENTIAL` | 대규모 주거 상권 | 아파트 밀집, 가족 단위 외식 | 목동, 반포, 송도, 판교, 평촌 |
| `TOURIST_DINING` | 관광지 상권 | 관광객·숙박, 유명 전통시장 포함 | 명동, 북촌, 중문, 해운대, 광장시장 |
| `CAMPUS_CASUAL` | 대학가 가성비 상권 | 학생, 저가·캐주얼 | 신촌, 건대, 성대, 관악, 흑석 |
| `GENERAL` | 일반 상권 (Fallback) | 특정 성격 뚜렷하지 않음 · 동네 시장 포함 | 지방 소도시, 외곽 동 |

### 유형 변경 이력

| 버전 | 유형 수 | 변경 |
|------|:-:|------|
| v0.1 | 9종 | 초기 (MARKET_STREET, DATE_TRENDY 포함) |
| v0.3 | 8종 | **DATE_TRENDY 제거** — feature 변별력 부재 |
| **v0.4** | **7종** | **MARKET_STREET 제거** — 유명 시장은 TOURIST, 동네 시장은 GENERAL |

### 멀티 레이블 (Primary + Secondary + Tertiary)

실제 상권은 복합적 성격을 가지므로 **Top 1/2/3** 을 모두 제공.
- Primary (rank1): 1위 카테고리 (score ≥ 0.6 필수)
- Secondary (rank2), Tertiary (rank3): 보조 카테고리 (score ≥ 0.6 필수, 미달 시 비움)
- `is_general`: Primary가 GENERAL 인지 플래그

---

## 2. 데이터 소스

### 2-1. 실제 활용 소스 (v0.4)

| 데이터 | 출처 | 규모 | 기여 |
|--------|------|------|------|
| 상가(상권)정보 CSV | 소상공인시장진흥공단 | 2,591,587 사업자 | 업종 mix, 프랜차이즈, 좌표 |
| POI 카테고리 9종 | 카카오 로컬 API | 32,058 호출 | 학교·관광·지하철·은행·숙박·문화·학원·병원·편의점 |
| POI 키워드 8종 | 카카오 로컬 API | 32,058 호출 | 대학교(1/2/3km)·아파트·백화점·클럽·바·포차·브런치·디저트 |
| 행정동 경계 GeoJSON | vuski/admdongkor | 3,554 폴리곤 | 지도 시각화 |

### 2-2. 계획했으나 미사용

| 소스 | 이유 |
|------|------|
| TourAPI 4.0, 공정위 가맹사업, 공동주택 공시, 대학알리미, 미쉐린·블루리본 | **카카오 키워드 검색으로 대체** 가능 (수집 편의성) |
| 캐치테이블 내부 DB (예약·객단가·시간대·party size) | 프로젝트 전제 상 미사용 |
| SKT 생활인구, 네이버 플레이스 대량 크롤링, 구글맵 리뷰 | 유료·제약 — Phase 2+ 검토 |

---

## 3. Feature Engineering

### 3-1. 정규화 원칙

| Feature 종류 | 정규화 방식 | 표기 |
|--------------|-------------|------|
| sbiz 업종 비율 | (해당 업종 수) / (음식점 총 수) | `*_ratio` |
| sbiz 절대 밀도 | 전국 percentile rank | `*_density` |
| 카카오 POI 비중 | 카테고리 / 전체 POI 의 percentile rank | `*_share` |
| 카카오 키워드 카운트 | 절대 카운트의 전국 percentile rank | `*_count_rank` |
| Boolean flag | 0/1 | `*_flag`, `*_has_*` |

결측은 0으로 처리.

### 3-2. 전체 Feature 목록 (50+)

**sbiz 업종 비율 (식당 중)**
- `premium_industry_ratio`: 경양식·회초밥·한우·복 비중
- `foreign_restaurant_ratio`: 양식·일식·중식·동남아 비중
- `korean_traditional_ratio`: 한식 비중
- `low_price_industry_ratio`: 분식·치킨·피자 비중
- `cafe_ratio`, `alcohol_industry_ratio`, `night_business_ratio`, `izakaya_pub_ratio`
- `franchise_ratio`, `independent_small_ratio` (= 1 − franchise_ratio)

**sbiz 절대 밀도 (percentile rank)**
- `business_density`, `premium_density`, `low_price_density`, `korean_density`, `small_store_density`
- `office_poi_density`, `entertainment_poi_density`, `cafe_brunch_density`
- `foreign_restaurant_density`

**카카오 POI 비중 (percentile of share)**
- `bank_share`, `subway_station_share`, `accommodation_share`
- `school_share`, `academy_share`, `hospital_share`
- `tourist_spot_share`, `culture_facility_share`, `convenience_store_share`

**카카오 키워드 count rank**
- `university_count_rank` (3km), `university_2km_rank`, `university_2km_has_campus`
- `apartment_count_rank` (3km), `department_store_count_rank` (3km)
- `club_count_rank`, `bar_count_rank`, `pocha_count_rank` (1.5km)
- `brunch_count_rank`, `dessert_count_rank` (1.5km)

### 3-3. Feature 선택 원칙

1. **도메인 시그널** — 각 유형의 실세계 특징을 반영 (예: 대학교 수 → CAMPUS)
2. **정규화** — 전국 비교 가능하도록 percentile rank
3. **비율 + 밀도 병행** — 번화가 쏠림 억제 (상대적 특성 확인)
4. **긍정/부정 signal** — 한 feature가 여러 유형에 positive/negative 양방향 기여

---

## 4. Rule-Based Scoring

### 4-1. 가중합 방식

각 유형 `c` 에 대해:

```
acc = Σ (weight_f × feature_value_f)

min_possible = Σ min(weight_f, 0)
max_possible = Σ max(weight_f, 0)

score[c] = (acc − min_possible) / (max_possible − min_possible)  ∈ [0, 1]
```

### 4-2. Positive / Negative Weight

Weight는 **양수(+) / 음수(−) 모두 허용**. 의미:
- **Positive**: 해당 feature가 높을수록 이 유형 성격 강함
- **Negative**: 해당 feature가 높을수록 이 유형 아님 (반대 유형)

예) `PREMIUM` 의 `korean_traditional_ratio: −0.46`
- 한식 비중이 높으면 PREMIUM 점수 감점 (지방 한식 편중 지역 배제)

### 4-3. Weight 학습 방법

**Hill Climbing + Random Restart** (GT 63곳 기반)

1. 초기 가중치에서 출발
2. 랜덤 카테고리·feature 선택 → 작은 변화 (±0.05)
3. GT Top-1 hit 수 개선 시 유지
4. Random restart 10회 × 2,000 iteration
5. **Weight clip ±0.5** (overfitting 방지)

구현: `src/evaluation/hill_climb.py`

### 4-4. 현재 가중치

상세는 `config/feature_weights.yaml` 및 `CLASSIFICATION_CRITERIA.md` 섹션 5 참조.

---

## 5. Postprocess (5단계)

Rule score 만으로는 해결 안 되는 **구조적 오분류**를 후처리 규칙으로 보정.

### 5-1. Demote (유형별 절대 threshold 미달 → 강등)

| 유형 | Demote 조건 |
|------|------------|
| CAMPUS_CASUAL | 2km 내 대학 < 2 **AND** 3km 내 < 3 |
| TOURIST_DINING | AT4 POI < 3 **OR** AD5 POI < 10 |
| PREMIUM | prem_industry_ratio < 0.12 **OR** foreign_restaurant_ratio < 0.15 |

**목적**: 춘천 같은 "시골인데 대학 몇 개 있음" 을 CAMPUS로 분류, 또는 지방 소도시를 TOURIST로 분류하는 과대분류 억제.

**로직**: rank1 이 해당 유형인데 조건 미달 → rank2 를 rank1 으로 승격, rank2 가 None 이면 GENERAL.

### 5-2. Threshold Enforcement

Rule score 가 전반적으로 낮아 어떤 유형도 뚜렷하지 않은 동:
- `rank1_score < 0.60` → **GENERAL** 로 강제 전환
- rank2, rank3 정리 (rank1 score 보다 큰 경우 제거)

**효과**: 전국 약 1,200곳 (34%) 이 GENERAL 로 배정. "이것도 애매 저것도 애매" 상태 포착.

### 5-3. Force Promote (GENERAL → 특정 유형)

반대로 rank1 이 GENERAL 이지만 **명확한 유형 시그널** 이 있는 경우 강제 승격:

| 유형 | Force 조건 |
|------|-----------|
| PREMIUM | prem_ratio ≥ 0.12 AND foreign ≥ 0.15 |
| CAMPUS | 2km 내 대학 ≥ 2 |
| NIGHTLIFE | club_rank ≥ 0.95 AND alcohol_ratio ≥ 0.10 |
| TOURIST | tourist_share ≥ 0.55 AND accom_share ≥ 0.70 |
| FAMILY | apt_rank ≥ 0.90 AND academy_share ≥ 0.50 |
| OFFICE | bank_share ≥ 0.90 AND subway ≥ 0.80 AND biz ≥ 0.90 |

**적용 범위**: rank1 이 **GENERAL 인 경우만** 승격 (다른 유형 분류는 덮어쓰지 않음).

**예시**:
- 흑석동: rule_score CAMPUS 0.53 < 0.6 → GENERAL 배정 → 2km 대학 4개 → **CAMPUS 복구**

### 5-4. Postprocess 순서

```
1. CAMPUS demote          (29개 강등)
2. TOURIST demote        (1,037개 강등)
3. PREMIUM demote          (203개 강등)
4. Threshold enforcement    (511개 GENERAL 추가)
5. Force Promote 체인:
   a. PREMIUM force          (6개 승격)
   b. CAMPUS force           (99개 승격)
   c. NIGHTLIFE force         (0개)
   d. TOURIST force         (382개 승격)
   e. FAMILY force            (4개)
   f. OFFICE force            (0개)
```

---

## 6. Rank 배정 규칙

### 6-1. 절대 Threshold (주요 기준)

| Rank | Threshold | 설명 |
|------|:---------:|------|
| rank1 | ≥ 0.6 | 주 분류. 미달 시 GENERAL |
| rank2 | ≥ 0.6 | 보조 분류 (복합 상권). 미달 시 비움 |
| rank3 | ≥ 0.6 | 삼순위. 미달 시 비움 |

### 6-2. 접전 (Margin) 조건

초접전 (rank1_score − rank2_score 매우 작음) 은 **복합 상권 신호로 해석** — rank1 유지.
별도 min_margin 조건 없음 (`min_margin = 0`).

### 6-3. 배정 통계 (전국 3,562 동)

| 배정 상태 | 동 수 | 비중 |
|-----------|-----:|-----:|
| rank1~3 모두 배정 | 605 | 17% |
| rank1, 2만 (rank3 미달) | 777 | 22% |
| rank1 만 (rank2·3 미달) | 884 | 25% |
| GENERAL | 1,297 | 36% |

---

## 7. 출력 스키마

`data/processed/area_commercial_type.parquet` (CSV 사본 동봉)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `sido` | str | 시/도 |
| `sigungu` | str | 시/군/구 |
| `eupmyeondong` | str | 읍/면/동 |
| `rank1_category` | str | 1순위 (GENERAL 포함) |
| `rank1_score` | float | 1순위 스코어 ∈ [0, 1] |
| `rank2_category` | str / null | 2순위 (미달 시 null) |
| `rank2_score` | float / null | 2순위 스코어 |
| `rank3_category` | str / null | 3순위 |
| `rank3_score` | float / null | 3순위 스코어 |
| `is_general` | bool | Primary == GENERAL 플래그 |
| `all_scores` | dict | 전 7개 유형 스코어 (디버깅용) |

### Snowflake 적재 스키마

```sql
CREATE TABLE retail_area_clustering.area_commercial_type (
    sido                 VARCHAR,
    sigungu              VARCHAR,
    eupmyeondong         VARCHAR,
    primary_category     VARCHAR,    -- rank1_category
    secondary_categories ARRAY,      -- [rank2, rank3] (null 제외)
    confidence_scores    OBJECT,     -- all_scores
    data_collected_at    TIMESTAMP,
    model_version        VARCHAR
);
```

---

## 8. 검증 (Ground Truth 63곳)

### 8-1. GT 구성 원칙

- 카테고리별 대표 상권 **4~16곳** 선별
- 명백한 사례만 포함 (복합 상권·경계선은 제외)
- 지방 상권 포함 (수도권 편향 방지)

### 8-2. GT 카테고리별 정확도

| 카테고리 | GT 수 | Top-1 정확도 |
|----------|:---:|:-----:|
| PREMIUM | 6 | 6/6 (100%) |
| FAMILY_RESIDENTIAL | 10 | 9/10 (90%) |
| NIGHTLIFE_DINING | 11 | 9/11 (82%) |
| OFFICE_LUNCH | 10 | 8/10 (80%) |
| TOURIST_DINING | 16 | 11/16 (69%) |
| CAMPUS_CASUAL | 10 | 7/10 (70%) |
| **합계** | **63** | **50/63 (79.4%)** |

### 8-3. 알려진 상권 샘플 (Primary)

| 지역 | 기대 | 모델 Primary |
|------|------|------------|
| 강남 청담동 | PREMIUM | PREMIUM ✓ |
| 용산 한남동 | PREMIUM | PREMIUM ✓ |
| 성동 성수1가1동 | PREMIUM | PREMIUM ✓ (Force) |
| 동작 흑석동 | CAMPUS | CAMPUS ✓ (Force) |
| 중구 명동 | TOURIST | TOURIST ✓ |
| 종로 종로5.6가동(광장시장) | TOURIST | TOURIST ✓ |
| 마포 서교동(홍대) | NIGHTLIFE | NIGHTLIFE ✓ |
| 영등포 여의동 | OFFICE | OFFICE ✓ |
| 양천 목1동 | FAMILY | FAMILY ✓ |

---

## 9. 전국 Primary 분포

| 유형 | 동 수 | 비중 |
|------|----:|----:|
| FAMILY_RESIDENTIAL | 929 | 26.1% |
| TOURIST_DINING | 849 | 23.8% |
| **GENERAL** | **806** | **22.6%** |
| OFFICE_LUNCH | 615 | 17.3% |
| CAMPUS_CASUAL | 189 | 5.3% |
| NIGHTLIFE_DINING | 143 | 4.0% |
| PREMIUM | 31 | 0.9% |

---

## 10. 한계와 리스크

| 한계 | 내용 | 대응 |
|------|------|------|
| 내부 데이터 미사용 | 예약·객단가·시간대·party size 시그널 부재 | 외부 프록시로 근사 |
| DATE_TRENDY 판별 불가 | 카페·브런치가 번화가 전반 높음 | 유형에서 제외 (v0.3) |
| 서울 시내 시장 | 번화가 속 시장 = 모든 POI 높음 | MARKET_STREET 제거, TOURIST 흡수 (v0.4) |
| 랜드마크 (야구장·공항·놀이공원) | 카카오 AT4 미포함 → TOURIST 누락 | 현재 수용, 필요 시 landmark 키워드 추가 가능 |
| 지방 대학가 | 캠퍼스 외곽 대학은 2km 밖 | 2km + 3km OR 조건 시도 (현재는 2km만) |
| Hill Climb 국소 최적 | Weight 학습 국지적 | Random restart + clip (±0.5) |

---

## 11. 재현 방법

```bash
# 1. 키·데이터 준비
cp .env.example .env   # KAKAO_REST_API_KEY 입력
# 소상공인 CSV 다운로드 후 config.yaml 의 sbiz_csv_dir 에 배치

pip install -r requirements.txt

# 2. Feature build
python main.py features

# 3. 분류 (postprocess + force 포함)
python main.py classify

# 4. 지도 생성
python run_area_map.py   # 폴리곤 지도
python run_map.py        # 마커 지도

# 5. GT 평가
python -c "
from pathlib import Path
from src.evaluation.evaluator import evaluate, summary
df = evaluate(Path('config/feature_weights.yaml'),
              Path('data/processed/area_features.parquet'))
summary(df)
"
```

---

## 12. 설정 파일

| 파일 | 역할 |
|------|------|
| `config/config.yaml` | 파이프라인 파라미터 (α, threshold, ML 설정) |
| `config/categories.yaml` | 7개 유형 정의·설명 |
| `config/feature_weights.yaml` | 유형별 가중치 (Hill Climb 결과) |
| `.env` | API 키 (카카오 REST, 공공데이터포털) |

---

## 13. 관련 문서

- **[CLASSIFICATION_CRITERIA.md](./CLASSIFICATION_CRITERIA.md)** — v0.4 최종 판별 기준 레퍼런스 (가중치·Threshold·Force 규칙)
- **[CLASSIFICATION_RESULTS.md](./CLASSIFICATION_RESULTS.md)** — v0.3 결과 분석 (사료)
- **[../README.md](../README.md)** — 실행 개요
- **[../PLANNING.md](../PLANNING.md)** — 초기 기획 (v0.1 기준, 사료)
