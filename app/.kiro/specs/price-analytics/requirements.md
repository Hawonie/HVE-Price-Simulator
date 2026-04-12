# Requirements Document

## Introduction

Amazon Tracker MVP에 가격 분석(Price Analytics) 기능을 추가한다. 이 기능은 기간별 가격 히스토리 필터링, Was Price(90일 중앙값) 계산, T30(30일 최저값) 계산, 그리고 가상 가격 시뮬레이션을 포함한다. 사용자는 특정 기간의 가격 추이를 차트로 확인하고, 아마존의 Was Price 및 T30 지표를 기준일 기반으로 조회하며, 가상의 가격 변경이 이 지표들에 미치는 영향을 시뮬레이션할 수 있다.

## Glossary

- **Price_Analytics_API**: 가격 분석 관련 데이터를 제공하는 FastAPI 백엔드 REST API 엔드포인트 집합
- **History_Filter**: 기간 프리셋(1일, 7일, 30일, 60일, 90일) 또는 사용자 지정 날짜 범위로 스냅샷 히스토리를 필터링하는 기능
- **Was_Price_Calculator**: 기준일로부터 과거 90일간의 current_price 중앙값(median)을 계산하는 서비스 모듈
- **T30_Calculator**: 기준일로부터 과거 30일간의 current_price 최저값(minimum)을 계산하는 서비스 모듈
- **Price_Simulator**: 특정 날짜에 가상의 가격을 주입한 후, 지정된 기준일 기준으로 Was Price와 T30을 재계산하는 서비스 모듈
- **History_Dialog**: 가격 히스토리 차트, Was Price/T30 조회, 시뮬레이션 폼을 포함하는 프론트엔드 모달 다이얼로그
- **Reference_Date**: Was Price 또는 T30 계산의 기준이 되는 날짜
- **Simulation_Date**: 가상 가격이 적용되는 날짜 (시뮬레이션 입력값 X)
- **Simulation_Price**: 시뮬레이션에서 주입하는 가상 가격 (시뮬레이션 입력값 Y)
- **Evaluation_Date**: 시뮬레이션 결과를 평가하는 기준일 (시뮬레이션 입력값 Z)
- **ProductSnapshot**: crawl_timestamp, current_price 등 시계열 가격 데이터를 저장하는 SQLAlchemy 모델

## Requirements

### Requirement 1: 기간별 가격 히스토리 필터링 API

**User Story:** 셀러로서, 특정 기간의 가격 히스토리만 조회하고 싶다. 이를 통해 원하는 기간의 가격 추이를 분석할 수 있다.

#### Acceptance Criteria

1. WHEN 클라이언트가 기간 프리셋(1d, 7d, 30d, 60d, 90d) 파라미터와 함께 히스토리 API를 호출하면, THE Price_Analytics_API SHALL 현재 시각 기준으로 해당 기간 내의 ProductSnapshot 목록만 반환한다.
2. WHEN 클라이언트가 start_date와 end_date 파라미터를 함께 제공하면, THE Price_Analytics_API SHALL 해당 날짜 범위(양 끝 포함) 내의 ProductSnapshot 목록만 반환한다.
3. WHEN 기간 프리셋과 커스텀 날짜 범위가 동시에 제공되면, THE Price_Analytics_API SHALL 커스텀 날짜 범위를 우선 적용한다.
4. WHEN 지정된 기간 내에 스냅샷이 존재하지 않으면, THE Price_Analytics_API SHALL 빈 배열을 반환한다.
5. IF 존재하지 않는 상품에 대해 필터링 요청이 들어오면, THEN THE Price_Analytics_API SHALL HTTP 404 상태 코드와 오류 메시지를 반환한다.
6. THE Price_Analytics_API SHALL 반환되는 스냅샷 목록을 crawl_timestamp 오름차순으로 정렬한다.

### Requirement 2: Was Price 계산 API

**User Story:** 셀러로서, 특정 날짜 기준의 Was Price(90일 중앙값)를 조회하고 싶다. 이를 통해 아마존의 Was Price 기준을 파악할 수 있다.

#### Acceptance Criteria

1. WHEN 클라이언트가 Reference_Date를 제공하면, THE Was_Price_Calculator SHALL Reference_Date로부터 과거 90일간(Reference_Date 포함, 90일 전 날짜 포함)의 current_price 값들의 중앙값을 계산하여 반환한다.
2. WHEN 90일 윈도우 내에 current_price가 null인 스냅샷이 존재하면, THE Was_Price_Calculator SHALL 해당 스냅샷을 중앙값 계산에서 제외한다.
3. WHEN 90일 윈도우 내에 유효한 가격 데이터가 짝수 개이면, THE Was_Price_Calculator SHALL 중앙에 위치한 두 값의 평균을 중앙값으로 반환한다.
4. WHEN 90일 윈도우 내에 유효한 가격 데이터가 존재하지 않으면, THE Was_Price_Calculator SHALL null 값을 반환한다.
5. IF 존재하지 않는 상품에 대해 Was Price 요청이 들어오면, THEN THE Price_Analytics_API SHALL HTTP 404 상태 코드와 오류 메시지를 반환한다.

### Requirement 3: T30 계산 API

**User Story:** 셀러로서, 특정 날짜 기준의 T30(30일 최저값)을 조회하고 싶다. 이를 통해 아마존의 T30 할인 기준을 파악할 수 있다.

#### Acceptance Criteria

1. WHEN 클라이언트가 Reference_Date를 제공하면, THE T30_Calculator SHALL Reference_Date로부터 과거 30일간(Reference_Date 포함, 30일 전 날짜 포함)의 current_price 값들 중 최저값을 계산하여 반환한다.
2. WHEN 30일 윈도우 내에 current_price가 null인 스냅샷이 존재하면, THE T30_Calculator SHALL 해당 스냅샷을 최저값 계산에서 제외한다.
3. WHEN 30일 윈도우 내에 유효한 가격 데이터가 존재하지 않으면, THE T30_Calculator SHALL null 값을 반환한다.
4. IF 존재하지 않는 상품에 대해 T30 요청이 들어오면, THEN THE Price_Analytics_API SHALL HTTP 404 상태 코드와 오류 메시지를 반환한다.

### Requirement 4: 가격 시뮬레이션 API

**User Story:** 셀러로서, 특정 날짜에 가격을 변경했을 때 Was Price와 T30이 어떻게 바뀌는지 미리 확인하고 싶다. 이를 통해 가격 전략을 사전에 검증할 수 있다.

#### Acceptance Criteria

1. WHEN 클라이언트가 Simulation_Date(X), Simulation_Price(Y), Evaluation_Date(Z)를 제공하면, THE Price_Simulator SHALL 기존 스냅샷 데이터에 Simulation_Date에 Simulation_Price를 가상으로 추가한 후, Evaluation_Date 기준의 Was Price와 T30을 계산하여 반환한다.
2. THE Price_Simulator SHALL 시뮬레이션 결과에 시뮬레이션 적용 전의 Was Price와 T30 값도 함께 반환하여 비교할 수 있도록 한다.
3. WHEN Simulation_Price가 0 미만의 값이면, THE Price_Analytics_API SHALL HTTP 400 상태 코드와 유효성 검증 오류 메시지를 반환한다.
4. WHEN Simulation_Date가 Evaluation_Date보다 미래 날짜이면, THE Price_Analytics_API SHALL HTTP 400 상태 코드와 오류 메시지를 반환한다.
5. THE Price_Simulator SHALL 실제 데이터베이스의 스냅샷 데이터를 변경하지 않는다.
6. IF 존재하지 않는 상품에 대해 시뮬레이션 요청이 들어오면, THEN THE Price_Analytics_API SHALL HTTP 404 상태 코드와 오류 메시지를 반환한다.

### Requirement 5: Was Price 및 T30 통합 조회 API

**User Story:** 셀러로서, 하나의 API 호출로 특정 날짜 기준의 Was Price와 T30을 동시에 조회하고 싶다. 이를 통해 두 지표를 한눈에 비교할 수 있다.

#### Acceptance Criteria

1. WHEN 클라이언트가 Reference_Date를 제공하면, THE Price_Analytics_API SHALL Was Price와 T30을 동시에 계산하여 하나의 응답으로 반환한다.
2. THE Price_Analytics_API SHALL 응답에 Reference_Date, Was Price 값, T30 값, 각 계산에 사용된 데이터 포인트 수를 포함한다.
3. IF 존재하지 않는 상품에 대해 통합 조회 요청이 들어오면, THEN THE Price_Analytics_API SHALL HTTP 404 상태 코드와 오류 메시지를 반환한다.

### Requirement 6: 프론트엔드 기간별 필터링 UI

**User Story:** 셀러로서, 히스토리 다이얼로그에서 기간을 선택하여 차트에 표시되는 데이터 범위를 조절하고 싶다.

#### Acceptance Criteria

1. WHEN 사용자가 히스토리 다이얼로그를 열면, THE History_Dialog SHALL 기간 프리셋 버튼(1일, 7일, 30일, 60일, 90일)과 커스텀 날짜 범위 입력 필드(시작일, 종료일)를 표시한다.
2. WHEN 사용자가 기간 프리셋 버튼을 클릭하면, THE History_Dialog SHALL 해당 기간의 필터링된 스냅샷 데이터를 가져와 차트를 갱신한다.
3. WHEN 사용자가 커스텀 날짜 범위를 입력하고 적용하면, THE History_Dialog SHALL 해당 날짜 범위의 필터링된 스냅샷 데이터를 가져와 차트를 갱신한다.
4. THE History_Dialog SHALL 현재 선택된 기간 프리셋 버튼을 시각적으로 구분하여 표시한다.

### Requirement 7: 프론트엔드 Was Price 및 T30 조회 UI

**User Story:** 셀러로서, 히스토리 다이얼로그에서 특정 날짜를 입력하여 Was Price와 T30을 확인하고 싶다.

#### Acceptance Criteria

1. THE History_Dialog SHALL Was Price/T30 조회를 위한 날짜 입력 필드와 조회 버튼을 표시한다.
2. WHEN 사용자가 Reference_Date를 입력하고 조회 버튼을 클릭하면, THE History_Dialog SHALL Was Price와 T30 값을 API로부터 가져와 표시한다.
3. THE History_Dialog SHALL Was Price와 T30 값을 통화 기호와 함께 명확하게 표시한다.
4. WHEN API 응답에서 Was Price 또는 T30이 null이면, THE History_Dialog SHALL 해당 값을 "데이터 부족"으로 표시한다.

### Requirement 8: 프론트엔드 가격 시뮬레이션 UI

**User Story:** 셀러로서, 히스토리 다이얼로그에서 가상 가격을 입력하여 Was Price와 T30 변화를 시뮬레이션하고 싶다.

#### Acceptance Criteria

1. THE History_Dialog SHALL 시뮬레이션을 위한 입력 폼(Simulation_Date, Simulation_Price, Evaluation_Date)과 실행 버튼을 표시한다.
2. WHEN 사용자가 시뮬레이션 입력값을 채우고 실행 버튼을 클릭하면, THE History_Dialog SHALL 시뮬레이션 API를 호출하고 결과를 표시한다.
3. THE History_Dialog SHALL 시뮬레이션 결과를 시뮬레이션 전(Before)과 시뮬레이션 후(After) 값을 나란히 비교하는 형태로 표시한다.
4. WHEN 시뮬레이션 API가 유효성 검증 오류를 반환하면, THE History_Dialog SHALL 사용자에게 오류 메시지를 표시한다.

### Requirement 9: Was Price 계산 라운드트립 정합성

**User Story:** 개발자로서, Was Price 계산 로직의 정확성을 보장하고 싶다. 이를 통해 계산 결과를 신뢰할 수 있다.

#### Acceptance Criteria

1. FOR ALL 유효한 가격 리스트에 대해, THE Was_Price_Calculator SHALL Python statistics.median 함수와 동일한 결과를 반환한다.
2. FOR ALL 유효한 가격 리스트에 대해, THE Was_Price_Calculator SHALL 입력 리스트의 순서에 관계없이 동일한 중앙값을 반환한다 (순서 불변성).
3. FOR ALL 동일한 값으로 구성된 가격 리스트에 대해, THE Was_Price_Calculator SHALL 해당 값을 중앙값으로 반환한다 (멱등성).

### Requirement 10: T30 계산 라운드트립 정합성

**User Story:** 개발자로서, T30 계산 로직의 정확성을 보장하고 싶다. 이를 통해 계산 결과를 신뢰할 수 있다.

#### Acceptance Criteria

1. FOR ALL 유효한 가격 리스트에 대해, THE T30_Calculator SHALL Python min 함수와 동일한 결과를 반환한다.
2. FOR ALL 유효한 가격 리스트에 대해, THE T30_Calculator SHALL 입력 리스트의 순서에 관계없이 동일한 최저값을 반환한다 (순서 불변성).
3. FOR ALL 유효한 가격 리스트에 대해, THE T30_Calculator SHALL Was_Price_Calculator의 결과 이하의 값을 반환한다 (T30 ≤ Was Price, 동일 기간 기준 시).
