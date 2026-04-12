# Requirements Document

## Introduction

Brand-Based Amazon ASIN Discovery & Price Tracker is a standalone local application that allows users to import a brand name, verify it against actual Amazon product pages, discover as many ASINs as possible for that brand across target marketplaces (amazon.ae, amazon.sa, amazon.com.au), and continuously track prices with change-only history. The application uses Python, Playwright (sync API), BeautifulSoup/lxml, SQLite, and a web UI built with FastAPI/Flask + Jinja2. This is a separate project from the existing amazon-tracker-mvp, focused on brand-level discovery rather than individual ASIN tracking.

## Glossary

- **Brand_Tracker**: The overall application system responsible for brand import, ASIN discovery, price tracking, and web UI
- **Brand_Importer**: The subsystem that handles brand name input, search, verification, and confidence-based import decisions
- **ASIN_Discoverer**: The subsystem that discovers ASINs for a verified brand using search results, pagination, related links, product detail pages, and brand store links
- **Price_Tracker**: The subsystem that crawls product pages and extracts pricing, availability, and seller data with selector fallbacks
- **Change_Detector**: The component that compares newly extracted prices against the last saved price and decides whether to insert a price_history record
- **Brand_Normalizer**: The component that normalizes brand name strings for fuzzy comparison (lowercasing, stripping whitespace, removing special characters)
- **Crawl_Manager**: The subsystem that creates, tracks, and logs crawl jobs with status, timing, and item counts
- **Web_UI**: The FastAPI or Flask + Jinja2 web interface providing brand input, marketplace selection, and data browsing pages
- **Marketplace**: One of the three supported Amazon regional sites: AE (amazon.ae), SA (amazon.sa), AU (amazon.com.au)
- **Confidence_Score**: A numeric value (0.0–1.0) representing how closely the detected brand on a product page matches the user-input brand name
- **Current_State**: The database table holding the latest known state of each ASIN (price, availability, seller) without historical duplication
- **Price_History**: The database table storing only price change events, not every crawl result
- **Selector_Fallback**: An ordered list of CSS selectors tried sequentially for each data field; the first match wins

## Requirements

### Requirement 1: Brand Input and Marketplace Selection

**User Story:** As a user, I want to enter a brand name and select target marketplaces, so that I can initiate brand discovery on specific Amazon regions.

#### Acceptance Criteria

1. THE Web_UI SHALL provide a text input field for entering a brand name and a marketplace selector with options AE, SA, AU, and ALL
2. WHEN the user submits a brand name with one or more selected marketplaces, THE Brand_Importer SHALL create a brand record with status "pending" and store the input_brand_name, selected marketplace, and created_at timestamp
3. IF the user submits an empty brand name, THEN THE Web_UI SHALL display a validation error message and prevent form submission
4. WHEN the user selects "ALL" as the marketplace, THE Brand_Importer SHALL initiate the import process for each of the three marketplaces (AE, SA, AU) independently

### Requirement 2: Brand Search on Amazon

**User Story:** As a user, I want the system to search for my brand on Amazon, so that candidate products can be found for brand verification.

#### Acceptance Criteria

1. WHEN a brand import is initiated for a marketplace, THE Brand_Importer SHALL navigate to the corresponding Amazon domain and perform a search using the input brand name as the query
2. THE Brand_Importer SHALL use Playwright sync API running in a separate thread for browser automation to maintain Windows compatibility
3. WHEN search results are returned, THE Brand_Importer SHALL collect candidate product links from the first page of results (minimum 5 candidates, maximum 10)
4. IF the search returns zero results, THEN THE Brand_Importer SHALL update the brand record status to "no_results" and log the outcome to crawl_logs

### Requirement 3: Brand Verification from Product Pages

**User Story:** As a user, I want the system to verify the brand from actual product detail pages, so that I can trust the brand association is accurate.

#### Acceptance Criteria

1. WHEN candidate products are collected, THE Brand_Importer SHALL navigate to each candidate product detail page and extract the detected brand name using Selector_Fallback chains
2. THE Brand_Normalizer SHALL normalize both the input brand name and detected brand name by lowercasing, stripping leading/trailing whitespace, and removing special characters before comparison
3. WHEN comparing normalized brand names, THE Brand_Importer SHALL compute a Confidence_Score between 0.0 and 1.0 based on string similarity
4. WHEN the Confidence_Score across sampled products is 0.8 or higher, THE Brand_Importer SHALL automatically proceed with the import by setting the brand status to "verified" and storing the canonical_brand_name and confidence_score
5. WHEN the Confidence_Score is below 0.8, THE Web_UI SHALL display the list of candidate brand names detected from product pages and require the user to select the correct brand or reject the import
6. WHEN the user selects a candidate brand, THE Brand_Importer SHALL update the brand record with the selected canonical_brand_name, set status to "verified", and proceed with ASIN discovery

### Requirement 4: ASIN Discovery

**User Story:** As a user, I want the system to discover as many ASINs as possible for a verified brand, so that I can build a comprehensive product database.

#### Acceptance Criteria

1. WHEN a brand is verified, THE ASIN_Discoverer SHALL search for ASINs using multiple strategies: search result pages, pagination through search results, related product links on detail pages, and brand store links when available
2. THE ASIN_Discoverer SHALL extract and store for each discovered ASIN: asin, marketplace, brand_id, title, brand, product_url, first_seen_at, last_seen_at, source_type, source_url, and is_active flag
3. THE ASIN_Discoverer SHALL use the composite key (asin, marketplace) to prevent duplicate entries in the master_asins table
4. WHEN a previously discovered ASIN is found again, THE ASIN_Discoverer SHALL update the last_seen_at timestamp and is_active flag without creating a duplicate record
5. THE ASIN_Discoverer SHALL record the source_type for each ASIN as one of: "search", "pagination", "related", "brand_store", or "detail_page"
6. THE ASIN_Discoverer SHALL operate on a best-effort basis without claiming complete coverage of all brand ASINs on a marketplace

### Requirement 5: Price and Product Data Extraction

**User Story:** As a user, I want the system to crawl product pages and extract pricing and product data, so that I can monitor prices across my brand's catalog.

#### Acceptance Criteria

1. WHEN the Price_Tracker crawls a product page, THE Price_Tracker SHALL extract: title, brand, price, currency, availability, seller, raw_price_text, page_url, and checked_at
2. THE Price_Tracker SHALL use Selector_Fallback chains for each extracted field, trying CSS selectors in order and using the first successful match
3. THE Price_Tracker SHALL represent all price values using Python Decimal type, not float, to avoid floating-point precision errors
4. IF a product page fails to load or times out, THEN THE Price_Tracker SHALL log the error with the ASIN, marketplace, and error details to crawl_logs and continue processing remaining ASINs
5. THE Price_Tracker SHALL use Playwright sync API in a separate thread for page rendering and BeautifulSoup or lxml for HTML parsing

### Requirement 6: Change-Only Price History

**User Story:** As a user, I want price history to record only actual price changes, so that the database stays compact and meaningful.

#### Acceptance Criteria

1. WHEN a new price is extracted for an ASIN, THE Change_Detector SHALL compare the normalized new_price against the last saved price in the current_state table
2. WHEN the normalized new_price differs from the last saved price, THE Change_Detector SHALL insert a new record into price_history with: asin, marketplace, changed_at, old_price, new_price, currency, availability, seller, page_url
3. WHEN the normalized new_price equals the last saved price, THE Change_Detector SHALL update only the last_checked_at field in the current_state table without inserting a price_history record
4. THE Change_Detector SHALL normalize prices using Decimal comparison to avoid false change detections from floating-point rounding
5. THE Brand_Tracker SHALL provide a configuration option to enable or disable availability change tracking in price_history independently from price change tracking

### Requirement 7: Current State Management

**User Story:** As a user, I want to see the latest known state of each product at a glance, so that I can quickly assess current prices and availability.

#### Acceptance Criteria

1. THE Price_Tracker SHALL maintain a current_state record for each (asin, marketplace) pair containing: last_checked_at, last_price, currency, availability, seller, title, brand, raw_price_text, and page_url
2. WHEN a product is crawled for the first time, THE Price_Tracker SHALL create a new current_state record and insert the initial price into price_history
3. WHEN a product is crawled subsequently, THE Price_Tracker SHALL update the current_state record with the latest extracted data regardless of whether the price changed

### Requirement 8: Crawl Job Management and Logging

**User Story:** As a user, I want to see crawl job status and logs, so that I can monitor system activity and troubleshoot issues.

#### Acceptance Criteria

1. WHEN a crawl operation starts, THE Crawl_Manager SHALL create a crawl_jobs record with: job_type (one of "brand_search", "asin_discovery", "price_check"), marketplace, target (brand name or ASIN list identifier), status "running", and started_at timestamp
2. WHEN a crawl operation completes, THE Crawl_Manager SHALL update the crawl_jobs record with status "completed" or "failed", finished_at timestamp, and item_count
3. THE Crawl_Manager SHALL write structured log entries to the crawl_logs table with: job_id, level (DEBUG, INFO, WARNING, ERROR), message, and created_at timestamp
4. IF a crawl job encounters an unrecoverable error, THEN THE Crawl_Manager SHALL set the job status to "failed", log the error details, and allow remaining scheduled jobs to continue

### Requirement 9: Database Schema

**User Story:** As a developer, I want a well-defined SQLite database schema, so that data is stored consistently and efficiently.

#### Acceptance Criteria

1. THE Brand_Tracker SHALL create and maintain six database tables: brands, master_asins, current_state, price_history, crawl_jobs, and crawl_logs
2. THE brands table SHALL use an auto-increment integer primary key and store: input_brand_name, canonical_brand_name, normalized_brand_name, marketplace, status, confidence_score, created_at, and updated_at
3. THE master_asins table SHALL use the composite primary key (asin, marketplace) and store: brand_id (foreign key to brands), title, brand, product_url, first_seen_at, last_seen_at, source_type, source_url, and is_active
4. THE current_state table SHALL use the composite primary key (asin, marketplace) and store: last_checked_at, last_price, currency, availability, seller, title, brand, raw_price_text, and page_url
5. THE price_history table SHALL use an auto-increment integer primary key and store: asin, marketplace, changed_at, old_price, new_price, currency, availability, seller, page_url, and note
6. THE crawl_jobs table SHALL use an auto-increment integer primary key and store: job_type, marketplace, target, status, started_at, finished_at, item_count, and note
7. THE crawl_logs table SHALL use an auto-increment integer primary key and store: job_id (foreign key to crawl_jobs), level, message, and created_at

### Requirement 10: Web UI Pages

**User Story:** As a user, I want a web interface with dedicated pages for managing brands, viewing ASINs, checking price history, and reviewing crawl logs, so that I can interact with the system easily.

#### Acceptance Criteria

1. THE Web_UI SHALL provide a brands list page displaying all imported brands with their marketplace, status, confidence_score, canonical_brand_name, and ASIN count
2. THE Web_UI SHALL provide an ASINs list page displaying all discovered ASINs for a selected brand, with columns for: asin, marketplace, title, product_url, source_type, first_seen_at, last_seen_at, and is_active status
3. THE Web_UI SHALL provide a price history page for a selected ASIN showing: changed_at, old_price, new_price, currency, availability, and seller
4. THE Web_UI SHALL provide a crawl logs page displaying recent crawl jobs and their associated log entries with filtering by job_type and status
5. THE Web_UI SHALL use Jinja2 templates served by FastAPI or Flask for server-side rendering

### Requirement 11: Marketplace Configuration

**User Story:** As a developer, I want marketplace-specific configuration, so that the system correctly handles domain URLs, currencies, and locales for each supported Amazon region.

#### Acceptance Criteria

1. THE Brand_Tracker SHALL maintain a marketplace configuration mapping for exactly three marketplaces: AE (amazon.ae, AED), SA (amazon.sa, SAR), and AU (amazon.com.au, AUD)
2. WHEN constructing Amazon URLs for search or product pages, THE Brand_Tracker SHALL use the domain from the marketplace configuration corresponding to the target marketplace
3. THE Brand_Tracker SHALL reject any marketplace code not in the set {AE, SA, AU} and return a descriptive error message

### Requirement 12: Incremental Database Expansion

**User Story:** As a user, I want to re-run discovery for existing brands to find new ASINs over time, so that my product database grows incrementally.

#### Acceptance Criteria

1. WHEN the user triggers a re-discovery for an existing verified brand, THE ASIN_Discoverer SHALL search for ASINs using the same multi-strategy approach and add newly found ASINs to master_asins
2. WHEN a previously known ASIN is encountered during re-discovery, THE ASIN_Discoverer SHALL update last_seen_at without creating a duplicate record
3. WHEN a previously known ASIN is not found during re-discovery, THE ASIN_Discoverer SHALL retain the existing record and keep is_active unchanged (discovery is best-effort)

### Requirement 13: Error Handling and Resilience

**User Story:** As a user, I want the system to handle errors gracefully, so that individual failures do not stop the entire crawl process.

#### Acceptance Criteria

1. IF a page load exceeds the configured timeout, THEN THE Brand_Tracker SHALL log the timeout event, skip the current page, and continue with the next item in the queue
2. IF Playwright encounters a browser crash or navigation error, THEN THE Brand_Tracker SHALL log the error, attempt to restart the browser context, and continue processing
3. THE Brand_Tracker SHALL use configurable timeout values for page loads and network requests
4. IF a selector chain returns no match for a required field, THEN THE Price_Tracker SHALL log a warning with the ASIN, marketplace, and field name, and set the field value to null

### Requirement 14: Application Architecture

**User Story:** As a developer, I want a modular project structure with clear separation of concerns, so that the codebase is maintainable and extensible.

#### Acceptance Criteria

1. THE Brand_Tracker SHALL organize code into separate modules for: web routes, database models, scraping/crawling, brand import logic, ASIN discovery logic, price tracking logic, and configuration
2. THE Brand_Tracker SHALL use Python standard logging with configurable log levels for all modules
3. THE Brand_Tracker SHALL use Playwright sync API executed in a dedicated thread to avoid blocking the async web server event loop on Windows
4. THE Brand_Tracker SHALL store all data in a local SQLite database file with no external database dependencies
