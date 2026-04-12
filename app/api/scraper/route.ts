import { NextRequest, NextResponse } from "next/server";

// ScraperAPI configuration
const SCRAPER_API_KEY = "c07c3d8999acfc7f70be7518c17425d8";

// Supported marketplaces for ScraperAPI (AE, SA, AU)
const SCRAPER_API_DOMAINS: Record<string, string> = {
  AE: "www.amazon.ae",
  SA: "www.amazon.sa",
  AU: "www.amazon.com.au",
};

interface ScraperAPIResponse {
  asin: string;
  marketplace: string;
  title: string;
  price: number;
  currency: string;
  seller: string;
  timestamp: string;
  source: "scraperapi";
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const asin = searchParams.get("asin");
  const marketplace = searchParams.get("marketplace");

  if (!asin || !marketplace) {
    return NextResponse.json(
      { error: "Missing asin or marketplace parameter" },
      { status: 400 }
    );
  }

  // Check if this marketplace is supported by ScraperAPI
  const domain = SCRAPER_API_DOMAINS[marketplace.toUpperCase()];
  if (!domain) {
    return NextResponse.json(
      { error: `Marketplace ${marketplace} not supported by ScraperAPI. Use Keepa instead.` },
      { status: 400 }
    );
  }

  try {
    const amazonUrl = `https://${domain}/dp/${asin}`;
    const scraperUrl = `https://api.scraperapi.com?api_key=${SCRAPER_API_KEY}&url=${encodeURIComponent(amazonUrl)}&render=false`;

    const response = await fetch(scraperUrl, {
      headers: {
        "Accept": "text/html",
      },
    });

    if (!response.ok) {
      throw new Error(`ScraperAPI returned status ${response.status}`);
    }

    const html = await response.text();

    // Parse the HTML to extract price data
    const priceData = parseAmazonPage(html, asin, marketplace);

    return NextResponse.json(priceData);
  } catch (error) {
    console.error("ScraperAPI error:", error);
    return NextResponse.json(
      { error: "Failed to fetch data from ScraperAPI", details: String(error) },
      { status: 500 }
    );
  }
}

function parseAmazonPage(html: string, asin: string, marketplace: string): ScraperAPIResponse {
  // Extract title
  let title = "Unknown Product";
  const titleMatch = html.match(/<span[^>]*id="productTitle"[^>]*>([^<]+)<\/span>/);
  if (titleMatch) {
    title = titleMatch[1].trim();
  }

  // Extract price - multiple patterns for different Amazon formats
  let price = 0;
  let currency = getCurrencyForMarketplace(marketplace);

  // Pattern 1: Price whole and fraction spans
  const priceWholeMatch = html.match(/<span class="a-price-whole">([0-9,]+)/);
  const priceFractionMatch = html.match(/<span class="a-price-fraction">([0-9]+)/);
  
  if (priceWholeMatch) {
    const whole = priceWholeMatch[1].replace(/,/g, "");
    const fraction = priceFractionMatch ? priceFractionMatch[1] : "00";
    price = parseFloat(`${whole}.${fraction}`);
  }

  // Pattern 2: Combined price string
  if (price === 0) {
    const combinedPriceMatch = html.match(/class="a-price"[^>]*>.*?<span[^>]*>([A-Z]{3}|[$£€¥])\s*([0-9,]+\.?[0-9]*)/s);
    if (combinedPriceMatch) {
      price = parseFloat(combinedPriceMatch[2].replace(/,/g, ""));
    }
  }

  // Pattern 3: Buy box price
  if (price === 0) {
    const buyBoxMatch = html.match(/id="priceblock_ourprice"[^>]*>([A-Z]{3}|[$£€¥])\s*([0-9,]+\.?[0-9]*)/);
    if (buyBoxMatch) {
      price = parseFloat(buyBoxMatch[2].replace(/,/g, ""));
    }
  }

  // Extract seller
  let seller = `Amazon.${marketplace.toLowerCase()}`;
  const sellerMatch = html.match(/id="sellerProfileTriggerId"[^>]*>([^<]+)<\/a>/);
  if (sellerMatch) {
    seller = sellerMatch[1].trim();
  }

  return {
    asin,
    marketplace,
    title,
    price,
    currency,
    seller,
    timestamp: new Date().toISOString(),
    source: "scraperapi",
  };
}

function getCurrencyForMarketplace(marketplace: string): string {
  const currencies: Record<string, string> = {
    AE: "AED",
    SA: "SAR",
    AU: "AUD",
  };
  return currencies[marketplace.toUpperCase()] || "USD";
}
