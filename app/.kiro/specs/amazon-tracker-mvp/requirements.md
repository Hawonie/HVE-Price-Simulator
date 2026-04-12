# Requirements Document

## Introduction

Amazon Product Tracker MVP is a Python-based backend service that tracks publicly visible product data from three Amazon marketplaces (AE, SA, AU). The service uses browser automation (Playwright) and HTML parsing (BeautifulSoup/lxml) to scrape product detail pages, stores time-series snapshots in PostgreSQL, detects changes in price, reviews, and availability, and exposes the data through a FastAPI REST API and CSV export. This service complements the existing ZonTrack Next.js frontend.

## Glossary

- **Tracker**: The overall Python backend service responsible for scraping, storing, and serving Amazon product data
- **ASIN**: Amazon Standard Identification Number, a 10-character alphanumeric identifier unique to each product within a marketplace
- **Marketplace**: One of the three supported Amazon storefronts: AE (amazon.ae), SA (amazon.sa), AU (amazon.com.au)
- **Product_URL**: A full Amazon product detail page URL containing the marketplace domain and ASIN
- **Scraper**: The Playwright-based module that loads Amazon product pages and extracts structured data
- **Parser**: The BeautifulSoup/lxml-based module that extracts specific fields from the scraped HTML
- **Snapshot**: A single point-in-time record of all extracted product data fields captured during one crawl
- **Product_Master**: The persistent record storing a product's identity (ASIN, marketplace) and latest metadata
- **Crawl**: A single execution of the scraping pipeline for one product
- **Scheduler**: The APScheduler or Celery component that triggers crawls at configured intervals
- **Change_Detector**: The module that compares the latest snapshot against the previous snapshot to identify differences
- **API**: The FastAPI-based REST interface for reading product data and price history
- **CSV_Exporter**: The module that generates CSV files from stored product and snapshot data
- **Fallback_Selector**: An alternative CSS/XPath selector used when the primary selector fails to locate an element on the page

## Requirements

### Requirement 1: Product Input and Normalization

**User Story:** As a user, I want to submit Amazon product URLs or ASINs so that the Tracker can identify and begin monitoring products across supported marketplaces.

#### Acceptance Criteria

1. WHEN a valid Product_URL from a supported Marketplace is provided, THE Tracker SHALL extract the ASIN and Marketplace from the URL
2. WHEN a bare ASIN is provided with a Marketplace identifier, THE Tracker SHALL construct the canonical Product_URL for that Marketplace
3. WHEN a Product_URL from an unsupported domain is provided, THE Tracker SHALL return an error indicating the Marketplace is not supported
4. WHEN a string that does not match the ASIN format (10 alphanumeric characters) is provided, THE Tracker SHALL return a validation error
5. THE Tracker SHALL normalize every valid input into a (Marketplace, ASIN) pair before further processing
6. WHEN a Product_URL is provided, THE Tracker SHALL auto-detect the Marketplace from the domain without requiring the user to specify it

### Requirement 2: Product Page Scraping

**User Story:** As a user, I want the Tracker to load Amazon product pages using browser automation so that it can extract up-to-date product information even from JavaScript-rendered content.

#### Acceptance Criteria

1. WHEN a Crawl is initiated for a product, THE Scraper SHALL load the product detail page using Playwright for the corresponding Marketplace
2. THE Scraper SHALL use async Playwright consistently across all scraping operations
3. WHEN the primary CSS selector for a field fails to match any element, THE Scraper SHALL attempt each configured Fallback_Selector for that field in order
4. IF a product page fails to load within 30 seconds, THEN THE Scraper SHALL retry the request up to 3 times with exponential backoff
5. IF all retry attempts are exhausted, THEN THE Scraper SHALL log the failure with the ASIN, Marketplace, and error details, and skip the product for the current Crawl cycle
6. THE Scraper SHALL configure marketplace-specific settings (language, currency, domain) through environment variables or a configuration file

### Requirement 3: Data Extraction and Parsing

**User Story:** As a user, I want the Tracker to extract structured product data fields from each product page so that I can monitor product attributes over time.

#### Acceptance Criteria

1. WHEN a product page is successfully loaded, THE Parser SHALL extract the following fields: asin, marketplace, url, title, brand, current_price, list_price, rating, review_count, availability_text, main_image_url, bullet_points, and seller_info
2. THE Parser SHALL return clean parsed values (strings, numbers, or null) and not raw HTML fragments
3. WHEN current_price is extracted, THE Parser SHALL parse it into a numeric decimal value with the currency code as a separate field
4. WHEN list_price is not displayed on the page, THE Parser SHALL set the list_price field to null
5. WHEN seller_info is not visible on the page, THE Parser SHALL set the seller_info field to null
6. WHEN rating is extracted, THE Parser SHALL parse it into a numeric decimal value between 0.0 and 5.0
7. WHEN review_count is extracted, THE Parser SHALL parse it into an integer, removing commas and locale-specific formatting
8. THE Parser SHALL maintain separate Fallback_Selector configurations for title, current_price, rating, review_count, main_image_url, and availability_text

### Requirement 4: Data Storage — Product Master

**User Story:** As a user, I want product identity and metadata stored persistently so that the Tracker can maintain a catalog of monitored products.

#### Acceptance Criteria

1. WHEN a new (Marketplace, ASIN) pair is encountered, THE Tracker SHALL create a new Product_Master record
2. WHEN a product is crawled and the Product_Master already exists, THE Tracker SHALL update the Product_Master with the latest metadata (title, brand, main_image_url)
3. THE Tracker SHALL enforce a unique constraint on the (marketplace, asin) pair in the Product_Master table
4. THE Product_Master SHALL store: asin, marketplace, url, title, brand, main_image_url, created_at, and updated_at timestamps

### Requirement 5: Data Storage — Time-Series Snapshots

**User Story:** As a user, I want every crawl result saved as a time-series snapshot so that I can analyze product data trends over time.

#### Acceptance Criteria

1. WHEN a Crawl completes successfully for a product, THE Tracker SHALL save exactly one Snapshot record
2. THE Snapshot SHALL store: product reference, current_price, currency, list_price, rating, review_count, availability_text, seller_info, bullet_points, and crawl_timestamp
3. THE Tracker SHALL record the crawl_timestamp as the UTC time when the Crawl was initiated
4. THE Tracker SHALL retain all Snapshot records without automatic deletion

### Requirement 6: Change Detection

**User Story:** As a user, I want the Tracker to detect changes in price, review count, and availability so that I can be aware of significant product updates.

#### Acceptance Criteria

1. WHEN a new Snapshot is saved, THE Change_Detector SHALL compare current_price against the previous Snapshot for the same product
2. WHEN a new Snapshot is saved, THE Change_Detector SHALL compare review_count against the previous Snapshot for the same product
3. WHEN a new Snapshot is saved, THE Change_Detector SHALL compare availability_text against the previous Snapshot for the same product
4. WHEN a change is detected in any monitored field, THE Change_Detector SHALL create a change record containing the product reference, field name, old value, new value, and detection timestamp
5. WHEN no previous Snapshot exists for a product, THE Change_Detector SHALL skip comparison and record no changes

### Requirement 7: CSV Export

**User Story:** As a user, I want to export product data and price history as CSV files so that I can analyze the data in spreadsheet tools.

#### Acceptance Criteria

1. WHEN a CSV export is requested for a product, THE CSV_Exporter SHALL generate a file containing all Snapshot records for that product ordered by crawl_timestamp ascending
2. THE CSV_Exporter SHALL include column headers matching the Snapshot field names
3. WHEN a CSV export is requested for a product with no Snapshots, THE CSV_Exporter SHALL return an empty CSV file with headers only
4. THE CSV_Exporter SHALL format timestamps in ISO 8601 format (UTC)

### Requirement 8: REST API

**User Story:** As a user, I want REST API endpoints so that the ZonTrack frontend and other clients can read product data and price history programmatically.

#### Acceptance Criteria

1. THE API SHALL expose an endpoint to retrieve the latest Snapshot for a given product by Marketplace and ASIN
2. THE API SHALL expose an endpoint to retrieve the full price history (all Snapshots) for a given product by Marketplace and ASIN
3. THE API SHALL expose an endpoint to add a new product for tracking by accepting a Product_URL or ASIN with Marketplace
4. THE API SHALL expose an endpoint to list all tracked products
5. THE API SHALL expose an endpoint to trigger a CSV export for a given product and return the file as a download
6. WHEN a requested product does not exist, THE API SHALL return HTTP 404 with a descriptive error message
7. THE API SHALL return all responses in JSON format except for CSV export endpoints

### Requirement 9: Scheduled Crawling

**User Story:** As a user, I want the Tracker to automatically crawl products on a configurable schedule so that data stays current without manual intervention.

#### Acceptance Criteria

1. THE Scheduler SHALL trigger Crawls for all tracked products at a configurable interval defined via environment variable
2. THE Scheduler SHALL process products sequentially or with a configurable concurrency limit to avoid overwhelming Amazon servers
3. WHEN a scheduled Crawl fails for a product, THE Scheduler SHALL log the failure and continue with the remaining products
4. THE Scheduler SHALL support being run as a background process alongside the API server

### Requirement 10: Code Quality and Configuration

**User Story:** As a developer, I want the codebase to follow Python best practices with modular structure, type hints, and proper error handling so that the code is maintainable and reliable.

#### Acceptance Criteria

1. THE Tracker SHALL organize code into the following modules: config, models, scrapers, services, api, scripts, and tests
2. THE Tracker SHALL use Python type hints on all function signatures and return types
3. THE Tracker SHALL read all configurable values (database URL, crawl interval, retry count, timeouts) from environment variables with sensible defaults
4. THE Tracker SHALL log all significant operations (crawl start, crawl success, crawl failure, change detection, API requests) using Python's logging module
5. IF an unhandled exception occurs during a Crawl, THEN THE Tracker SHALL catch the exception, log the full traceback, and continue operation without crashing the service
6. THE Tracker SHALL implement retry logic with exponential backoff for all network operations (page loads, database connections)
