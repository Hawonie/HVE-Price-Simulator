# Implementation Plan: Amazon Tracker MVP

## Overview

Build a standalone Python backend service (`amazon-tracker-mvp/`) that scrapes Amazon product pages (AE, SA, AU), stores time-series snapshots in PostgreSQL, detects changes, and exposes data via FastAPI REST API and CSV export. Implementation proceeds bottom-up: project scaffold → config → database → utilities → scraper → services → API → scheduler → scripts.

## Tasks

- [x] 1. Project scaffold and configuration
  - [x] 1.1 Create project directory structure and dependency files
    - Create `amazon-tracker-mvp/` directory with all subdirectories: `app/`, `app/models/`, `app/schemas/`, `app/scrapers/`, `app/services/`, `app/api/`, `app/utils/`, `scripts/`, `tests/`
    - Create all `__init__.py` files
    - Create `requirements.txt` with: fastapi, uvicorn, sqlalchemy[asyncio], asyncpg, playwright, beautifulsoup4, lxml, pydantic-settings, apscheduler, hypothesis, pytest, pytest-asyncio, httpx
    - Create `pyproject.toml` with project metadata and pytest configuration
    - Create `.env.example` with all `TRACKER_` prefixed environment variables and defaults
    - _Requirements: 10.1_

  - [x] 1.2 Implement configuration module (`app/config.py`)
    - Implement `Settings` class using `pydantic-settings` with all fields: `database_url`, `playwright_headless`, `page_load_timeout`, `retry_count`, `retry_base_delay`, `crawl_interval_minutes`, `crawl_concurrency`, `supported_marketplaces`, `log_level`
    - All fields must have sensible defaults and use `TRACKER_` env prefix
    - Add `MARKETPLACE_CONFIG` dict with domain, currency, locale, timezone per marketplace
    - _Requirements: 10.3, 2.6_

  - [ ]* 1.3 Write property test for configuration defaults and env override
    - **Property 13: Configuration Defaults and Environment Override**
    - **Validates: Requirements 10.3**

- [x] 2. Database layer and models
  - [x] 2.1 Implement database setup (`app/database.py`)
    - Create `Base` declarative base class
    - Implement `get_engine()` and `get_session_factory()` async functions
    - _Requirements: 10.1_

  - [x] 2.2 Implement SQLAlchemy models
    - Create `Product` model in `app/models/product.py` with unique constraint on (marketplace, asin), relationships to snapshots and changes
    - Create `ProductSnapshot` model in `app/models/snapshot.py` with foreign key to Product, JSON column for bullet_points, index on crawl_timestamp
    - Create `ChangeRecord` model in `app/models/change.py` with foreign key to Product, index on product_id
    - All models must use type hints on columns
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 6.4_

  - [x] 2.3 Implement Pydantic schemas (`app/schemas/product.py`)
    - Create `AddProductRequest`, `ProductResponse`, `SnapshotResponse`, `ChangeResponse` schemas
    - Enable `from_attributes` model config for ORM compatibility
    - _Requirements: 8.3, 8.7_

  - [x] 2.4 Create database init script (`scripts/init_db.py`)
    - Script to create all tables using `Base.metadata.create_all()`
    - _Requirements: 10.1_

- [x] 3. URL/ASIN normalizer utility
  - [x] 3.1 Implement normalizer (`app/utils/normalizer.py`)
    - Implement `NormalizedProduct` frozen dataclass
    - Implement `normalize_input()` accepting URL or bare ASIN + marketplace
    - Implement `extract_asin_from_url()` supporting `/dp/ASIN` and `/gp/product/ASIN` patterns
    - Implement `detect_marketplace_from_url()` for all supported domains
    - Implement `build_canonical_url()` constructing `https://{domain}/dp/{asin}`
    - Raise `ValueError` for invalid ASIN format or unsupported marketplace
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [ ]* 3.2 Write property test for URL/ASIN round-trip
    - **Property 1: URL/ASIN Normalization Round-Trip**
    - **Validates: Requirements 1.1, 1.2, 1.5, 1.6**

  - [ ]* 3.3 Write property test for invalid input rejection
    - **Property 2: Invalid Input Rejection**
    - **Validates: Requirements 1.3, 1.4**

  - [ ]* 3.4 Write unit tests for normalizer edge cases
    - Test URLs with trailing slashes, query parameters, ref tags
    - Test case sensitivity of ASIN
    - Test all three marketplace domains including www and non-www variants
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 4. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Scraper module
  - [x] 5.1 Implement fallback CSS selectors (`app/scrapers/selectors.py`)
    - Define `FieldSelectors` dataclass with ordered list of CSS selectors
    - Define `SELECTOR_CONFIG` dict with fallback chains for: title, current_price, list_price, rating, review_count, main_image_url, availability_text
    - _Requirements: 2.3, 3.8_

  - [x] 5.2 Implement Playwright browser manager (`app/scrapers/browser.py`)
    - Implement `BrowserManager` class with `start()`, `new_context()`, `close()` methods
    - `new_context()` must set marketplace-specific locale and timezone from `MARKETPLACE_CONFIG`
    - Use headless mode from settings
    - _Requirements: 2.1, 2.2, 2.6_

  - [x] 5.3 Implement retry utility (`app/utils/retry.py`)
    - Implement `retry_with_backoff()` async function with exponential backoff
    - Delay formula: `base_delay * 2^(attempt-1)`
    - Log each retry attempt at WARNING level, final failure at ERROR level
    - _Requirements: 2.4, 10.5, 10.6_

  - [ ]* 5.4 Write property test for exponential backoff delay pattern
    - **Property 14: Exponential Backoff Delay Pattern**
    - **Validates: Requirements 10.6**

  - [x] 5.5 Implement scraping orchestrator (`app/scrapers/scraper.py`)
    - Implement `ParsedProduct` dataclass with all extracted fields
    - Implement `scrape_product()` async function that loads page via Playwright, extracts fields using fallback selectors, parses prices/ratings/reviews into typed values
    - Use `retry_with_backoff()` for page loading
    - Set field to `None` when all selectors fail or parsing fails
    - Log failures with ASIN, marketplace, and error details
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [ ]* 5.6 Write property tests for parser output
    - **Property 4: Parser Output Completeness and Cleanliness**
    - **Validates: Requirements 3.1, 3.2**
    - **Property 5: Price Parsing Produces Numeric Value with Currency**
    - **Validates: Requirements 3.3**
    - **Property 6: Rating Parsing Within Bounds**
    - **Validates: Requirements 3.6**
    - **Property 7: Review Count Parsing Strips Formatting**
    - **Validates: Requirements 3.7**

  - [ ]* 5.7 Write property test for fallback selector ordering
    - **Property 3: Fallback Selector Ordering**
    - **Validates: Requirements 2.3**

- [x] 6. Service layer
  - [x] 6.1 Implement product service (`app/services/product_service.py`)
    - Implement `upsert_product()` — create or update Product_Master by (marketplace, asin), enforce unique constraint
    - Implement `get_product()` — fetch by marketplace + asin
    - Implement `list_products()` — return all tracked products
    - All functions async, use type hints
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 8.3, 8.4_

  - [ ]* 6.2 Write property test for product upsert idempotence
    - **Property 8: Product Upsert Idempotence**
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [x] 6.3 Implement snapshot service (`app/services/snapshot_service.py`)
    - Implement `save_snapshot()` — insert one snapshot per crawl
    - Implement `get_latest_snapshot()` — fetch most recent snapshot for a product
    - Implement `get_snapshot_history()` — fetch all snapshots ordered by crawl_timestamp ascending
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 8.1, 8.2_

  - [ ]* 6.4 Write property test for snapshot accumulation
    - **Property 9: Snapshot Accumulation**
    - **Validates: Requirements 5.1, 5.4**

  - [x] 6.5 Implement change detector (`app/services/change_detector.py`)
    - Implement `detect_changes()` comparing new snapshot against previous for monitored fields: current_price, review_count, availability_text
    - Create `ChangeRecord` for each differing field with old_value, new_value, field_name, detected_at
    - Return empty list when no previous snapshot exists
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 6.6 Write property test for change detection
    - **Property 10: Change Detection for Monitored Fields**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

  - [x] 6.7 Implement CSV exporter (`app/services/csv_exporter.py`)
    - Implement `export_snapshots_csv()` producing CSV string from snapshot list
    - Headers match snapshot field names, rows ordered by crawl_timestamp ascending
    - Timestamps in ISO 8601 UTC format
    - Return headers-only CSV for empty snapshot list
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 6.8 Write property test for CSV export format
    - **Property 11: CSV Export Format Correctness**
    - **Validates: Requirements 7.1, 7.2, 7.4**

- [ ] 7. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. FastAPI REST API
  - [x] 8.1 Implement API routes (`app/api/routes.py`)
    - `POST /api/v1/products` — add product by URL or ASIN+marketplace, validate input via normalizer, upsert product, return 201
    - `GET /api/v1/products` — list all tracked products
    - `GET /api/v1/products/{marketplace}/{asin}/latest` — latest snapshot, return 404 if product not found
    - `GET /api/v1/products/{marketplace}/{asin}/history` — all snapshots as JSON array, return 404 if product not found
    - `GET /api/v1/products/{marketplace}/{asin}/export` — CSV download via `StreamingResponse`, return 404 if product not found
    - All responses JSON except CSV endpoint
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

  - [x] 8.2 Implement FastAPI app entry point (`app/main.py`)
    - Create FastAPI app instance, include router
    - Add lifespan handler for browser manager startup/shutdown and scheduler startup
    - Configure logging based on settings
    - _Requirements: 10.1, 10.4_

  - [ ]* 8.3 Write unit tests for API 404 responses
    - **Property 12: API 404 for Non-Existent Products**
    - Test latest, history, and export endpoints return 404 with JSON error body for non-existent products
    - Use `httpx.AsyncClient` with FastAPI test client
    - **Validates: Requirements 8.6**

- [x] 9. Scheduler integration
  - [x] 9.1 Implement scheduler service (`app/services/scheduler.py`)
    - Implement `crawl_all_products()` — iterate all tracked products, scrape each, save snapshot, detect changes
    - Catch exceptions per product so one failure doesn't stop the batch
    - Implement `setup_scheduler()` — configure `AsyncIOScheduler` with interval from settings
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 10. Scripts and wiring
  - [x] 10.1 Create manual crawl script (`scripts/manual_crawl.py`)
    - Accept marketplace and ASIN as CLI arguments
    - Run a single crawl, print results
    - _Requirements: 10.1_

  - [x] 10.2 Wire all components in `app/main.py`
    - Ensure database session dependency injection works across all routes
    - Ensure browser manager is shared across scraper calls
    - Ensure scheduler starts on app startup and stops on shutdown
    - _Requirements: 9.4, 10.1_

- [x] 11. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (14 properties total)
- Unit tests validate specific examples and edge cases
- The project lives in `amazon-tracker-mvp/` at the workspace root, separate from the Next.js frontend
