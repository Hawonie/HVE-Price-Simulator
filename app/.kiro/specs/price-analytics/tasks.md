# 구현 계획: Price Analytics

## 개요

기존 Amazon Tracker MVP 코드베이스에 가격 분석 기능을 점진적으로 추가한다. 순수 계산 함수 → Pydantic 스키마 → DB 연동 서비스 → API 엔드포인트 → 프론트엔드 UI 순서로 구현하며, 각 단계에서 테스트를 병행한다.

## Tasks

- [x] 1. Pydantic 스키마 및 순수 계산 함수 구현
  - [x] 1.1 `app/schemas/product.py`에 응답/요청 스키마 추가
    - `WasPriceResponse`, `T30Response`, `PriceIndicatorsResponse`, `SimulationRequest`, `SimulationResult` 스키마 정의
    - `SimulationRequest.simulation_price`에 `Field(ge=0)` 유효성 검증 적용
    - _Requirements: 2.1, 3.1, 4.1, 4.3, 5.2_

  - [x] 1.2 `app/services/price_analytics.py` 생성 및 순수 계산 함수 구현
    - `compute_was_price(prices: list[float]) -> float | None`: 중앙값 계산, 빈 리스트 시 None 반환
    - `compute_t30(prices: list[float]) -> float | None`: 최저값 계산, 빈 리스트 시 None 반환
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 9.1, 9.3, 10.1_

  - [ ]* 1.3 `compute_was_price` 속성 기반 테스트 작성
    - **Property 3: Was Price는 statistics.median과 일치**
    - **Validates: Requirements 9.1, 2.1, 2.3**

  - [ ]* 1.4 `compute_was_price` 순서 불변성 속성 기반 테스트 작성
    - **Property 4: Was Price 순서 불변성**
    - **Validates: Requirements 9.2**

  - [ ]* 1.5 `compute_t30` 속성 기반 테스트 작성
    - **Property 5: T30은 min()과 일치**
    - **Validates: Requirements 10.1, 3.1**

  - [ ]* 1.6 `compute_t30` 순서 불변성 속성 기반 테스트 작성
    - **Property 6: T30 순서 불변성**
    - **Validates: Requirements 10.2**

  - [ ]* 1.7 T30 ≤ Was Price 속성 기반 테스트 작성
    - **Property 7: T30 ≤ Was Price**
    - **Validates: Requirements 10.3**

  - [ ]* 1.8 순수 계산 함수 단위 테스트 작성
    - 빈 리스트 → None 반환 (Req 2.4, 3.3)
    - 짝수 개 가격 → 중앙 두 값 평균 (Req 2.3)
    - 동일 값 리스트 → 해당 값 반환 (Req 9.3)
    - _Requirements: 2.1, 2.3, 2.4, 3.1, 3.3_

- [x] 2. Checkpoint - 순수 계산 함수 검증
  - 모든 테스트가 통과하는지 확인하고, 문제가 있으면 사용자에게 질문한다.

- [x] 3. DB 연동 서비스 함수 구현
  - [x] 3.1 `get_filtered_snapshots` 구현
    - `start_date`, `end_date` 기반 `crawl_timestamp` WHERE 조건 필터링
    - 결과를 `crawl_timestamp` 오름차순 정렬
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_

  - [x] 3.2 `get_was_price` 및 `get_t30` DB 연동 함수 구현
    - `reference_date` 기준 90일/30일 윈도우 스냅샷 조회
    - `current_price`가 null인 스냅샷 제외
    - 순수 함수 `compute_was_price`/`compute_t30` 호출하여 결과 반환
    - 사용된 데이터 포인트 수 함께 반환
    - _Requirements: 2.1, 2.2, 2.4, 3.1, 3.2, 3.3_

  - [x] 3.3 `simulate_price` 함수 구현
    - 기존 스냅샷 데이터를 메모리에 복사 후 가상 가격 주입
    - 시뮬레이션 전(before)과 후(after) Was Price/T30 계산
    - 실제 DB 데이터 변경 없음
    - `SimulationResult` 스키마로 결과 반환
    - _Requirements: 4.1, 4.2, 4.5_

  - [ ]* 3.4 기간 필터링 정합성 속성 기반 테스트 작성
    - **Property 1: 기간 필터링 정합성**
    - **Validates: Requirements 1.1, 1.2, 1.6**

  - [ ]* 3.5 커스텀 범위 우선 적용 속성 기반 테스트 작성
    - **Property 2: 커스텀 범위 우선 적용**
    - **Validates: Requirements 1.3**

  - [ ]* 3.6 시뮬레이션 정합성 속성 기반 테스트 작성
    - **Property 8: 시뮬레이션 정합성**
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 3.7 시뮬레이션 DB 불변성 속성 기반 테스트 작성
    - **Property 10: 시뮬레이션 DB 불변성**
    - **Validates: Requirements 4.5**

- [x] 4. Checkpoint - 서비스 레이어 검증
  - 모든 테스트가 통과하는지 확인하고, 문제가 있으면 사용자에게 질문한다.

- [x] 5. API 엔드포인트 구현
  - [x] 5.1 기존 `/history` 엔드포인트에 기간 필터링 파라미터 추가
    - `period` (1d, 7d, 30d, 60d, 90d), `start_date`, `end_date` 쿼리 파라미터 추가
    - 커스텀 날짜 범위가 프리셋보다 우선
    - 존재하지 않는 상품 → 404
    - `get_filtered_snapshots` 서비스 함수 호출
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 5.2 Was Price 엔드포인트 추가 (`GET /was-price`)
    - `reference_date` 쿼리 파라미터, 존재하지 않는 상품 → 404
    - `WasPriceResponse` 스키마로 응답
    - _Requirements: 2.1, 2.5_

  - [x] 5.3 T30 엔드포인트 추가 (`GET /t30`)
    - `reference_date` 쿼리 파라미터, 존재하지 않는 상품 → 404
    - `T30Response` 스키마로 응답
    - _Requirements: 3.1, 3.4_

  - [x] 5.4 통합 조회 엔드포인트 추가 (`GET /price-indicators`)
    - Was Price + T30 동시 계산, `PriceIndicatorsResponse` 스키마로 응답
    - 존재하지 않는 상품 → 404
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 5.5 시뮬레이션 엔드포인트 추가 (`POST /simulate`)
    - `SimulationRequest` 바디 수신, `simulation_date > evaluation_date` → 400
    - `simulation_price < 0` → Pydantic 422 (Field ge=0)
    - 존재하지 않는 상품 → 404
    - `SimulationResult` 스키마로 응답
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 5.6 시뮬레이션 유효성 검증 속성 기반 테스트 작성
    - **Property 9: 시뮬레이션 유효성 검증**
    - **Validates: Requirements 4.3, 4.4**

  - [ ]* 5.7 통합 조회 일관성 속성 기반 테스트 작성
    - **Property 11: 통합 조회 일관성**
    - **Validates: Requirements 5.1, 5.2**

  - [ ]* 5.8 API 엔드포인트 단위 테스트 작성
    - `httpx.AsyncClient`로 각 엔드포인트 호출 검증
    - 404 오류 케이스, 빈 결과 케이스, 정상 응답 케이스
    - _Requirements: 1.5, 2.5, 3.4, 4.6, 5.3_

- [x] 6. Checkpoint - API 레이어 검증
  - 모든 테스트가 통과하는지 확인하고, 문제가 있으면 사용자에게 질문한다.

- [x] 7. 프론트엔드 UI 구현
  - [x] 7.1 히스토리 다이얼로그에 기간 필터 UI 추가
    - 프리셋 버튼(1일, 7일, 30일, 60일, 90일) 및 커스텀 날짜 범위 입력 필드 추가
    - 프리셋 버튼 클릭 시 필터링된 데이터로 차트 갱신
    - 커스텀 날짜 범위 적용 시 차트 갱신
    - 선택된 프리셋 버튼 시각적 구분 (active 스타일)
    - `showHistory` 함수 수정: 필터 파라미터 포함하여 API 호출
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 7.2 Was Price/T30 조회 패널 추가
    - 기준일(Reference_Date) 입력 필드 및 조회 버튼 추가
    - `/price-indicators` API 호출하여 결과 표시
    - 통화 기호와 함께 Was Price, T30 값 표시
    - null 값은 "데이터 부족"으로 표시
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 7.3 시뮬레이션 패널 추가
    - Simulation_Date, Simulation_Price, Evaluation_Date 입력 폼 및 실행 버튼 추가
    - `/simulate` API 호출 및 Before/After 비교 테이블로 결과 표시
    - API 유효성 검증 오류 시 사용자에게 오류 메시지 표시
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 8. 최종 Checkpoint - 전체 기능 검증
  - 모든 테스트가 통과하는지 확인하고, 문제가 있으면 사용자에게 질문한다.

## Notes

- `*` 표시된 태스크는 선택 사항이며 빠른 MVP를 위해 건너뛸 수 있다
- 각 태스크는 추적 가능성을 위해 구체적인 요구사항을 참조한다
- Checkpoint에서 점진적 검증을 수행한다
- 속성 기반 테스트는 보편적 정합성 속성을, 단위 테스트는 구체적 예시와 엣지 케이스를 검증한다
- 테스트 파일: `tests/test_price_analytics.py` (순수 함수 + 속성 기반), `tests/test_price_analytics_api.py` (API 통합)
