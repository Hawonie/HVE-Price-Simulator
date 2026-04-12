# 요구사항 문서

## 소개

ZonTrack(Amazon ASIN 가격 트래킹 앱)의 분석 기능을 개선한다. 가격 차트에 기간 내 최저가/최고가 마커를 표시하고, CSV 내보내기에 통계 정보를 포함하며, Buybox 제품 이미지 로딩 문제를 수정하고, 대시보드 통계 카드의 표시 항목을 개선한다.

## 용어 정의

- **Analytics_View**: 선택된 ASIN의 가격 히스토리, 통계, 시뮬레이션을 표시하는 분석 화면 컴포넌트 (`analytics-view.tsx`)
- **Price_Chart**: Analytics_View 내의 Recharts AreaChart 기반 가격 히스토리 차트
- **ReferenceDot**: Recharts 라이브러리에서 차트 위에 특정 데이터 포인트를 강조 표시하는 마커 컴포넌트
- **CSV_Exporter**: Analytics_View의 "Export CSV" 버튼 클릭 시 가격 데이터를 CSV 파일로 내보내는 기능
- **Stats_Card**: 대시보드 화면에서 주요 지표를 요약 표시하는 카드 컴포넌트 (`stats-cards.tsx`)
- **Product_Image**: 제품의 메인 사진을 표시하는 `next/image` 기반 이미지 컴포넌트
- **PriceStats**: 가격 통계 객체 (mean, median, min, max, lastPrice, pctChange, cv, t30, wasPrice)
- **Period_Low**: 선택된 기간(DateRange) 내 가격 데이터 중 최저가
- **Period_High**: 선택된 기간(DateRange) 내 가격 데이터 중 최고가
- **Volatility_Level**: CV(변동계수) 기반 변동성 수준 (low: CV < 3%, medium: 3%-10%, high: CV > 10%)
- **Simulation_Result**: 가격 시뮬레이션 실행 후 산출된 새 T30 및 Was Price 값
- **Buybox_Seller**: Amazon 제품 페이지에서 Buy Box를 점유하고 있는 판매자
- **Last_Update_Time**: 가장 최근 가격 관측(PriceObservation)의 observed_at 타임스탬프

## 요구사항

### 요구사항 1: 가격 차트에 기간 내 최저가/최고가 마커 표시

**사용자 스토리:** 분석 담당자로서, 가격 차트에서 기간 내 최저가와 최고가 지점을 시각적으로 즉시 확인하고 싶다. 이를 통해 가격 변동의 극단값을 빠르게 파악할 수 있다.

#### 인수 조건

1. WHEN 사용자가 기간(DateRange)을 선택하면, THE Price_Chart SHALL 해당 기간 내 최저가 데이터 포인트 위치에 녹색 ReferenceDot 마커를 표시한다.
2. WHEN 사용자가 기간(DateRange)을 선택하면, THE Price_Chart SHALL 해당 기간 내 최고가 데이터 포인트 위치에 빨간색 ReferenceDot 마커를 표시한다.
3. WHEN 최저가 또는 최고가 ReferenceDot 위에 마우스를 올리면, THE Price_Chart SHALL 해당 포인트의 정확한 날짜와 가격을 툴팁으로 표시한다.
4. WHEN 기간 내 가격 데이터가 1개 이하이면, THE Price_Chart SHALL ReferenceDot 마커를 표시하지 않는다.
5. THE Price_Chart SHALL 차트 상단 영역에 Period_Low와 Period_High의 가격 및 날짜를 범례 형태로 표시한다.

### 요구사항 2: CSV 내보내기 기능 개선

**사용자 스토리:** 분석 담당자로서, CSV 내보내기 시 기간 내 최저가, 최고가, 현재 가격(현재 날짜 및 시간 포함), 변동성 수준, 가격 시뮬레이션 결과를 포함하고 싶다. 이를 통해 외부 보고서 작성에 필요한 데이터를 한 번에 확보할 수 있다.

#### 인수 조건

1. WHEN 사용자가 "Export CSV" 버튼을 클릭하면, THE CSV_Exporter SHALL 기간 내 가격 히스토리 데이터를 CSV 파일로 다운로드한다.
2. THE CSV_Exporter SHALL CSV 파일 상단에 요약 섹션을 포함하며, 해당 섹션에는 ASIN, 마켓플레이스, 통화, 내보내기 일시(현재 날짜 및 시간)를 기재한다.
3. THE CSV_Exporter SHALL 요약 섹션에 현재 가격(Current Price)과 해당 가격의 관측 시점을 포함한다.
4. THE CSV_Exporter SHALL 요약 섹션에 기간 내 최저가(Period Low)와 최고가(Period High)를 해당 날짜와 함께 포함한다.
5. THE CSV_Exporter SHALL 요약 섹션에 Volatility_Level(low, medium, high)과 CV 백분율 값을 포함한다.
6. WHEN 사용자가 가격 시뮬레이션을 실행한 상태에서 CSV를 내보내면, THE CSV_Exporter SHALL 요약 섹션에 Simulation_Result(새 T30, 새 Was Price)를 포함한다.
7. WHEN 사용자가 가격 시뮬레이션을 실행하지 않은 상태에서 CSV를 내보내면, THE CSV_Exporter SHALL 시뮬레이션 결과 항목을 "N/A"로 표시한다.
8. THE CSV_Exporter SHALL 요약 섹션 아래에 빈 행을 하나 삽입한 후, 가격 히스토리 데이터를 날짜(observed_at), 가격(price_value), 통화(currency) 컬럼으로 나열한다.
9. THE CSV_Exporter SHALL 파일명을 `{ASIN}_{Marketplace}_{YYYYMMDD_HHmmss}.csv` 형식으로 생성한다.

### 요구사항 3: Buybox 제품 메인 이미지 로딩 수정

**사용자 스토리:** 사용자로서, Buybox를 점유한 제품의 메인 사진이 정상적으로 표시되기를 원한다. 이를 통해 추적 중인 제품을 시각적으로 식별할 수 있다.

#### 인수 조건

1. WHEN 제품이 추가되면, THE Product_Image SHALL Amazon 제품 페이지의 실제 메인 이미지 URL을 사용하여 이미지를 표시한다.
2. IF Amazon 메인 이미지 URL을 가져올 수 없으면, THEN THE Product_Image SHALL 플레이스홀더 이미지를 대체 표시한다.
3. WHEN ScraperAPI를 통해 제품 데이터를 가져오면, THE ScraperAPI_Route SHALL HTML에서 제품 메인 이미지 URL을 파싱하여 응답에 포함한다.
4. WHEN Keepa API를 통해 제품 데이터를 가져오면, THE Keepa_Route SHALL 제품 이미지 URL을 응답에 포함한다.
5. WHEN API 응답에 유효한 이미지 URL이 포함되면, THE Store SHALL 해당 제품의 image_url 필드를 업데이트한다.
6. THE Product_Image SHALL Next.js Image 컴포넌트의 외부 이미지 도메인 설정에 Amazon 이미지 호스트(images-na.ssl-images-amazon.com, m.media-amazon.com)를 포함한다.
7. IF Product_Image 로딩 중 오류가 발생하면, THEN THE Product_Image SHALL 오류 상태를 감지하고 플레이스홀더 이미지로 대체 표시한다.

### 요구사항 4: 대시보드 통계 카드 표시 항목 변경

**사용자 스토리:** 사용자로서, 대시보드에서 "데이터 포인트" 수 대신 "마지막 업데이트 시간"을 확인하고 싶다. 이를 통해 데이터의 최신성을 즉시 파악할 수 있다.

#### 인수 조건

1. THE Stats_Card SHALL 기존 "데이터 포인트" 카드를 "마지막 업데이트 시간" 카드로 대체한다.
2. THE Stats_Card SHALL 모든 PriceObservation 중 가장 최근 observed_at 타임스탬프를 기준으로 Last_Update_Time을 계산한다.
3. THE Stats_Card SHALL Last_Update_Time을 상대 시간 형식(예: "3분 전", "1시간 전", "2일 전")으로 표시한다.
4. WHEN 가격 관측 데이터가 없으면, THE Stats_Card SHALL Last_Update_Time을 "—"으로 표시한다.
5. THE Stats_Card SHALL 한국어 및 영어 번역을 모두 지원한다.
6. THE Stats_Card SHALL "데이터 포인트" 관련 아이콘(Database)을 시간 관련 아이콘(Clock)으로 변경한다.
