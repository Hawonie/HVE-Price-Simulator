import type { PriceObservation, OutlierAlert, Product } from "./types";
import { calculateStats } from "./price-utils";

// Outlier detection threshold (percentage change)
const OUTLIER_THRESHOLD = 10; // 10% change triggers an alert

export interface OutlierCheckResult {
  isOutlier: boolean;
  type: "spike" | "drop" | null;
  pctChange: number;
  threshold: number;
}

/**
 * Check if a price change is an outlier compared to recent history
 */
export function checkForOutlier(
  currentPrice: number,
  history: PriceObservation[]
): OutlierCheckResult {
  if (history.length < 2) {
    return { isOutlier: false, type: null, pctChange: 0, threshold: OUTLIER_THRESHOLD };
  }

  // Sort by date descending to get most recent prices
  const sortedHistory = [...history].sort(
    (a, b) => new Date(b.observed_at).getTime() - new Date(a.observed_at).getTime()
  );

  // Get the previous price (second most recent)
  const previousPrice = sortedHistory[1]?.price_value || sortedHistory[0]?.price_value;
  
  if (!previousPrice || previousPrice === 0) {
    return { isOutlier: false, type: null, pctChange: 0, threshold: OUTLIER_THRESHOLD };
  }

  const pctChange = ((currentPrice - previousPrice) / previousPrice) * 100;
  const absChange = Math.abs(pctChange);

  if (absChange >= OUTLIER_THRESHOLD) {
    return {
      isOutlier: true,
      type: pctChange > 0 ? "spike" : "drop",
      pctChange,
      threshold: OUTLIER_THRESHOLD,
    };
  }

  return { isOutlier: false, type: null, pctChange, threshold: OUTLIER_THRESHOLD };
}

/**
 * Check for outliers using statistical methods (Z-score)
 */
export function checkForStatisticalOutlier(
  currentPrice: number,
  history: PriceObservation[],
  zThreshold: number = 2.5
): OutlierCheckResult {
  if (history.length < 5) {
    // Fall back to simple percentage check for small datasets
    return checkForOutlier(currentPrice, history);
  }

  const stats = calculateStats(history);
  if (!stats) {
    return { isOutlier: false, type: null, pctChange: 0, threshold: OUTLIER_THRESHOLD };
  }

  const prices = history.map((h) => h.price_value);
  const mean = stats.mean;
  const stdDev = Math.sqrt(
    prices.map((x) => Math.pow(x - mean, 2)).reduce((a, b) => a + b, 0) / prices.length
  );

  if (stdDev === 0) {
    return { isOutlier: false, type: null, pctChange: 0, threshold: OUTLIER_THRESHOLD };
  }

  const zScore = (currentPrice - mean) / stdDev;
  const pctChange = ((currentPrice - stats.lastPrice) / stats.lastPrice) * 100;

  if (Math.abs(zScore) >= zThreshold) {
    return {
      isOutlier: true,
      type: zScore > 0 ? "spike" : "drop",
      pctChange,
      threshold: OUTLIER_THRESHOLD,
    };
  }

  return { isOutlier: false, type: null, pctChange, threshold: OUTLIER_THRESHOLD };
}

/**
 * Generate outlier alerts for all products grouped by marketplace
 */
export function generateOutlierAlerts(
  products: Product[],
  priceObservations: PriceObservation[]
): OutlierAlert[] {
  const alerts: OutlierAlert[] = [];

  products.forEach((product) => {
    const productHistory = priceObservations
      .filter((o) => o.product_id === product.id)
      .sort((a, b) => new Date(a.observed_at).getTime() - new Date(b.observed_at).getTime());

    if (productHistory.length < 2) return;

    const currentPrice = productHistory[productHistory.length - 1].price_value;
    const currency = productHistory[productHistory.length - 1].currency;

    // Check for outlier using statistical method
    const result = checkForStatisticalOutlier(currentPrice, productHistory.slice(0, -1));

    if (result.isOutlier && result.type) {
      alerts.push({
        id: `alert-${product.id}-${Date.now()}`,
        productId: product.id,
        asin: product.asin,
        marketplace: product.marketplace,
        title: product.title,
        currentPrice,
        previousPrice: productHistory[productHistory.length - 2]?.price_value || currentPrice,
        pctChange: result.pctChange,
        currency,
        type: result.type,
        detectedAt: new Date().toISOString(),
        threshold: result.threshold,
      });
    }
  });

  // Sort by absolute percentage change (most significant first)
  return alerts.sort((a, b) => Math.abs(b.pctChange) - Math.abs(a.pctChange));
}

/**
 * Group alerts by marketplace
 */
export function groupAlertsByMarketplace(
  alerts: OutlierAlert[]
): Record<string, OutlierAlert[]> {
  return alerts.reduce((acc, alert) => {
    if (!acc[alert.marketplace]) {
      acc[alert.marketplace] = [];
    }
    acc[alert.marketplace].push(alert);
    return acc;
  }, {} as Record<string, OutlierAlert[]>);
}
