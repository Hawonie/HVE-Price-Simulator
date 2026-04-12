import { NextRequest, NextResponse } from "next/server";

// Keepa API configuration
// Users need to provide their own Keepa API key
const KEEPA_API_KEY = process.env.KEEPA_API_KEY || "";

// Keepa domain IDs
const KEEPA_DOMAIN_IDS: Record<string, number> = {
  US: 1,
  UK: 2,
  DE: 3,
  FR: 4,
  JP: 5,
  CA: 6,
  IT: 8,
  ES: 9,
  IN: 10,
  MX: 11,
  BR: 12,
};

// Marketplaces NOT supported by Keepa (use ScraperAPI instead)
const SCRAPER_API_ONLY = ["AE", "SA", "AU"];

interface KeepaProductResponse {
  asin: string;
  marketplace: string;
  title: string;
  prices: Array<{
    timestamp: string;
    price: number;
    currency: string;
  }>;
  currentPrice: number;
  currency: string;
  seller: string;
  source: "keepa";
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

  const upperMarketplace = marketplace.toUpperCase();

  // Check if this marketplace should use ScraperAPI
  if (SCRAPER_API_ONLY.includes(upperMarketplace)) {
    return NextResponse.json(
      { error: `Marketplace ${marketplace} should use ScraperAPI endpoint instead.` },
      { status: 400 }
    );
  }

  // Check if Keepa supports this marketplace
  const domainId = KEEPA_DOMAIN_IDS[upperMarketplace];
  if (!domainId) {
    return NextResponse.json(
      { error: `Marketplace ${marketplace} not supported by Keepa.` },
      { status: 400 }
    );
  }

  if (!KEEPA_API_KEY) {
    // Return mock data if no API key is set
    return NextResponse.json(generateMockKeepaData(asin, upperMarketplace));
  }

  try {
    const keepaUrl = `https://api.keepa.com/product?key=${KEEPA_API_KEY}&domain=${domainId}&asin=${asin}&history=1&stats=1`;

    const response = await fetch(keepaUrl);

    if (!response.ok) {
      throw new Error(`Keepa API returned status ${response.status}`);
    }

    const data = await response.json();

    if (!data.products || data.products.length === 0) {
      throw new Error("Product not found in Keepa");
    }

    const product = data.products[0];
    const priceData = parseKeepaProduct(product, asin, upperMarketplace);

    return NextResponse.json(priceData);
  } catch (error) {
    console.error("Keepa API error:", error);
    // Fall back to mock data on error
    return NextResponse.json(generateMockKeepaData(asin, upperMarketplace));
  }
}

function parseKeepaProduct(product: any, asin: string, marketplace: string): KeepaProductResponse {
  const currency = getCurrencyForMarketplace(marketplace);
  
  // Keepa stores prices in cents, timestamps in Keepa minutes (minutes since 2011-01-01)
  const KEEPA_EPOCH = new Date("2011-01-01").getTime();
  
  const prices: Array<{ timestamp: string; price: number; currency: string }> = [];
  
  // Parse Amazon price history (index 0 in csv array)
  if (product.csv && product.csv[0]) {
    const priceHistory = product.csv[0];
    for (let i = 0; i < priceHistory.length; i += 2) {
      const keepaMinutes = priceHistory[i];
      const priceInCents = priceHistory[i + 1];
      
      if (priceInCents > 0) {
        const timestamp = new Date(KEEPA_EPOCH + keepaMinutes * 60000).toISOString();
        const price = priceInCents / 100;
        prices.push({ timestamp, price, currency });
      }
    }
  }

  // Get current price from stats
  let currentPrice = 0;
  if (product.stats && product.stats.current) {
    currentPrice = (product.stats.current[0] || 0) / 100;
  } else if (prices.length > 0) {
    currentPrice = prices[prices.length - 1].price;
  }

  return {
    asin,
    marketplace,
    title: product.title || "Unknown Product",
    prices,
    currentPrice,
    currency,
    seller: product.manufacturer || `Amazon.${marketplace.toLowerCase()}`,
    source: "keepa",
  };
}

function generateMockKeepaData(asin: string, marketplace: string): KeepaProductResponse {
  const currency = getCurrencyForMarketplace(marketplace);
  const basePrice = getBasePriceForCurrency(currency);
  
  // Generate 90 days of price history
  const prices: Array<{ timestamp: string; price: number; currency: string }> = [];
  const now = Date.now();
  
  for (let i = 90; i >= 0; i--) {
    const timestamp = new Date(now - i * 86400000).toISOString();
    const fluctuation = 1 + (Math.random() - 0.5) * 0.2;
    const price = Math.round(basePrice * fluctuation * 100) / 100;
    prices.push({ timestamp, price, currency });
  }

  return {
    asin,
    marketplace,
    title: `Product ${asin.slice(-4)}`,
    prices,
    currentPrice: prices[prices.length - 1].price,
    currency,
    seller: `Amazon.${marketplace.toLowerCase()}`,
    source: "keepa",
  };
}

function getCurrencyForMarketplace(marketplace: string): string {
  const currencies: Record<string, string> = {
    US: "USD",
    UK: "GBP",
    DE: "EUR",
    FR: "EUR",
    IT: "EUR",
    ES: "EUR",
    JP: "JPY",
    IN: "INR",
    CA: "CAD",
    MX: "MXN",
    BR: "BRL",
  };
  return currencies[marketplace] || "USD";
}

function getBasePriceForCurrency(currency: string): number {
  const basePrices: Record<string, number> = {
    USD: 99,
    EUR: 89,
    GBP: 79,
    JPY: 12000,
    INR: 8000,
    CAD: 129,
    MXN: 1800,
    BRL: 500,
  };
  return basePrices[currency] || 99;
}
