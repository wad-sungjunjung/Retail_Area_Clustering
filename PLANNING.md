# 상권 클러스터링 프로젝트 기획서

## 1. 프로젝트 개요

캐치테이블에 가맹된 매장들의 주소(시/도 > 시/군/구 > 읍/면/동)를 바탕으로,
각 지역이 어떤 **레스토랑 중심 상권 유형**에 속하는지 자동으로 분류한다.

- **단위**: 읍/면/동
- **출력**: Primary 레이블 + Secondary 레이블(복수) + Confidence
- **데이터**: 외부 공공 데이터만 사용 (내부 데이터 미사용 전제)

---

## 2. 상권 유형 정의 (9종 + Fallback)

| 코드 | 상권명 | 정의 | 예시 |
|------|--------|------|------|
| `PREMIUM` | 고급 외식 상권 | 높은 객단가, 파인다이닝·프리미엄 한/일/양식·고급 바 밀집 | 청담, 한남, 도산, 압구정 |
| `DATE_TRENDY` | 데이트·트렌디 상권 | 데이트·SNS 핫플, 분위기·인테리어 중심 | 성수, 연남, 익선동 |
| `OFFICE_LUNCH` | 오피스 점심 상권 | 직장인 점심 수요, 회전율 높은 캐주얼 | 강남역, 을지로, 판교 |
| `NIGHTLIFE_DINING` | 유흥 결합 상권 | 저녁+술자리, 야간 외식 중심 | 홍대, 강남 유흥가, 종로3가 |
| `FAMILY_RESIDENTIAL` | 대규모 주거 상권 | 아파트 단지 밀집, 가족 단위 외식 | 목동, 반포, 판교 알파돔, 송도 |
| `TOURIST_DINING` | 관광지 상권 | 관광객 대상, 체류시간 짧음 | 명동, 인사동, 북촌 |
| `CAMPUS_CASUAL` | 대학가 가성비 상권 | 학생 중심, 저가·중간가 캐주얼 | 신촌, 건대, 안암 |
| `MARKET_STREET` | 전통시장·노포 상권 | 재래시장·골목 노포 중심 | 광장시장, 을지로 노가리골목 |
| `GENERAL` | 일반 지역 | 특정 성격 뚜렷하지 않음 (Fallback) | 지방 중소도시, 외곽 동 |

## 3. 분류 로직

```
1. 각 유형별 score = α · rule_score + (1-α) · ml_prob   (α=0.6)
2. Primary:
   - if max(score) >= 0.4 → argmax(score)
   - else                   → GENERAL
3. Secondary:
   - Primary != GENERAL 인 경우, score >= 0.4 인 나머지 유형
```

### 출력 예시

```json
{
  "region": "서울특별시 마포구 서교동",
  "primary_category": "NIGHTLIFE_DINING",
  "secondary_categories": ["CAMPUS_CASUAL", "DATE_TRENDY"],
  "confidence_scores": {
    "NIGHTLIFE_DINING": 0.78,
    "CAMPUS_CASUAL": 0.65,
    "DATE_TRENDY": 0.52,
    "PREMIUM": 0.11
  }
}
```

---

## 4. 외부 데이터 소스

| 데이터 | 출처 | 수집 방법 | 사용 유형 |
|--------|------|-----------|-----------|
| POI | 카카오 로컬 API | 읍/면/동 중심점 반경 검색 | 전 유형 |
| 관광지·축제·숙박 | 한국관광공사 TourAPI 4.0 | 지역코드 REST | TOURIST |
| 상가업소(업종·면적·개업일) | 소상공인시장진흥공단 | CSV 배치 | 전 유형 |
| 가맹사업 | 공정거래위원회 가맹사업정보 | CSV | PREMIUM / CAMPUS / MARKET |
| 공동주택 공시 | 국토부 | CSV | FAMILY_RESIDENTIAL |
| 대학·재학생 | 대학알리미 | CSV | CAMPUS_CASUAL |
| 외국인 등록 | 행정안전부 | CSV | TOURIST |
| 전통시장 지정 | 소상공인진흥공단 | 리스트 | MARKET_STREET |
| 미쉐린·블루리본 | 공개 가이드 | 크롤링 | PREMIUM |
| 행정 경계(읍면동) | 국가공간정보포털 | Shapefile | 공통 |

> 유료·제약 있는 소스는 Phase 2 이후 검토 (KT/SKT 생활인구, 네이버 플레이스 가격 크롤링, 구글맵 리뷰 언어 분포 등).

---

## 5. 유형별 Feature 및 스코어링

### 5-1. `PREMIUM`
- 고가 업종(파인다이닝·오마카세·한정식) 비율
- 미쉐린/블루리본 선정 매장 수
- 프랜차이즈 비율 **낮음** (공정위)
- (옵션) 객단가 상위분위 비율 — 공개 크롤링 가능 시

### 5-2. `DATE_TRENDY`
- 카페·브런치·디저트 POI 밀도
- 최근 2년 신규 개업 매장 비율 (사업자등록)
- 네이버 블로그/지역 검색 빈도
- 신규/소규모 독립 매장 비율

### 5-3. `OFFICE_LUNCH`
- 사업체 밀도 (소상공인)
- 업무시설 POI 밀도 (은행·오피스빌딩)
- 중저가 한/중/일식 비율
- (Phase 2) 평일 점심 생활인구 / 거주인구

### 5-4. `NIGHTLIFE_DINING`
- 유흥시설(단란주점·노래방·클럽) POI 밀도
- 이자카야·펍·포차·주점 비율
- 야간업종 밀도 (소상공인)
- (Phase 2) 22시 이후 생활인구

### 5-5. `FAMILY_RESIDENTIAL`
- 아파트 세대수 합계 (공동주택 공시)
- 학원 밀도 (교육청/카카오)
- 주거지역 비율 (토지이용)
- 편의점·병원·약국 밀도

### 5-6. `TOURIST_DINING`
- TourAPI 관광지 수
- 숙박 밀도 (호텔·게스트하우스)
- 외국인 거주 비율
- (Phase 2) 구글맵 외국어 리뷰 비율

### 5-7. `CAMPUS_CASUAL`
- 3km 내 대학교 수 / 재학생 수
- 저가 업종(분식·떡볶이·백반) 비율
- 프랜차이즈 비율 **높음**
- 소형 매장(20평 이하) 밀도

### 5-8. `MARKET_STREET`
- 전통시장 지정 여부 (boolean)
- 업력 20년+ 매장 비율
- 20평 이하 소형 매장 밀도
- 한식·주점·국밥·해장국 비율

### 5-9. `GENERAL`
- 계산하지 않음. `max(score) < 0.4` 시 자동 배정.

---

## 6. 구현 로드맵 (Phase 1 MVP)

### Stage 1 — 데이터 수집 (1-2주)
- 카카오 API 배치 수집기
- TourAPI, 소상공인, 공정위, 공동주택, 대학알리미 CSV 로더
- 미쉐린/블루리본 크롤러
- 행정 경계(Shapefile) 적재

### Stage 2 — Feature Store (2주)
- 읍/면/동 × feature 테이블 (`data/processed/area_features.parquet`)
- 정규화·결측치 처리
- EDA (skew 확인·로그 변환)

### Stage 3 — 스코어링 엔진 (2주)
- Rule-based scorer (유형별 가중합)
- GMM / HDBSCAN 보조 확률
- Hybrid scorer + GENERAL fallback

### Stage 4 — 검증 (1-2주)
- Ground-truth 상권 30곳 라벨링 후 정성 평가
- Silhouette·혼동행렬
- 가중치·임계값 그리드 서치

### Stage 5 — 배포 (1주)
- Snowflake `area_commercial_type` 적재
- 월간 재계산 스케줄

---

## 7. Snowflake 테이블

```sql
CREATE TABLE retail_area_clustering.area_commercial_type (
    sido                 VARCHAR,
    sigungu              VARCHAR,
    eupmyeondong         VARCHAR,
    primary_category     VARCHAR,
    secondary_categories ARRAY,
    confidence_scores    OBJECT,
    data_collected_at    TIMESTAMP,
    model_version        VARCHAR
);
```

---

## 8. 검증 Ground Truth (샘플)

| 지역 | Primary | Secondary |
|------|---------|-----------|
| 강남역(역삼동) | OFFICE_LUNCH | PREMIUM, NIGHTLIFE_DINING |
| 홍대(서교동) | NIGHTLIFE_DINING | CAMPUS_CASUAL, DATE_TRENDY |
| 청담동 | PREMIUM | DATE_TRENDY |
| 명동 | TOURIST_DINING | — |
| 성수동 | DATE_TRENDY | — |
| 목동 | FAMILY_RESIDENTIAL | — |
| 신촌 | CAMPUS_CASUAL | NIGHTLIFE_DINING |
| 광장시장(종로4가) | MARKET_STREET | TOURIST_DINING |
| 여의도 | OFFICE_LUNCH | PREMIUM |
| 판교 | OFFICE_LUNCH | FAMILY_RESIDENTIAL |

---

## 9. 한계 및 리스크

| 리스크 | 대응 |
|--------|------|
| 내부 데이터 미사용 → 예약·객단가·시간대 시그널 부재 | 외부 프록시(생활인구·가격 크롤링) 단계적 도입 |
| 카카오 API 쿼터 | 캐싱·배치 수집 |
| 지방 POI 부족 | 소상공인 CSV로 보완, `GENERAL` 비중 허용 |
| 상권 변동 | 분기/월 단위 재계산 |
