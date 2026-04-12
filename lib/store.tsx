"use client";

import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import type { Product, Marketplace, Page, Lang, PriceObservation, OutlierAlert, DataSource } from "./types";
import { 
  marketplaces, 
  initialProducts, 
  initialPriceObservations, 
  getProductHistory,
  generatePriceHistory,
  generateProductInfo
} from "./mock-data";
import { generateOutlierAlerts, groupAlertsByMarketplace } from "./outlier-detection";

// Marketplaces that use ScraperAPI (AE, SA, AU)
const SCRAPER_API_MARKETPLACES = ["AE", "SA", "AU"];

interface Notification {
  message: string;
  type: "success" | "info" | "error";
}

interface StoreContextType {
  // Navigation
  page: Page;
  setPage: (page: Page) => void;
  
  // Language
  lang: Lang;
  setLang: (lang: Lang) => void;
  
  // Data
  products: Product[];
  marketplaces: Marketplace[];
  priceObservations: PriceObservation[];
  
  // Outlier Alerts
  outlierAlerts: OutlierAlert[];
  alertsByMarketplace: Record<string, OutlierAlert[]>;
  dismissAlert: (alertId: string) => void;
  
  // Analytics state
  selectedAsin: string;
  selectedMkt: string;
  setSelectedAsin: (asin: string) => void;
  setSelectedMkt: (mkt: string) => void;
  
  // Currency
  preferredCurrency: string | null;
  setPreferredCurrency: (currency: string | null) => void;
  
  // Notifications
  notification: Notification | null;
  showNotification: (message: string, type?: Notification["type"]) => void;
  
  // Data fetching
  isLoading: boolean;
  fetchLivePrice: (asin: string, marketplace: string) => Promise<void>;
  refreshAllPrices: () => Promise<void>;
  
  // Actions
  addTracking: (asins: string[], marketplace: string, frequency: string) => void;
  deleteProduct: (id: number) => void;
  getHistory: (asin: string, marketplace: string) => PriceObservation[];
  getDataSource: (marketplace: string) => DataSource;
}

const StoreContext = createContext<StoreContextType | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [page, setPage] = useState<Page>("dashboard");
  const [lang, setLang] = useState<Lang>("en");
  const [products, setProducts] = useState<Product[]>(initialProducts);
  const [priceObservations, setPriceObservations] = useState<PriceObservation[]>(initialPriceObservations);
  const [selectedAsin, setSelectedAsin] = useState("B08N5WRWJ6");
  const [selectedMkt, setSelectedMkt] = useState("US");
  const [preferredCurrency, setPreferredCurrency] = useState<string | null>(null);
  const [notification, setNotification] = useState<Notification | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());

  // Calculate outlier alerts
  const outlierAlerts = generateOutlierAlerts(products, priceObservations)
    .filter(alert => !dismissedAlerts.has(alert.id));
  const alertsByMarketplace = groupAlertsByMarketplace(outlierAlerts);

  const dismissAlert = useCallback((alertId: string) => {
    setDismissedAlerts(prev => new Set([...prev, alertId]));
  }, []);

  const showNotification = useCallback((message: string, type: Notification["type"] = "success") => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  }, []);

  const getDataSource = useCallback((marketplace: string): DataSource => {
    return SCRAPER_API_MARKETPLACES.includes(marketplace.toUpperCase()) ? "scraperapi" : "keepa";
  }, []);

  const fetchLivePrice = useCallback(async (asin: string, marketplace: string) => {
    const dataSource = getDataSource(marketplace);
    const endpoint = dataSource === "scraperapi" ? "/api/scraper" : "/api/keepa";
    
    try {
      setIsLoading(true);
      const response = await fetch(`${endpoint}?asin=${asin}&marketplace=${marketplace}`);
      
      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }
      
      const data = await response.json();
      
      // Find the product
      const product = products.find(p => p.asin === asin && p.marketplace === marketplace);
      if (!product) return;
      
      // Add new price observation
      const mkt = marketplaces.find(m => m.code === marketplace);
      const currency = mkt?.currency || "USD";
      
      const newObservation: PriceObservation = {
        id: Date.now(),
        product_id: product.id,
        observed_at: new Date().toISOString(),
        price_value: data.price || data.currentPrice || 0,
        currency,
        price_type: "buy_box"
      };
      
      setPriceObservations(prev => [...prev, newObservation]);
      
      // Update product title if we got a better one
      if (data.title && data.title !== "Unknown Product") {
        setProducts(prev => prev.map(p => 
          p.id === product.id ? { ...p, title: data.title, buybox_seller: data.seller } : p
        ));
      }
      
      showNotification(`Fetched live price for ${asin} from ${dataSource.toUpperCase()}`);
    } catch (error) {
      console.error(`Error fetching from ${dataSource}:`, error);
      showNotification(`Failed to fetch price: ${error}`, "error");
    } finally {
      setIsLoading(false);
    }
  }, [products, getDataSource, showNotification]);

  const refreshAllPrices = useCallback(async () => {
    setIsLoading(true);
    showNotification("Refreshing all prices...", "info");
    
    const uniqueProducts = products.reduce((acc, p) => {
      const key = `${p.asin}-${p.marketplace}`;
      if (!acc.has(key)) {
        acc.set(key, p);
      }
      return acc;
    }, new Map<string, Product>());
    
    const fetchPromises = Array.from(uniqueProducts.values()).map(p => 
      fetchLivePrice(p.asin, p.marketplace).catch(() => {})
    );
    
    await Promise.all(fetchPromises);
    setIsLoading(false);
    showNotification("All prices refreshed!", "success");
  }, [products, fetchLivePrice, showNotification]);

  const addTracking = useCallback((asins: string[], marketplace: string, frequency: string) => {
    const mkt = marketplaces.find(m => m.code === marketplace);
    const currency = mkt?.currency || "USD";
    const dataSource = getDataSource(marketplace);
    
    const newProducts: Product[] = [];
    const newObservations: PriceObservation[] = [];
    
    asins.forEach((asin, index) => {
      const trimmedAsin = asin.trim().toUpperCase();
      if (!trimmedAsin) return;
      
      const productId = Date.now() + index;
      const { title, brand } = generateProductInfo(trimmedAsin);
      
      const newProduct: Product = {
        id: productId,
        asin: trimmedAsin,
        marketplace,
        title,
        brand,
        image_url: `https://picsum.photos/seed/${trimmedAsin}/200/200`,
        buybox_seller: `Amazon.${marketplace.toLowerCase()}`
      };
      
      newProducts.push(newProduct);
      
      const startObservationId = Date.now() * 1000 + index * 100;
      const history = generatePriceHistory(productId, currency, startObservationId);
      newObservations.push(...history);
    });
    
    if (newProducts.length > 0) {
      setProducts(prev => [...prev, ...newProducts]);
      setPriceObservations(prev => [...prev, ...newObservations]);
      
      setSelectedAsin(newProducts[0].asin);
      setSelectedMkt(marketplace);
      
      showNotification(
        `Started tracking ${newProducts.length} ASIN(s) on ${marketplace} via ${dataSource.toUpperCase()}!`
      );
      
      // Fetch live prices for new products
      newProducts.forEach(p => {
        fetchLivePrice(p.asin, p.marketplace).catch(() => {});
      });
    }
  }, [showNotification, getDataSource, fetchLivePrice]);

  const deleteProduct = useCallback((id: number) => {
    setProducts(prev => prev.filter(p => p.id !== id));
    setPriceObservations(prev => prev.filter(o => o.product_id !== id));
    showNotification("Product removed from tracking");
  }, [showNotification]);

  const getHistory = useCallback((asin: string, marketplace: string) => {
    return getProductHistory(asin, marketplace, products, priceObservations);
  }, [products, priceObservations]);

  return (
    <StoreContext.Provider value={{
      page,
      setPage,
      lang,
      setLang,
      products,
      marketplaces,
      priceObservations,
      outlierAlerts,
      alertsByMarketplace,
      dismissAlert,
      selectedAsin,
      selectedMkt,
      setSelectedAsin,
      setSelectedMkt,
      preferredCurrency,
      setPreferredCurrency,
      notification,
      showNotification,
      isLoading,
      fetchLivePrice,
      refreshAllPrices,
      addTracking,
      deleteProduct,
      getHistory,
      getDataSource,
    }}>
      {children}
    </StoreContext.Provider>
  );
}

export function useStore() {
  const context = useContext(StoreContext);
  if (!context) {
    throw new Error("useStore must be used within a StoreProvider");
  }
  return context;
}
