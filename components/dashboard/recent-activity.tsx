"use client";

import { useStore } from "@/lib/store";
import { translations } from "@/lib/translations";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { calculateStats, formatCurrency, getVolatilityLevel } from "@/lib/price-utils";
import { ArrowUpRight, ArrowDownRight, Minus, BarChart2 } from "lucide-react";
import Image from "next/image";

const SCRAPER_API_MARKETPLACES = ["AE", "SA", "AU"];

export function RecentActivity() {
  const { products, priceObservations, marketplaces, lang, setPage, setSelectedAsin, setSelectedMkt } = useStore();
  const t = translations[lang];

  const getProductStats = (productId: number) => {
    const observations = priceObservations.filter((o) => o.product_id === productId);
    return calculateStats(observations);
  };

  const getStatusBadge = (pctChange: number) => {
    if (pctChange > 3) {
      return (
        <Badge variant="outline" className="border-destructive/50 text-destructive">
          <ArrowUpRight className="mr-1 h-3 w-3" />
          {t.spike}
        </Badge>
      );
    }
    if (pctChange < -3) {
      return (
        <Badge variant="outline" className="border-success/50 text-success">
          <ArrowDownRight className="mr-1 h-3 w-3" />
          {t.drop}
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="border-muted-foreground/50 text-muted-foreground">
        <Minus className="mr-1 h-3 w-3" />
        {t.stable}
      </Badge>
    );
  };

  const handleViewAnalytics = (asin: string, marketplace: string) => {
    setSelectedAsin(asin);
    setSelectedMkt(marketplace);
    setPage("analytics");
  };

  return (
    <Card className="bg-card border-border">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg font-semibold text-card-foreground">
          {t.recentActivity}
        </CardTitle>
        <Button variant="ghost" size="sm" className="text-primary" onClick={() => setPage("add")}>
          {t.viewAll}
        </Button>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="text-muted-foreground">{t.asin}</TableHead>
              <TableHead className="text-muted-foreground">{t.marketplace}</TableHead>
              <TableHead className="text-muted-foreground">{t.currentPrice}</TableHead>
              <TableHead className="text-muted-foreground">{t.change}</TableHead>
              <TableHead className="text-muted-foreground">{t.status}</TableHead>
              <TableHead className="text-muted-foreground text-right">{t.action}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {products.slice(0, 5).map((product) => {
              const stats = getProductStats(product.id);
              const mkt = marketplaces.find((m) => m.code === product.marketplace);
              const currency = mkt?.currency || "USD";

              return (
                <TableRow key={product.id} className="border-border">
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="relative h-10 w-10 overflow-hidden rounded-md bg-secondary">
                        <Image
                          src={product.image_url}
                          alt={product.title}
                          fill
                          className="object-cover"
                        />
                      </div>
                      <div className="flex flex-col">
                        <span className="font-mono text-sm text-foreground">{product.asin}</span>
                        <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                          {product.title}
                        </span>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="bg-secondary text-secondary-foreground">
                        {product.marketplace}
                      </Badge>
                      {(() => {
                        const isScraperAPI = SCRAPER_API_MARKETPLACES.includes(product.marketplace);
                        return (
                          <Badge 
                            variant="outline" 
                            className={`text-[10px] px-1.5 py-0 ${
                              isScraperAPI 
                                ? "border-cyan-500/50 text-cyan-400" 
                                : "border-amber-500/50 text-amber-400"
                            }`}
                          >
                            {isScraperAPI ? "S" : "K"}
                          </Badge>
                        );
                      })()}
                    </div>
                  </TableCell>
                  <TableCell className="font-medium text-foreground">
                    {stats ? formatCurrency(stats.lastPrice, currency) : "—"}
                  </TableCell>
                  <TableCell>
                    {stats && (
                      <span
                        className={
                          stats.pctChange > 0
                            ? "text-destructive"
                            : stats.pctChange < 0
                            ? "text-success"
                            : "text-muted-foreground"
                        }
                      >
                        {stats.pctChange > 0 ? "+" : ""}
                        {stats.pctChange.toFixed(1)}%
                      </span>
                    )}
                  </TableCell>
                  <TableCell>{stats ? getStatusBadge(stats.pctChange) : "—"}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleViewAnalytics(product.asin, product.marketplace)}
                    >
                      <BarChart2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
