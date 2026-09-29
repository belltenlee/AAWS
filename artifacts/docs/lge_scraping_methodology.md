# LGE(lge.co.kr) 냉장고 데이터 수집 기술 분석 보고서

## 1. 탐색 및 분석 과정 (Discovery & Reverse Engineering)
- **도메인 및 카테고리 식별**: `http://lge.com` 접속 시 국가별 리디렉션이 동작하므로 공식 한국 스토어인 `https://www.lge.co.kr/category/refrigerators`로 진입.
- **SSR/DOM 구조 분석**: `extract_dom_skeleton` 및 HTML 조사를 통해 Next.js 기반 스트리밍 SSR 환경임을 확인.
  - 카테고리 목록 내 각 제품 카드가 `a[href*='/refrigerators/']` 셀렉터로 렌더링되어 상품 식별자(SKU), 제품명, 혜택가, 할인율 정보가 포함되어 있음을 파악.
- **내장 구조화 데이터(Schema.org JSON-LD) 발견**: 상세 페이지(`https://www.lge.co.kr/refrigerators/{sku}`) 분석 중 `<script type="application/ld+json">` 태그 내에 Schema.org `Product` 스키마가 완벽히 구조화되어 탑재되어 있음을 역공학을 통해 확인.
  - 동적 UI 파싱 대신 규격화된 JSON-LD 및 HTML 메타데이터를 결합하는 하이브리드 수집 전략 채택.

## 2. HTTP 요청 방식 및 비동기 파이프라인
- **비동기 HTTP 클라이언트**: Python `httpx.AsyncClient` 및 `asyncio`를 사용하여 카테고리 탐색 및 다중 상세 페이지를 비동기 병렬 요청 처리.
- **헤더 및 리디렉션 처리**:
  - `follow_redirects=True`: 모델 기본 URL(예: `/refrigerators/t876mee1h1`)에서 정규 상세 URL(`/product/refrigerators/...`)로의 301 영구 이동 자동 추적.
  - 브라우저 표준 `User-Agent` 및 `Accept-Language` 헤더를 설정하여 봇 감지 방지 및 국문 응답 수신.

## 3. 스크립트 구현 내용 및 데이터 추출 로직 (`artifacts/scripts/scrape_lge_async.py`)
1. **카테고리 제품 탐색 (`fetch_category_products`)**:
   - `https://www.lge.co.kr/category/refrigerators` 호출 후 BeautifulSoup으로 `a[href*='/refrigerators/']` 태그를 수집.
   - 고유한 모델 식별자 9종을 추출하고 카드 내 표시된 최대혜택가(`benefit_price`), 할인율(`discount_rate`), 정가(`base_price`)를 사전 매핑.
2. **무작위 3개 모델 샘플링**:
   - `random.sample(products, 3)`을 통해 중복 없이 무작위 3개 냉장고 제품을 선택.
3. **상세 페이지 비동기 병합 수집 (`fetch_product_detail` + `asyncio.gather`)**:
   - 3개 모델의 상세 URL을 병렬 요청하여 HTML 내 `application/ld+json`의 `Product` 노드를 파싱.
   - **모델명 (`model`)**: `T876MEE1H1`, `S836MEE022`, `D502MEE33` 등
   - **제품명 (`name`)**: 공식 명칭 추출
   - **가격 (`offers.price`)**: 정가 통화 서식화
   - **상세 설명 (`description`)**: 핵심 특징 문구 추출
   - **주요 스펙 (`additionalProperty`)**: `전체 용량(L)`, `색상`, `도어스타일/재질`, `냉각방식`, `에너지 소비효율등급` 등 구조화된 속성 딕셔너리로 변환.
   - **카드 메타데이터 결합**: 목록 카드의 `benefit_price` 및 `discount_rate`를 통합.
4. **원자적 저장**:
   - 추출된 레코드를 `artifacts/data/lge_async.json`에 UTF-8 인코딩의 JSON 배열로 저장.
