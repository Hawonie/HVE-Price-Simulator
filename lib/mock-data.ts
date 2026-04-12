import type { Marketplace, Product, PriceObservation } from "./types";

export const marketplaces: Marketplace[] = [
  { code: "AE", name: "United Arab Emirates", currency: "AED" },
  { code: "SA", name: "Saudi Arabia", currency: "SAR" },
  { code: "AU", name: "Australia", currency: "AUD" },
  { code: "US", name: "United States", currency: "USD" },
  { code: "JP", name: "Japan", currency: "JPY" },
  { code: "IN", name: "India", currency: "INR" },
  { code: "UK", name: "United Kingdom", currency: "GBP" },
  { code: "DE", name: "Germany", currency: "EUR" },
  { code: "ES", name: "Spain", currency: "EUR" },
  { code: "IT", name: "Italy", currency: "EUR" },
  { code: "FR", name: "France", currency: "EUR" },
];

// Currency base prices for realistic price generation
const currencyBasePrices: Record<string, { min: number; max: number }> = {
  USD: { min: 15, max: 500 },
  EUR: { min: 15, max: 450 },
  GBP: { min: 12, max: 400 },
  JPY: { min: 1500, max: 50000 },
  AED: { min: 50, max: 1800 },
  SAR: { min: 50, max: 1800 },
  AUD: { min: 20, max: 700 },
  INR: { min: 1000, max: 40000 },
};

export const initialProducts: Product[] = [
  { id: 1, asin: "B08N5WRWJ6", marketplace: "AE", title: "Apple MacBook Air (M1, 13-inch)", brand: "Apple", image_url: "https://picsum.photos/seed/macbook/200/200", buybox_seller: "Amazon.ae" },
  { id: 2, asin: "B09G96TFF7", marketplace: "SA", title: "iPhone 13 Pro Max", brand: "Apple", image_url: "https://picsum.photos/seed/iphone/200/200", buybox_seller: "Apple Store" },
  { id: 3, asin: "B08N5WRWJ6", marketplace: "US", title: "Apple MacBook Air (M1, 13-inch)", brand: "Apple", image_url: "https://picsum.photos/seed/macbook/200/200", buybox_seller: "Amazon.com" },
  { id: 4, asin: "B09G96TFF7", marketplace: "UK", title: "iPhone 13 Pro Max", brand: "Apple", image_url: "https://picsum.photos/seed/iphone/200/200", buybox_seller: "Amazon UK" },
  { id: 5, asin: "B08N5WRWJ6", marketplace: "DE", title: "Apple MacBook Air (M1, 13-inch)", brand: "Apple", image_url: "https://picsum.photos/seed/macbook/200/200", buybox_seller: "Amazon.de" },
];

export const initialPriceObservations: PriceObservation[] = [
  { id: 1, product_id: 1, observed_at: new Date(Date.now() - 86400000 * 30).toISOString(), price_value: 3800, currency: "AED", price_type: "buy_box" },
  { id: 2, product_id: 1, observed_at: new Date(Date.now() - 86400000 * 20).toISOString(), price_value: 3750, currency: "AED", price_type: "buy_box" },
  { id: 3, product_id: 1, observed_at: new Date(Date.now() - 86400000 * 10).toISOString(), price_value: 3900, currency: "AED", price_type: "buy_box" },
  { id: 4, product_id: 1, observed_at: new Date().toISOString(), price_value: 3850, currency: "AED", price_type: "buy_box" },
  
  { id: 5, product_id: 2, observed_at: new Date(Date.now() - 86400000 * 30).toISOString(), price_value: 4500, currency: "SAR", price_type: "buy_box" },
  { id: 6, product_id: 2, observed_at: new Date(Date.now() - 86400000 * 15).toISOString(), price_value: 4400, currency: "SAR", price_type: "buy_box" },
  { id: 7, product_id: 2, observed_at: new Date().toISOString(), price_value: 4600, currency: "SAR", price_type: "buy_box" },

  { id: 8, product_id: 3, observed_at: new Date(Date.now() - 86400000 * 30).toISOString(), price_value: 999, currency: "USD", price_type: "buy_box" },
  { id: 9, product_id: 3, observed_at: new Date(Date.now() - 86400000 * 20).toISOString(), price_value: 949, currency: "USD", price_type: "buy_box" },
  { id: 10, product_id: 3, observed_at: new Date(Date.now() - 86400000 * 10).toISOString(), price_value: 929, currency: "USD", price_type: "buy_box" },
  { id: 11, product_id: 3, observed_at: new Date().toISOString(), price_value: 899, currency: "USD", price_type: "buy_box" },

  { id: 12, product_id: 4, observed_at: new Date(Date.now() - 86400000 * 30).toISOString(), price_value: 1049, currency: "GBP", price_type: "buy_box" },
  { id: 13, product_id: 4, observed_at: new Date().toISOString(), price_value: 999, currency: "GBP", price_type: "buy_box" },

  { id: 14, product_id: 5, observed_at: new Date(Date.now() - 86400000 * 30).toISOString(), price_value: 1129, currency: "EUR", price_type: "buy_box" },
  { id: 15, product_id: 5, observed_at: new Date().toISOString(), price_value: 1099, currency: "EUR", price_type: "buy_box" },
];

// Generate realistic price history for a new product (like Keepa does)
export function generatePriceHistory(
  productId: number,
  currency: string,
  startObservationId: number
): PriceObservation[] {
  const priceRange = currencyBasePrices[currency] || currencyBasePrices.USD;
  const basePrice = priceRange.min + Math.random() * (priceRange.max - priceRange.min);
  
  // Generate 90 days of price history with realistic fluctuations
  const observations: PriceObservation[] = [];
  const now = Date.now();
  
  // Generate data points for the last 90 days (approximately 30-40 data points)
  const numPoints = 30 + Math.floor(Math.random() * 15);
  
  for (let i = 0; i < numPoints; i++) {
    // Distribute points across 90 days
    const daysAgo = Math.floor((90 / numPoints) * (numPoints - i - 1));
    const timestamp = now - daysAgo * 86400000 - Math.random() * 86400000 * 0.5;
    
    // Add realistic price fluctuation (+/- 15%)
    const fluctuation = 1 + (Math.random() - 0.5) * 0.3;
    const price = Math.round(basePrice * fluctuation * 100) / 100;
    
    observations.push({
      id: startObservationId + i,
      product_id: productId,
      observed_at: new Date(timestamp).toISOString(),
      price_value: price,
      currency,
      price_type: "buy_box"
    });
  }
  
  // Sort by date
  observations.sort((a, b) => new Date(a.observed_at).getTime() - new Date(b.observed_at).getTime());
  
  return observations;
}

// Generate product title based on ASIN pattern
export function generateProductInfo(asin: string): { title: string; brand: string } {
  // Common product categories based on ASIN patterns
  const categories = [
    { prefix: "Electronics", brands: ["Samsung", "Sony", "LG", "Anker", "Belkin"] },
    { prefix: "Home & Kitchen", brands: ["Instant Pot", "Ninja", "KitchenAid", "OXO", "Cuisinart"] },
    { prefix: "Sports & Outdoors", brands: ["Nike", "Adidas", "Under Armour", "Coleman", "Yeti"] },
    { prefix: "Beauty & Personal Care", brands: ["L'Oreal", "Neutrogena", "Olay", "Dove", "Nivea"] },
    { prefix: "Toys & Games", brands: ["LEGO", "Hasbro", "Mattel", "Fisher-Price", "Nerf"] },
  ];
  
  // Use ASIN hash to deterministically select category and brand
  const hash = asin.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const category = categories[hash % categories.length];
  const brand = category.brands[hash % category.brands.length];
  
  return {
    title: `${brand} ${category.prefix} Product - ${asin.slice(-4)}`,
    brand
  };
}

export function getProductHistory(asin: string, marketplace: string, products: Product[], observations: PriceObservation[]): PriceObservation[] {
  const product = products.find(p => p.asin === asin && p.marketplace === marketplace);
  if (!product) return [];
  return observations.filter(o => o.product_id === product.id);
}
