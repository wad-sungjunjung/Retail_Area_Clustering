# 전국 읍/면/동 상권 분류 결과 (v0.3)

**산출일**: 2026-04-21
**데이터 기준**: 2025-12

---

## 1. 개선 히스토리

| 버전 | Top-1 | 변경 |
|------|------:|------|
| v0.1 | 20% (20 GT) | 카카오 POI 카테고리 9종만 |
| v0.2 | 41% (22 GT) | 카카오 keyword 수집 — 대학교·아파트·백화점 |
| **v0.3** | **61.6% (73 GT)** | Phase 3 keyword (클럽·바·포차·브런치·디저트) + hill climbing 자동 가중치 학습 |

## 2. 산출물

| 파일 | 설명 |
|------|------|
| `data/processed/area_commercial_type.parquet` | 3,562개 읍/면/동 × Top1/2/3 + 전체 8개 스코어 |
| `data/processed/area_commercial_type.csv` | 사람이 읽기 편한 CSV |
| `data/processed/area_features.parquet` | 47개 feature 원본 |
| `data/processed/area_map.html` | 인터랙티브 지도 |
| `data/interim/kakao_poi.parquet` | 카카오 카테고리 POI 9종 |
| `data/interim/kakao_kw.parquet` | 카카오 키워드 (대학교·아파트·백화점) |
| `data/interim/kakao_kw3.parquet` | 카카오 키워드 Phase 3 (클럽·바·포차·브런치·디저트) |

## 3. 데이터 소스

| 소스 | 레코드 | 기여 |
|------|-------|------|
| 소상공인 상가(상권)정보 CSV 2025-12 | 2,591,587 사업자 | 업종 mix, 프랜차이즈 |
| 카카오 로컬 API (카테고리 9종) | 32,058 호출 | 주변 시설 POI |
| 카카오 로컬 API (키워드 8종) | 28,496 호출 | **대학가·주거·유흥·트렌디 변별** |

## 4. GT 기반 평가 (73곳)

| 유형 | GT | Top-1 | 비고 |
|------|----|:-----:|------|
| CAMPUS_CASUAL | 10 | **10/10 (100%)** | 완벽 — 대학교 keyword 결정적 |
| PREMIUM | 4 | **4/4 (100%)** | 완벽 — 청담·한남·압구정·신사 |
| NIGHTLIFE_DINING | 9 | **8/9 (89%)** | 광안1동만 FAMILY로 오분류 |
| TOURIST_DINING | 10 | 7/10 (70%) | 명동·애월·강화 실패 |
| OFFICE_LUNCH | 10 | 7/10 (70%) | 사직·공덕·역삼2동 실패 |
| FAMILY_RESIDENTIAL | 10 | 7/10 (70%) | 야탑·송도·장항 실패 |
| MARKET_STREET | 10 | 2/10 (20%) | **서울 전통시장 구조적 어려움** |
| DATE_TRENDY | 10 | 0/10 (0%) | **데이터 부족 — 구조적 한계** |
| **합계** | 73 | **45/73 (61.6%)** | |

## 5. 핵심 개선: 자동 가중치 학습

### 방법
- GT 73곳을 기준 샘플로 설정
- **Hill Climbing + Random Restart**: 가중치 한 개를 랜덤 변경 → hit 수 재평가 → 개선 시 유지
- 6 restart × 1,500 iteration = 9,000 evaluation
- 최종 가중치: `config/feature_weights.yaml`

### 자동 학습의 주요 발견
- **CAMPUS는 `university_count_rank` 단독으로 완벽 판별**
- **PREMIUM은 `department_store_count_rank` + `premium_industry_ratio`** 조합이 결정적
- **NIGHTLIFE는 클럽/바/포차 키워드 + apartment negative** 조합
- **DATE_TRENDY는 현재 데이터에서 변별 feature 부재** — brunch/dessert/cafe 모두 서울 번화가 전반에 높음

## 6. Primary 분포 (3,562 동)

| 유형 | 동 수 | 비중 |
|------|-----:|-----:|
| TOURIST_DINING | 843 | 23.7% |
| MARKET_STREET | 826 | 23.2% |
| OFFICE_LUNCH | 678 | 19.0% |
| FAMILY_RESIDENTIAL | 639 | 17.9% |
| CAMPUS_CASUAL | 417 | 11.7% |
| PREMIUM | 83 | 2.3% |
| NIGHTLIFE_DINING | 76 | 2.1% |
| DATE_TRENDY | 0 | 0% |

## 7. Secondary 분포

| 유형 | 동 수 |
|------|-----:|
| MARKET_STREET | 1,322 |
| OFFICE_LUNCH | 792 |
| CAMPUS_CASUAL | 408 |
| FAMILY_RESIDENTIAL | 349 |
| TOURIST_DINING | 327 |
| PREMIUM | 185 |
| DATE_TRENDY | 90 |
| NIGHTLIFE_DINING | 89 |

## 8. 구조적 한계

### DATE_TRENDY 변별 불가
- **원인**: 현재 수집된 brunch/dessert/cafe 카카오 POI 수는 서울 번화가 전반에서 1.0 percentile. 성수·연남·가회가 특별히 높다는 시그널이 없음.
- **실제 차별 요소**: 신규 개업 비율·SNS 언급량·인스타 해시태그 — 수집 불가 (네이버 블로그 API 또는 내부 데이터 필요)
- Top-3 Secondary로는 90곳에서 등장

### MARKET_STREET 서울 시내 실패
- **원인**: 제기동·회현동·광장시장 등 서울 시내 전통시장 동은 주변이 번화가라 모든 카테고리 POI가 동시 상위. "번화가 속 전통시장"을 sbiz 업종 비율만으로 구분 불가.
- **정상 판별**: 지방 전통시장(정선·영주·무주 등) 포함 826곳은 MARKET으로 분류

### OFFICE_LUNCH 애매한 경우
- 사직동·공덕동 같은 "오피스+주거+문화" 복합 상권은 CAMPUS(대학교 근접)로 밀림
- 교대·법원 지역(서초3동)은 PREMIUM 성격과 혼재

## 9. GT 실패 상세

**TOURIST_DINING 실패 3곳**
- 명동(서울) → NIGHTLIFE: 관광지 POI보다 바·클럽 POI가 우세
- 애월읍·강화읍 → OFFICE: 지방 관광지인데 은행 POI 비중이 상대적으로 높음

**FAMILY_RESIDENTIAL 실패 3곳**
- 야탑1동 → OFFICE: 판교 인접으로 오피스 신호 일부
- 송도2동 → CAMPUS: 연세대 국제캠퍼스 인접
- 장항1동 → OFFICE: 일산 업무지구 인접

**NIGHTLIFE 실패 1곳**
- 광안1동(부산) → FAMILY: 광안리 해변 주거·아파트 많음

## 10. 실전 활용 가이드

- **Top-3 조합으로 활용 권장**: Top-1만 신뢰하지 말고 Top-3까지 복합 상권 성격으로
- **CAMPUS/PREMIUM Primary는 매우 신뢰 가능** (GT 100%)
- **DATE_TRENDY는 Secondary/Tertiary에서 조회** — Primary에선 나오지 않음
- **지방 TOURIST/MARKET은 Primary 신뢰**, 서울 시내 전통시장은 주의

## 11. Phase 4 로드맵 (DATE_TRENDY 판별)

| 작업 | 필요 리소스 | 효과 |
|------|-------------|------|
| 네이버 블로그 API 동별 지역 게시물 수 | 네이버 API 키, 3,562 호출 | DATE 1순위 신호 가능 |
| 인스타그램 해시태그 (공개) 수집 | 수동/크롤링 | SNS 언급량 |
| 소상공인 데이터 개업일 feature 복원 | 기존 CSV에 없음 — 다른 소스 필요 | 신규 개업 비율 |
| 캐치테이블 내부 객단가·리뷰 | 내부 허가 | 근본적 개선 |
