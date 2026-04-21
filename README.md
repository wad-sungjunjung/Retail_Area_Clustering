# Retail Area Clustering

캐치테이블 가맹 매장 관점의 **레스토랑 중심 상권 분류** 프로젝트.
전국 읍/면/동 **3,562개**를 6개 상권 유형 + `GENERAL` (Fallback) 으로 자동 분류한다.

> 🗺 **[Live Map (GitHub Pages)](https://<GH_USER>.github.io/<REPO>/area_map_polygon.html)** — Rank1/2/3 전환·유형 필터링이 가능한 인터랙티브 전국 지도
>
> *(아래 Pages 배포 안내에 따라 퍼블리시 후 URL 두 토큰을 실제 값으로 교체)*

- **단위**: 시/도 → 시/군/구 → 읍/면/동
- **출력**: Rank1 / Rank2 / Rank3 (임계값 0.60 이상만 배정)
- **데이터**: 외부 공공 데이터 전용 (내부 데이터 미사용)
- **검증**: Ground Truth 63개 기준 정확도 79.4%

## 상권 유형 (v0.4)

| 코드 | 상권명 | 예시 |
|------|--------|------|
| `PREMIUM` | 고급 외식 상권 | 청담, 한남, 도산, 압구정, 성수 |
| `OFFICE` | 오피스 점심 상권 | 역삼, 을지로, 판교 |
| `NIGHTLIFE` | 유흥 결합 상권 | 홍대, 강남, 종로3가 |
| `FAMILY` | 대규모 주거 상권 | 목동, 반포, 백현 |
| `TOURIST` | 관광지 상권 | 명동, 인사동, 북촌, 광장시장 |
| `CAMPUS` | 대학가 가성비 상권 | 신촌, 건대, 안암, 흑석 |
| `GENERAL` | 일반 지역 (Fallback) | 기타 동 |

> 버전 이력: v0.1 9종 → v0.3 `DATE_TRENDY`·`MARKET_STREET` 제거 → v0.4 force-promote·threshold 통합. 상세는 [docs/METHODOLOGY.md](./docs/METHODOLOGY.md) 참조.

## 분류 원칙

- **Rule-based 가중합 스코어** (`α=1.0`, ML 비활성 — GMM 이 GT 정확도를 낮추어 제외)
- **임계값 0.60 일괄 적용**: Rank1/2/3 모두 score < 0.60 → 미배정
- **Postprocess 체인**: demote (CAMPUS/TOURIST/PREMIUM 강등) → threshold enforce → force promote (PREMIUM/CAMPUS/NIGHTLIFE/TOURIST/FAMILY/OFFICE)
- **Force promote 우선순위**: PREMIUM > CAMPUS > NIGHTLIFE > TOURIST > FAMILY > OFFICE

## 디렉토리 구조

```
├── config/              # 상권 정의·가중치·경로
│   ├── config.yaml
│   ├── categories.yaml
│   └── feature_weights.yaml
├── data/
│   ├── raw/             # 원천 (git 미포함)
│   ├── interim/         # Kakao POI/키워드 캐시 (git 미포함)
│   └── processed/       # 최종 feature store + 분류 결과
├── docs/
│   ├── METHODOLOGY.md
│   ├── CLASSIFICATION_CRITERIA.md
│   └── CLASSIFICATION_RESULTS.md
├── scripts/             # 단발성 수집·시각화 러너
├── src/
│   ├── collectors/      # Kakao REST, Tour API 등
│   ├── features/        # sbiz / kakao feature 빌더
│   ├── scoring/         # rule_scorer, hybrid, postprocess
│   ├── evaluation/      # ground_truth, hill_climb
│   ├── pipeline/        # end-to-end
│   └── visualize/       # Folium 지도 (marker + polygon)
├── tests/
├── main.py
└── requirements.txt
```

## 외부 데이터

| 소스 | 경로 | 비고 |
|------|------|------|
| 소상공인 상가(상권)정보 CSV | `소상공인시장진흥공단_상가(상권)정보_*/` | 공공데이터포털, git 미포함 (1.4GB) |
| Kakao Local REST API | `data/interim/kakao_*.parquet` | POI + 키워드 검색 + `SC4` 대학 필터 |
| 행정동 GeoJSON | `data/raw/boundaries/hangjeongdong.geojson` | Polygon 지도용, git 미포함 |

## 실행

```bash
cp .env.example .env                  # KAKAO_REST_API_KEY 입력
pip install -r requirements.txt

# 1. feature store 빌드 (sbiz CSV + Kakao 캐시)
python main.py features

# 2. 분류 실행 → data/processed/area_commercial_type.{parquet,csv}
python main.py classify

# 3. 지도 시각화 (선택)
python scripts/run_area_map.py        # polygon 뷰
python scripts/run_map.py             # marker 뷰
```

### Kakao 수집 (최초 1회, 시간 소요)

```bash
python scripts/run_kakao.py           # POI 14 카테고리 수집
python scripts/run_kakao_kw.py        # 키워드 검색 (노포, 파인다이닝 등)
python scripts/run_kakao_kw3.py      # 추가 키워드
python scripts/run_kakao_univ2km.py   # 2km 반경 대학교(SC4) 집계
```

## 결과물

- `data/processed/area_commercial_type.csv` — 읍면동 × (Rank1, Rank2, Rank3, scores)
- `data/processed/area_map_polygon.html` — 행정동 경계 기반 인터랙티브 지도 (git 미포함, 재생성)
- `docs/area_map_polygon.html` — 위 지도의 퍼블리시용 사본 (GitHub Pages 배포 대상)

### GitHub Pages 배포

지도를 웹에서 바로 보여주려면:

1. 리포지토리를 GitHub에 푸시
2. **Settings → Pages → Build and deployment**
   - Source: `Deploy from a branch`
   - Branch: `main` / folder: `/docs`
3. 몇 분 뒤 `https://<USER>.github.io/<REPO>/area_map_polygon.html` 에 접근 가능
4. README 상단의 `<GH_USER>`·`<REPO>` 플레이스홀더를 실제 값으로 치환

지도를 업데이트했을 때는 `cp data/processed/area_map_polygon.html docs/` 후 커밋하면 자동 반영됩니다.

## 문서

- [METHODOLOGY.md](./docs/METHODOLOGY.md) — 파이프라인·Feature·Scoring 전체 설명
- [CLASSIFICATION_CRITERIA.md](./docs/CLASSIFICATION_CRITERIA.md) — 카테고리별 가중치·임계값·force 규칙
- [CLASSIFICATION_RESULTS.md](./docs/CLASSIFICATION_RESULTS.md) — 분포·예시·GT 검증
- [PLANNING.md](./PLANNING.md) — 초기 기획(v0.1 기준, 역사적 참고용)
