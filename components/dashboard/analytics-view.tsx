"use client";

import { useState, useMemo } from "react";
import { useStore } from "@/lib/store";
import { translations } from "@/lib/translations";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { calculateStats, formatCurrency, getVolatilityLevel, convertCurrency } from "@/lib/price-utils";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
  ReferenceDot,
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  Calendar,
  Play,
  Download,
  RefreshCw,
  Info,
  ArrowDown,
  ArrowUp,
} from "lucide-react";
import Image from "next/image";
import type { DateRange } from "@/lib/types";

export function AnalyticsView() {
  const {
    products,
    marketplaces,
    lang,
    selectedAsin,
    selectedMkt,
    setSelectedAsin,
    setSelectedMkt,
    getHistory,
    preferredCurrency,
  } = useStore();
  const t = translations[lang];

  const [dateRange, setDateRange] = useState<DateRange>("30D");
  const [simPrice, setSimPrice] = useState("");
  const [simDate, setSimDate] = useState("");
  const [simResults, setSimResults] = useState<{ t30: number | null; wasPrice: number | null } | null>(
    null
  );

  // Get selected product
  const selectedProduct = products.find(
    (p) => p.asin === selectedAsin && p.marketplace === selectedMkt
  );

  // Get unique ASINs and marketplaces for filters
  const uniqueAsins = [...new Set(products.map((p) => p.asin))];
  const productsForAsin = products.filter((p) => p.asin === selectedAsin);
  const marketsForAsin = [...new Set(productsForAsin.map((p) => p.marketplace))];

  // Get price history
  const priceHistory = useMemo(() => {
    return getHistory(selectedAsin, selectedMkt);
  }, [getHistory, selectedAsin, selectedMkt]);

  // Filter by date range
  const filteredHistory = useMemo(() => {
    const now = new Date();
    const ranges: Record<DateRange, number> = {
      "7D": 7,
      "30D": 30,
      "90D": 90,
      ALL: 365 * 10,
      CUSTOM: 365 * 10,
    };
    const days = ranges[dateRange];
    const cutoff = new Date(now.getTime() - days * 86400000);
    return priceHistory.filter((o) => new Date(o.observed_at) >= cutoff);
  }, [priceHistory, dateRange]);

  // Calculate stats
  const stats = useMemo(() => calculateStats(filteredHistory), [filteredHistory]);

  // Get marketplace currency and display currency
  const mkt = marketplaces.find((m) => m.code === selectedMkt);
  const sourceCurrency = mkt?.currency || "USD";
  const displayCurrency = preferredCurrency || sourceCurrency;

  // Convert price for display
  const convertPrice = (value: number) => {
    return convertCurrency(value, sourceCurrency, displayCurrency);
  };

  // Find min and max points in filtered history for chart markers
  const { minPoint, maxPoint } = useMemo(() => {
    if (filteredHistory.length === 0) return { minPoint: null, maxPoint: null };
    
    let minIdx = 0;
    let maxIdx = 0;
    
    filteredHistory.forEach((obs, idx) => {
      if (obs.price_value < filteredHistory[minIdx].price_value) minIdx = idx;
      if (obs.price_value > filteredHistory[maxIdx].price_value) maxIdx = idx;
    });
    
    return {
      minPoint: {
        date: new Date(filteredHistory[minIdx].observed_at).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        }),
        price: filteredHistory[minIdx].price_value,
        fullDate: new Date(filteredHistory[minIdx].observed_at).toLocaleDateString(),
      },
      maxPoint: {
        date: new Date(filteredHistory[maxIdx].observed_at).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        }),
        price: filteredHistory[maxIdx].price_value,
        fullDate: new Date(filteredHistory[maxIdx].observed_at).toLocaleDateString(),
      },
    };
  }, [filteredHistory]);

  // Chart data with converted prices
  const chartData = filteredHistory.map((o) => ({
    date: new Date(o.observed_at).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    price: convertPrice(o.price_value),
    originalPrice: o.price_value,
    fullDate: new Date(o.observed_at).toLocaleDateString(),
  }));

  // Run simulation
  const runSimulation = () => {
    if (!simPrice || !simDate) return;

    const simulatedObs = [
      ...filteredHistory,
      {
        id: Date.now(),
        product_id: selectedProduct?.id || 0,
        observed_at: new Date(simDate).toISOString(),
        price_value: parseFloat(simPrice),
        currency: sourceCurrency,
        price_type: "buy_box",
      },
    ].sort((a, b) => new Date(a.observed_at).getTime() - new Date(b.observed_at).getTime());

    const newStats = calculateStats(simulatedObs);
    if (newStats) {
      setSimResults({ t30: newStats.t30, wasPrice: newStats.wasPrice });
    }
  };

  const volatilityLevel = stats ? getVolatilityLevel(stats.cv) : "low";
  const volatilityColors = {
    low: "text-success border-success/50 bg-success/10",
    medium: "text-warning border-warning/50 bg-warning/10",
    high: "text-destructive border-destructive/50 bg-destructive/10",
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex flex-col gap-1">
        <h2 className="text-2xl font-bold text-foreground">{t.analyticsDetail}</h2>
        <p className="text-sm text-muted-foreground">{t.overviewSub}</p>
      </div>

      {/* Product Selector */}
      <Card className="bg-card border-border">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-3">
              {selectedProduct && (
                <div className="relative h-12 w-12 overflow-hidden rounded-lg bg-secondary">
                  <Image
                    src={selectedProduct.image_url}
                    alt={selectedProduct.title}
                    fill
                    className="object-cover"
                  />
                </div>
              )}
              <div className="flex flex-col">
                <span className="text-sm font-medium text-foreground">
                  {selectedProduct?.title || "Select a product"}
                </span>
                <span className="text-xs text-muted-foreground">
                  {selectedProduct?.brand}
                </span>
              </div>
            </div>

            <div className="flex flex-1 flex-wrap items-center justify-end gap-3">
              <Select value={selectedAsin} onValueChange={setSelectedAsin}>
                <SelectTrigger className="w-40 bg-input">
                  <SelectValue placeholder={t.selectAsin} />
                </SelectTrigger>
                <SelectContent>
                  {uniqueAsins.map((asin) => (
                    <SelectItem key={asin} value={asin}>
                      {asin}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={selectedMkt} onValueChange={setSelectedMkt}>
                <SelectTrigger className="w-32 bg-input">
                  <SelectValue placeholder={t.selectMarketplace} />
                </SelectTrigger>
                <SelectContent>
                  {marketsForAsin.map((code) => {
                    const market = marketplaces.find((m) => m.code === code);
                    return (
                      <SelectItem key={code} value={code}>
                        {code} - {market?.name}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>

              <div className="flex items-center gap-1 rounded-lg border border-border bg-secondary p-1">
                {(["7D", "30D", "90D", "ALL"] as DateRange[]).map((range) => (
                  <Button
                    key={range}
                    variant={dateRange === range ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setDateRange(range)}
                    className="h-7 px-3"
                  >
                    {range}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">{t.currentPrice}</span>
                <span className="text-xl font-bold text-foreground">
                  {stats ? formatCurrency(convertPrice(stats.lastPrice), displayCurrency) : "—"}
                </span>
                {stats && (
                  <span
                    className={
                      stats.pctChange > 0
                        ? "text-xs text-destructive"
                        : stats.pctChange < 0
                        ? "text-xs text-success"
                        : "text-xs text-muted-foreground"
                    }
                  >
                    {stats.pctChange > 0 ? "+" : ""}
                    {stats.pctChange.toFixed(1)}%
                  </span>
                )}
              </div>
              <div className="rounded-lg bg-primary/10 p-2">
                <DollarSign className="h-4 w-4 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">{t.t30}</span>
                <span className="text-xl font-bold text-foreground">
                  {stats?.t30 ? formatCurrency(convertPrice(stats.t30), displayCurrency) : "—"}
                </span>
                <span className="text-xs text-muted-foreground">{t.trailing30Min}</span>
              </div>
              <div className="rounded-lg bg-chart-2/10 p-2">
                <TrendingDown className="h-4 w-4 text-chart-2" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">{t.wasPrice}</span>
                <span className="text-xl font-bold text-foreground">
                  {stats?.wasPrice ? formatCurrency(convertPrice(stats.wasPrice), displayCurrency) : "—"}
                </span>
                <span className="text-xs text-muted-foreground">{t.wasPriceDesc}</span>
              </div>
              <div className="rounded-lg bg-chart-5/10 p-2">
                <Activity className="h-4 w-4 text-chart-5" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div className="flex flex-col gap-1">
                <span className="text-xs text-muted-foreground">{t.volatility}</span>
                <Badge variant="outline" className={volatilityColors[volatilityLevel]}>
                  {t[volatilityLevel]}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  CV: {stats ? (stats.cv * 100).toFixed(1) : 0}%
                </span>
              </div>
              <div className="rounded-lg bg-chart-4/10 p-2">
                <TrendingUp className="h-4 w-4 text-chart-4" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Price History Chart */}
      <Card className="bg-card border-border">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg">{t.priceHistory}</CardTitle>
            <CardDescription>
              {filteredHistory.length} data points • {displayCurrency}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm">
              <Download className="mr-2 h-4 w-4" />
              {t.exportCsv}
            </Button>
            <Button variant="outline" size="sm">
              <RefreshCw className="mr-2 h-4 w-4" />
              {t.forceRefresh}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Min/Max Legend */}
          {minPoint && maxPoint && (
            <div className="mb-4 flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-success/20">
                  <ArrowDown className="h-3 w-3 text-success" />
                </div>
                <div className="flex flex-col">
                  <span className="text-xs text-muted-foreground">{t.periodLow}</span>
                  <span className="text-sm font-medium text-success">
                    {formatCurrency(convertPrice(minPoint.price), displayCurrency)} ({minPoint.fullDate})
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-destructive/20">
                  <ArrowUp className="h-3 w-3 text-destructive" />
                </div>
                <div className="flex flex-col">
                  <span className="text-xs text-muted-foreground">{t.periodHigh}</span>
                  <span className="text-sm font-medium text-destructive">
                    {formatCurrency(convertPrice(maxPoint.price), displayCurrency)} ({maxPoint.fullDate})
                  </span>
                </div>
              </div>
            </div>
          )}
          <div className="h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--chart-1)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--chart-1)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
                  tickFormatter={(value) => formatCurrency(value, displayCurrency)}
                  domain={["auto", "auto"]}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const data = payload[0].payload;
                    return (
                      <div className="rounded-lg border border-border bg-popover px-3 py-2 shadow-lg">
                        <p className="text-xs text-muted-foreground">{data.fullDate}</p>
                        <p className="text-sm font-medium text-popover-foreground">
                          {formatCurrency(data.price, displayCurrency)}
                        </p>
                      </div>
                    );
                  }}
                />
                {stats?.t30 && (
                  <ReferenceLine
                    y={convertPrice(stats.t30)}
                    stroke="var(--chart-2)"
                    strokeDasharray="5 5"
                    label={{
                      value: "T30",
                      fill: "var(--chart-2)",
                      fontSize: 10,
                      position: "right",
                    }}
                  />
                )}
                {stats?.wasPrice && (
                  <ReferenceLine
                    y={convertPrice(stats.wasPrice)}
                    stroke="var(--chart-5)"
                    strokeDasharray="5 5"
                    label={{
                      value: "Was Price",
                      fill: "var(--chart-5)",
                      fontSize: 10,
                      position: "right",
                    }}
                  />
                )}
                <Area
                  type="monotone"
                  dataKey="price"
                  stroke="var(--chart-1)"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorPrice)"
                />
                {/* Min Point Marker */}
                {minPoint && (
                  <ReferenceDot
                    x={minPoint.date}
                    y={convertPrice(minPoint.price)}
                    r={6}
                    fill="var(--success)"
                    stroke="var(--background)"
                    strokeWidth={2}
                  />
                )}
                {/* Max Point Marker */}
                {maxPoint && (
                  <ReferenceDot
                    x={maxPoint.date}
                    y={convertPrice(maxPoint.price)}
                    r={6}
                    fill="var(--destructive)"
                    stroke="var(--background)"
                    strokeWidth={2}
                  />
                )}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Price Simulation */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Play className="h-5 w-5 text-primary" />
            {t.priceSim}
          </CardTitle>
          <CardDescription>{t.simSub}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-foreground">{t.targetPrice} ({displayCurrency})</label>
                <Input
                  type="number"
                  placeholder={t.enterPrice}
                  value={simPrice}
                  onChange={(e) => setSimPrice(e.target.value)}
                  className="bg-input"
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-foreground">{t.effectiveDate}</label>
                <Input
                  type="date"
                  value={simDate}
                  onChange={(e) => setSimDate(e.target.value)}
                  className="bg-input"
                />
              </div>
              <Button
                onClick={runSimulation}
                disabled={!simPrice || !simDate}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <Play className="mr-2 h-4 w-4" />
                {t.runSim}
              </Button>
            </div>

            {simResults && (
              <div className="flex flex-col gap-4 rounded-lg border border-border bg-secondary/50 p-4">
                <h4 className="font-medium text-foreground">{t.simResults}</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-muted-foreground">{t.newT30}</span>
                    <span className="text-lg font-bold text-foreground">
                      {simResults.t30 ? formatCurrency(convertPrice(simResults.t30), displayCurrency) : "—"}
                    </span>
                    {stats?.t30 && simResults.t30 && (
                      <span
                        className={
                          simResults.t30 < stats.t30
                            ? "text-xs text-success"
                            : simResults.t30 > stats.t30
                            ? "text-xs text-destructive"
                            : "text-xs text-muted-foreground"
                        }
                      >
                        {simResults.t30 < stats.t30 ? "Lower" : simResults.t30 > stats.t30 ? "Higher" : "No change"}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-muted-foreground">{t.newWasPrice}</span>
                    <span className="text-lg font-bold text-foreground">
                      {simResults.wasPrice ? formatCurrency(convertPrice(simResults.wasPrice), displayCurrency) : "—"}
                    </span>
                    {stats?.wasPrice && simResults.wasPrice && (
                      <span
                        className={
                          simResults.wasPrice < stats.wasPrice
                            ? "text-xs text-success"
                            : simResults.wasPrice > stats.wasPrice
                            ? "text-xs text-destructive"
                            : "text-xs text-muted-foreground"
                        }
                      >
                        {simResults.wasPrice < stats.wasPrice ? "Lower" : simResults.wasPrice > stats.wasPrice ? "Higher" : "No change"}
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">{t.simNote}</p>
              </div>
            )}
          </div>

          <div className="mt-4 flex items-start gap-2 rounded-lg border border-border bg-muted/50 p-3">
            <Info className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
            <p className="text-xs text-muted-foreground">{t.volInfo}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
