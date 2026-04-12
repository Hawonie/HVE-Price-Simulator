export interface Marketplace {
  code: string;
  name: string;
  currency: string;
}

export interface Product {
  id: number;
  asin: string;
  marketplace: string;
  title: string;
  brand: string;
  image_url: string;
  buybox_seller?: string;
}

export interface PriceObservation {
  id: number;
  product_id: number;
  observed_at: string;
  price_value: number;
  currency: string;
  price_type: string;
}

export interface PriceStats {
  mean: number;
  median: number;
  min: number;
  max: number;
  lastPrice: number;
  pctChange: number;
  cv: number;
  t30: number | null;
  wasPrice: number | null; // Was Price (90-day median)
}

export type Page = "dashboard" | "add" | "analytics";
export type Lang = "en" | "ko";
export type DateRange = "7D" | "30D" | "90D" | "ALL" | "CUSTOM";

export interface OutlierAlert {
  id: string;
  productId: number;
  asin: string;
  marketplace: string;
  title: string;
  currentPrice: number;
  previousPrice: number;
  pctChange: number;
  currency: string;
  type: "spike" | "drop";
  detectedAt: string;
  threshold: number;
}

export type DataSource = "scraperapi" | "keepa";
