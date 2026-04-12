import type { PriceObservation, PriceStats } from "./types";

// Exchange rates relative to USD (simplified for demo)
const EXCHANGE_RATES: Record<string, number> = {
  USD: 1,
  EUR: 0.92,
  GBP: 0.79,
  JPY: 149.5,
  AUD: 1.53,
  CAD: 1.36,
  INR: 83.12,
  AED: 3.67,
  SAR: 3.75,
  MXN: 17.15,
  BRL: 4.97,
  SGD: 1.34,
  KRW: 1320,
};

export function convertCurrency(
  value: number,
  fromCurrency: string,
  toCurrency: string
): number {
  if (fromCurrency === toCurrency) return value;
  
  const fromRate = EXCHANGE_RATES[fromCurrency] || 1;
  const toRate = EXCHANGE_RATES[toCurrency] || 1;
  
  // Convert to USD first, then to target currency
  const valueInUSD = value / fromRate;
  return valueInUSD * toRate;
}

export function calculateStats(data: PriceObservation[]): PriceStats | null {
  if (!Array.isArray(data) || data.length === 0) return null;
  
  const prices = data.map(d => d.price_value);
  const mean = prices.reduce((a, b) => a + b, 0) / prices.length;
  const sortedPrices = [...prices].sort((a, b) => a - b);
  const median = sortedPrices[Math.floor(sortedPrices.length / 2)];
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const lastPrice = prices[prices.length - 1];
  const firstPrice = prices[0];
  const pctChange = ((lastPrice - firstPrice) / firstPrice) * 100;
  
  // T30: Trailing 30-day Minimum
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
  const t30Prices = data
    .filter(d => new Date(d.observed_at) >= thirtyDaysAgo)
    .map(d => d.price_value);
  const t30 = t30Prices.length > 0 ? Math.min(...t30Prices) : null;

  // Was Price: Median 90-day
  const ninetyDaysAgo = new Date();
  ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90);
  const wasPrices = data
    .filter(d => new Date(d.observed_at) >= ninetyDaysAgo)
    .map(d => d.price_value)
    .sort((a, b) => a - b);
  const wasPrice = wasPrices.length > 0 ? wasPrices[Math.floor(wasPrices.length / 2)] : null;

  // Volatility (CV)
  const stdDev = Math.sqrt(prices.map(x => Math.pow(x - mean, 2)).reduce((a, b) => a + b, 0) / prices.length);
  const cv = mean > 0 ? stdDev / mean : 0;
  
  return { mean, median, min, max, lastPrice, pctChange, cv, t30, wasPrice };
}

export function formatCurrency(value: number, currency: string): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  }).format(value);
}

export function getVolatilityLevel(cv: number): "low" | "medium" | "high" {
  if (cv > 0.1) return "high";
  if (cv > 0.03) return "medium";
  return "low";
}
