# Design Document — Amazon Tracker MVP

## Overview

The Amazon Tracker MVP is a standalone Python backend service that complements the existing ZonTrack Next.js frontend. It replaces the current ScraperAPI/Keepa proxy routes (`app/api/scraper/route.ts`, `app/api/keepa/route.ts`) with a dedicated, persistent scraping and storage pipeline.

The service uses async Playwright for browser automation, BeautifulSoup/lxml for HTML parsing, PostgreSQL for persistent storage, and FastAPI for the REST API layer. It targets three Amazon marketplaces: AE (`amazon.ae`), SA (`amazon.sa`), and AU (`amazon.com.au`).

### Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Browser automation | Async Playwright | Handles JS-rendered Amazon pages; async avoids blocking the event loop |
| HTML parsing | BeautifulSoup4 + lxml | Fast, well-documented, supports CSS selectors natively |
| Database | PostgreSQL + SQLAlchemy (async) | Time-series snapshots need relational integrity; async driver (`asyncpg`) matches the async stack |
| API framework | FastAPI | Native async, auto-generated OpenAPI docs, Pydantic validation |
| Scheduler | APScheduler (AsyncIOScheduler) | Lightweight, runs in-process alongside FastAPI, no external broker needed |
| Configuration | pydantic-settings + `.env` | Type-safe config with environment variable support |
| CSV export | Python `csv` module via `StreamingResponse` | Simple, no extra dependency, streams large exports |

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "ZonTrack Frontend (Next.js)"
        FE[Next.js App]
    end

    subgraph "Amazon Tracker MVP (Python)"
        API[FastAPI REST API]
        SCR[Scraper Module<br/>Async Playwright]
        PAR[Parser Module<br/>BeautifulSoup/lxml]
        CHG[Change Detector]
        CSV[CSV Exporter]
        SCH[APScheduler]
        CFG[Config<br/>pydantic-settings]
    end

    subgraph "External"
        AMZ[Amazon Product Pages<br/>AE / SA / AU]
        DB[(PostgreSQL)]
    end

    FE -->|HTTP| API
    API --> SCR
    API --> CSV
    API --> DB
    SCR -->|loads page| AMZ
    SCR -->|raw HTML| PAR
    PAR -->|parsed data| SCR
    SCR -->|snapshot| DB
    SCR -->|snapshot| CHG
    CHG -->|change records| DB
    SCH -->|triggers crawl| SCR
    CFG -.->|config| API
    CFG -.->|config| SCR
    CFG -.->|config| SCH
```

### Request Flow — Crawl Pipeline

```mermaid
sequenceDiagram
    participant S as Scheduler / API
    participant SC as Scraper
    participant PW as Playwright
    participant AMZ as Amazon
    participant PA as Parser
    participant DB as PostgreSQL
    participant CD as Change Detector

    S->>SC: crawl(marketplace, asin)
    SC->>PW: launch browser, goto product URL
    PW->>AMZ: HTTP GET product page
    AMZ-->>PW: HTML response
    PW-->>SC: page content (HTML)
    SC->>PA: parse(html, marketplace)
    PA-->>SC: ParsedProduct
    SC->>DB: upsert Product_Master
    SC->>DB: insert Snapshot
    SC->>CD: detect_changes(product_id, new_snapshot)
    CD->>DB: fetch previous snapshot
    CD->>DB: insert change records (if any)
    CD-->>SC: changes[]
```

## Components and Interfaces

### Project Structure

```
amazon-tracker-mvp/
├── app/
│   ├── __init__.py
│   ├── config.py              # pydantic-settings configuration
│   ├── main.py                # FastAPI app entry point + scheduler startup
│   ├── database.py            # SQLAlchemy async engine + session factory
│   ├── models/
│   │   ├── __init__.py
│   │   ├── product.py         # Product SQLAlchemy model
│   │   ├── snapshot.py        # ProductSnapshot SQLAlchemy model
│   │   └── change.py          # ChangeRecord SQLAlchemy model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── product.py         # Pydantic request/response schemas
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── browser.py         # Playwright browser lifecycle management
│   │   ├── scraper.py         # Main scraping orchestrator
│   │   └── selectors.py       # CSS selector configs per marketplace/field
│   ├── services/
│   │   ├── __init__.py
│   │   ├── product_service.py # Product CRUD operations
│   │   ├── snapshot_service.py# Snapshot storage + retrieval
│   │   ├── change_detector.py # Change detection logic
│   │   ├── csv_exporter.py    # CSV generation
│   │   └── scheduler.py       # APScheduler setup + crawl job
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py          # FastAPI router with all endpoints
│   └── utils/
│       ├── __init__.py
│       └── normalizer.py      # URL/ASIN parsing and normalization
├── scripts/
│   ├── init_db.py             # Database table creation script
│   └── manual_crawl.py        # One-off crawl script for testing
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Shared fixtures
│   ├── test_normalizer.py
│   ├── test_parser.py
│   ├── test_change_detector.py
│   ├── test_csv_exporter.py
│   └── test_properties.py    # Property-based tests
├── .env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Component Interfaces

#### 1. `app/config.py` — Configuration

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/amazon_tracker"
    
    # Scraper
    playwright_headless: bool = True
    page_load_timeout: int = 30  # seconds
    retry_count: int = 3
    retry_base_delay: float = 2.0  # seconds, exponential backoff base
    
    # Scheduler
    crawl_interval_minutes: int = 360  # 6 hours default
    crawl_concurrency: int = 1  # sequential by default
    
    # Marketplace defaults
    supported_marketplaces: list[str] = ["AE", "SA", "AU"]
    
    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_prefix": "TRACKER_"}
```

#### 2. `app/utils/normalizer.py` — URL/ASIN Normalization

```python
import re
from dataclasses import dataclass

MARKETPLACE_DOMAINS: dict[str, str] = {
    "www.amazon.ae": "AE",
    "amazon.ae": "AE",
    "www.amazon.sa": "SA",
    "amazon.sa": "SA",
    "www.amazon.com.au": "AU",
    "amazon.com.au": "AU",
}

MARKETPLACE_TO_DOMAIN: dict[str, str] = {
    "AE": "www.amazon.ae",
    "SA": "www.amazon.sa",
    "AU": "www.amazon.com.au",
}

ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$")

@dataclass(frozen=True)
class NormalizedProduct:
    marketplace: str  # "AE", "SA", "AU"
    asin: str         # 10-char alphanumeric
    url: str          # canonical URL

def normalize_input(input_str: str, marketplace: str | None = None) -> NormalizedProduct:
    """
    Accepts a Product_URL or bare ASIN (+ marketplace).
    Returns a NormalizedProduct or raises ValueError.
    """
    ...

def extract_asin_from_url(url: str) -> str:
    """Extract ASIN from Amazon product URL patterns (/dp/ASIN, /gp/product/ASIN)."""
    ...

def detect_marketplace_from_url(url: str) -> str:
    """Detect marketplace code from URL domain. Raises ValueError if unsupported."""
    ...

def build_canonical_url(marketplace: str, asin: str) -> str:
    """Build https://{domain}/dp/{asin} URL."""
    ...
```

#### 3. `app/scrapers/selectors.py` — Fallback CSS Selectors

```python
from dataclasses import dataclass, field

@dataclass
class FieldSelectors:
    """Ordered list of CSS selectors for a single field. First match wins."""
    selectors: list[str]

# Per-field fallback selector chains
SELECTOR_CONFIG: dict[str, FieldSelectors] = {
    "title": FieldSelectors(selectors=[
        "#productTitle",
        "#title span",
        "h1.product-title-word-break span",
    ]),
    "current_price": FieldSelectors(selectors=[
        "span.a-price .a-offscreen",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "span.priceToPay .a-offscreen",
        "#corePrice_feature_div .a-offscreen",
    ]),
    "list_price": FieldSelectors(selectors=[
        "span.a-price.a-text-price .a-offscreen",
        "#priceblock_listprice",
        "span.priceBlockStrikePriceString",
    ]),
    "rating": FieldSelectors(selectors=[
        "#acrPopover span.a-icon-alt",
        "span[data-hook='rating-out-of-text']",
        "#averageCustomerReviews span.a-icon-alt",
    ]),
    "review_count": FieldSelectors(selectors=[
        "#acrCustomerReviewText",
        "span[data-hook='total-review-count']",
        "#acrCustomerReviewLink span",
    ]),
    "main_image_url": FieldSelectors(selectors=[
        "#landingImage",
        "#imgBlkFront",
        "#main-image",
    ]),
    "availability_text": FieldSelectors(selectors=[
        "#availability span",
        "#outOfStock span",
        "#deliveryMessageMirId span",
    ]),
}
```

#### 4. `app/scrapers/browser.py` — Playwright Browser Lifecycle

```python
from playwright.async_api import async_playwright, Browser, BrowserContext

class BrowserManager:
    """Manages a single Playwright browser instance for reuse across crawls."""
    
    async def start(self) -> None:
        """Launch headless Chromium browser."""
        ...

    async def new_context(self, marketplace: str) -> BrowserContext:
        """Create a new browser context with marketplace-specific locale/timezone."""
        ...

    async def close(self) -> None:
        """Close browser and Playwright instance."""
        ...
```

#### 5. `app/scrapers/scraper.py` — Scraping Orchestrator

```python
from app.scrapers.browser import BrowserManager
from app.scrapers.selectors import SELECTOR_CONFIG

@dataclass
class ParsedProduct:
    asin: str
    marketplace: str
    url: str
    title: str | None
    brand: str | None
    current_price: float | None
    currency: str | None
    list_price: float | None
    rating: float | None
    review_count: int | None
    availability_text: str | None
    main_image_url: str | None
    bullet_points: list[str]
    seller_info: str | None

async def scrape_product(
    browser_manager: BrowserManager,
    marketplace: str,
    asin: str,
    settings: Settings,
) -> ParsedProduct:
    """
    Load product page with Playwright, extract fields using fallback selectors.
    Retries up to settings.retry_count times with exponential backoff.
    """
    ...
```

#### 6. `app/services/change_detector.py` — Change Detection

```python
from dataclasses import dataclass
from datetime import datetime

MONITORED_FIELDS = ["current_price", "review_count", "availability_text"]

@dataclass
class ChangeRecord:
    product_id: int
    field_name: str
    old_value: str | None
    new_value: str | None
    detected_at: datetime

async def detect_changes(
    session: AsyncSession,
    product_id: int,
    new_snapshot: ProductSnapshot,
) -> list[ChangeRecord]:
    """
    Compare new_snapshot against the previous snapshot for the same product.
    Returns a list of ChangeRecords for any monitored fields that differ.
    Returns empty list if no previous snapshot exists.
    """
    ...
```

#### 7. `app/services/csv_exporter.py` — CSV Export

```python
import csv
import io

def export_snapshots_csv(snapshots: list[ProductSnapshot]) -> str:
    """
    Generate CSV string from snapshot records.
    Headers match snapshot field names. Timestamps in ISO 8601 UTC.
    Returns headers-only CSV if snapshots list is empty.
    """
    ...
```

#### 8. `app/api/routes.py` — FastAPI Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/v1")

# POST /api/v1/products          — Add product for tracking
# GET  /api/v1/products          — List all tracked products
# GET  /api/v1/products/{marketplace}/{asin}/latest  — Latest snapshot
# GET  /api/v1/products/{marketplace}/{asin}/history  — Full price history
# GET  /api/v1/products/{marketplace}/{asin}/export   — CSV download
```

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `POST` | `/api/v1/products` | Add product by URL or ASIN+marketplace | `201` with product JSON |
| `GET` | `/api/v1/products` | List all tracked products | `200` with product list JSON |
| `GET` | `/api/v1/products/{marketplace}/{asin}/latest` | Latest snapshot | `200` JSON / `404` |
| `GET` | `/api/v1/products/{marketplace}/{asin}/history` | All snapshots (time-series) | `200` JSON / `404` |
| `GET` | `/api/v1/products/{marketplace}/{asin}/export` | CSV file download | `200` CSV / `404` |

#### 9. `app/services/scheduler.py` — APScheduler Integration

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def crawl_all_products(session_factory, browser_manager, settings):
    """Crawl all tracked products sequentially or with concurrency limit."""
    ...

def setup_scheduler(session_factory, browser_manager, settings) -> AsyncIOScheduler:
    """Configure and return scheduler with crawl interval from settings."""
    ...
```


## Data Models

### Entity Relationship Diagram

```mermaid
erDiagram
    Product ||--o{ ProductSnapshot : "has many"
    Product ||--o{ ChangeRecord : "has many"

    Product {
        int id PK
        string asin
        string marketplace
        string url
        string title
        string brand
        string main_image_url
        datetime created_at
        datetime updated_at
    }

    ProductSnapshot {
        int id PK
        int product_id FK
        float current_price
        string currency
        float list_price
        float rating
        int review_count
        string availability_text
        string seller_info
        json bullet_points
        datetime crawl_timestamp
    }

    ChangeRecord {
        int id PK
        int product_id FK
        string field_name
        string old_value
        string new_value
        datetime detected_at
    }
```

### SQLAlchemy Models

#### `app/models/product.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(10), nullable=False, index=True)
    marketplace = Column(String(5), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    title = Column(String(1000), nullable=True)
    brand = Column(String(200), nullable=True)
    main_image_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("marketplace", "asin", name="uq_marketplace_asin"),
    )

    snapshots = relationship("ProductSnapshot", back_populates="product", cascade="all, delete-orphan")
    changes = relationship("ChangeRecord", back_populates="product", cascade="all, delete-orphan")
```

#### `app/models/snapshot.py`

```python
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class ProductSnapshot(Base):
    __tablename__ = "product_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    current_price = Column(Float, nullable=True)
    currency = Column(String(5), nullable=True)
    list_price = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    availability_text = Column(String(500), nullable=True)
    seller_info = Column(String(500), nullable=True)
    bullet_points = Column(JSON, nullable=True)  # stored as JSON array
    crawl_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    product = relationship("Product", back_populates="snapshots")
```

#### `app/models/change.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class ChangeRecord(Base):
    __tablename__ = "change_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(50), nullable=False)
    old_value = Column(String(500), nullable=True)
    new_value = Column(String(500), nullable=True)
    detected_at = Column(DateTime(timezone=True), nullable=False)

    product = relationship("Product", back_populates="changes")
```

#### `app/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

async def get_engine(database_url: str):
    return create_async_engine(database_url, echo=False)

async def get_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

### Pydantic Schemas (`app/schemas/product.py`)

```python
from pydantic import BaseModel, Field
from datetime import datetime

class AddProductRequest(BaseModel):
    url: str | None = None
    asin: str | None = None
    marketplace: str | None = None

class ProductResponse(BaseModel):
    id: int
    asin: str
    marketplace: str
    url: str
    title: str | None
    brand: str | None
    main_image_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class SnapshotResponse(BaseModel):
    id: int
    product_id: int
    current_price: float | None
    currency: str | None
    list_price: float | None
    rating: float | None
    review_count: int | None
    availability_text: str | None
    seller_info: str | None
    bullet_points: list[str] | None
    crawl_timestamp: datetime

    model_config = {"from_attributes": True}

class ChangeResponse(BaseModel):
    id: int
    product_id: int
    field_name: str
    old_value: str | None
    new_value: str | None
    detected_at: datetime

    model_config = {"from_attributes": True}
```

### Marketplace Configuration

```python
MARKETPLACE_CONFIG: dict[str, dict] = {
    "AE": {
        "domain": "www.amazon.ae",
        "currency": "AED",
        "locale": "en-AE",
        "timezone": "Asia/Dubai",
    },
    "SA": {
        "domain": "www.amazon.sa",
        "currency": "SAR",
        "locale": "en-SA",
        "timezone": "Asia/Riyadh",
    },
    "AU": {
        "domain": "www.amazon.com.au",
        "currency": "AUD",
        "locale": "en-AU",
        "timezone": "Australia/Sydney",
    },
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: URL/ASIN Normalization Round-Trip

*For any* supported marketplace and any valid ASIN, constructing a canonical URL from (marketplace, ASIN) and then parsing that URL back should yield the same (marketplace, ASIN) pair. Conversely, *for any* valid Amazon product URL from a supported marketplace, extracting (marketplace, ASIN) and reconstructing the URL should produce a URL with the same domain and ASIN.

**Validates: Requirements 1.1, 1.2, 1.5, 1.6**

### Property 2: Invalid Input Rejection

*For any* string that does not match the ASIN format (10 alphanumeric characters), the normalizer should raise a validation error. *For any* URL whose domain is not in the supported marketplace list, the normalizer should raise an unsupported marketplace error.

**Validates: Requirements 1.3, 1.4**

### Property 3: Fallback Selector Ordering

*For any* field and any HTML document where only the Nth fallback selector matches (and selectors 1..N-1 do not match), the parser should still successfully extract the field value using the Nth selector.

**Validates: Requirements 2.3**

### Property 4: Parser Output Completeness and Cleanliness

*For any* valid product page HTML, the parser output should contain all specified fields (title, current_price, rating, review_count, availability_text, main_image_url, etc.) as keys, and no field value should contain raw HTML tags.

**Validates: Requirements 3.1, 3.2**

### Property 5: Price Parsing Produces Numeric Value with Currency

*For any* price string in any supported marketplace format (e.g., "AED 199.00", "SAR 1,299.99", "A$49.95"), parsing should produce a non-negative float for the price and a valid 3-letter currency code as a separate field.

**Validates: Requirements 3.3**

### Property 6: Rating Parsing Within Bounds

*For any* rating string extracted from a product page (e.g., "4.5 out of 5 stars"), the parsed numeric value should be a float in the range [0.0, 5.0].

**Validates: Requirements 3.6**

### Property 7: Review Count Parsing Strips Formatting

*For any* review count string with commas or locale-specific thousand separators (e.g., "1,234 ratings", "12.345 Bewertungen"), parsing should produce a non-negative integer equal to the numeric value represented by the string.

**Validates: Requirements 3.7**

### Property 8: Product Upsert Idempotence

*For any* (marketplace, ASIN) pair, upserting a product record twice with different metadata should result in exactly one product record in the database, with the metadata from the second upsert.

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 9: Snapshot Accumulation

*For any* product and any sequence of N successful crawls, the total number of snapshot records for that product should be exactly N, and all N snapshots should be retained.

**Validates: Requirements 5.1, 5.4**

### Property 10: Change Detection for Monitored Fields

*For any* product with an existing snapshot, and *for any* new snapshot where at least one monitored field (current_price, review_count, availability_text) differs from the previous snapshot, the change detector should produce exactly one change record per differing field, each containing the correct old value, new value, and field name. When no fields differ, zero change records should be produced.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

### Property 11: CSV Export Format Correctness

*For any* list of snapshots (including empty), the CSV exporter should produce output where: (a) the first row contains the expected column headers, (b) subsequent rows appear in ascending crawl_timestamp order, (c) all timestamps are formatted in ISO 8601 UTC, and (d) the number of data rows equals the number of input snapshots.

**Validates: Requirements 7.1, 7.2, 7.4**

### Property 12: API 404 for Non-Existent Products

*For any* (marketplace, ASIN) pair that does not exist in the database, the API endpoints for latest snapshot, history, and CSV export should all return HTTP 404 with a JSON error body.

**Validates: Requirements 8.6**

### Property 13: Configuration Defaults and Environment Override

*For any* configuration field in Settings, the field should have a sensible default value. *For any* environment variable set with the `TRACKER_` prefix, the corresponding Settings field should reflect the environment variable's value instead of the default.

**Validates: Requirements 10.3**

### Property 14: Exponential Backoff Delay Pattern

*For any* retry sequence of length N with base delay B, the delay before retry attempt K (1-indexed) should be B × 2^(K-1) seconds (±jitter). The total number of retries should not exceed the configured retry_count.

**Validates: Requirements 10.6**

## Error Handling

### Error Categories and Strategies

| Category | Example | Strategy |
|---|---|---|
| Network / Page Load | Timeout, connection refused, HTTP 5xx | Retry with exponential backoff (up to `retry_count` attempts). Log each attempt. After exhaustion, log failure and skip product. |
| Selector Miss | Primary CSS selector returns no match | Try fallback selectors in order. If all fail, set field to `None`. |
| Parse Error | Price string can't be converted to float | Set field to `None`, log warning with raw value. Never crash. |
| Database Error | Connection lost, constraint violation | Retry connection with backoff. For constraint violations (duplicate product), treat as upsert. |
| Validation Error | Invalid ASIN format, unsupported marketplace | Return `400 Bad Request` with descriptive error message via API. Raise `ValueError` in service layer. |
| Unhandled Exception | Any unexpected error during crawl | Catch at crawl-job level, log full traceback, continue with next product. Service never crashes. |

### Retry Implementation

```python
import asyncio
import logging

logger = logging.getLogger(__name__)

async def retry_with_backoff(
    coro_factory,       # callable that returns a coroutine
    max_retries: int = 3,
    base_delay: float = 2.0,
    operation_name: str = "operation",
):
    """Execute an async operation with exponential backoff retry."""
    for attempt in range(1, max_retries + 1):
        try:
            return await coro_factory()
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"{operation_name} failed after {max_retries} attempts: {e}")
                raise
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(f"{operation_name} attempt {attempt} failed: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
```

### Logging Strategy

All significant operations are logged using Python's `logging` module:

- `INFO`: Crawl start, crawl success, change detected, API request served, scheduler tick
- `WARNING`: Selector fallback used, parse field returned None, retry attempt
- `ERROR`: Crawl failure after retries exhausted, database connection error, unhandled exception (with traceback)

## Testing Strategy

### Dual Testing Approach

The project uses both unit tests and property-based tests for comprehensive coverage:

- **Unit tests** (`pytest`): Verify specific examples, edge cases, integration points, and error conditions
- **Property-based tests** (`hypothesis`): Verify universal properties across randomly generated inputs

### Property-Based Testing Configuration

- **Library**: [Hypothesis](https://hypothesis.readthedocs.io/) for Python
- **Minimum iterations**: 100 per property test (`@settings(max_examples=100)`)
- **Each property test references its design document property via tag comment**
- **Tag format**: `# Feature: amazon-tracker-mvp, Property {N}: {title}`
- **Each correctness property is implemented by a single property-based test**

### Test Plan

| Test File | Type | Covers |
|---|---|---|
| `tests/test_normalizer.py` | Property + Unit | Properties 1, 2. URL round-trip, ASIN validation, unsupported domain rejection |
| `tests/test_parser.py` | Property + Unit | Properties 3, 4, 5, 6, 7. Fallback selectors, field extraction, price/rating/review parsing |
| `tests/test_change_detector.py` | Property + Unit | Property 10. Change detection across monitored fields, first-snapshot edge case |
| `tests/test_csv_exporter.py` | Property + Unit | Property 11. CSV format, ordering, ISO timestamps, empty-snapshot edge case |
| `tests/test_product_service.py` | Property + Unit | Properties 8, 9. Upsert idempotence, snapshot accumulation |
| `tests/test_api.py` | Unit (integration) | Property 12. 404 responses, endpoint existence, JSON content-type |
| `tests/test_config.py` | Property + Unit | Property 13. Default values, env override |
| `tests/test_retry.py` | Property + Unit | Property 14. Exponential backoff delay pattern |

### Unit Test Focus Areas

- Specific HTML samples from each marketplace (AE, SA, AU) for parser tests
- Edge cases: empty HTML, missing fields, malformed prices, zero reviews
- First-crawl scenario (no previous snapshot) for change detector
- Empty snapshot list for CSV exporter
- API error responses (400, 404, 500)
- Scheduler failure isolation (one product failure doesn't stop batch)

### Property Test Examples

```python
# Feature: amazon-tracker-mvp, Property 1: URL/ASIN Normalization Round-Trip
from hypothesis import given, settings
from hypothesis import strategies as st

valid_asin = st.from_regex(r"[A-Z0-9]{10}", fullmatch=True)
valid_marketplace = st.sampled_from(["AE", "SA", "AU"])

@given(marketplace=valid_marketplace, asin=valid_asin)
@settings(max_examples=100)
def test_url_asin_round_trip(marketplace, asin):
    url = build_canonical_url(marketplace, asin)
    result = normalize_input(url)
    assert result.marketplace == marketplace
    assert result.asin == asin
```

```python
# Feature: amazon-tracker-mvp, Property 10: Change Detection for Monitored Fields
@given(
    old_price=st.floats(min_value=0.01, max_value=10000, allow_nan=False),
    new_price=st.floats(min_value=0.01, max_value=10000, allow_nan=False),
    old_reviews=st.integers(min_value=0, max_value=1000000),
    new_reviews=st.integers(min_value=0, max_value=1000000),
)
@settings(max_examples=100)
def test_change_detection_monitored_fields(old_price, new_price, old_reviews, new_reviews):
    old_snapshot = make_snapshot(current_price=old_price, review_count=old_reviews)
    new_snapshot = make_snapshot(current_price=new_price, review_count=new_reviews)
    changes = detect_changes_sync(old_snapshot, new_snapshot)
    
    expected_changes = set()
    if old_price != new_price:
        expected_changes.add("current_price")
    if old_reviews != new_reviews:
        expected_changes.add("review_count")
    
    actual_fields = {c.field_name for c in changes}
    assert actual_fields == expected_changes
```
