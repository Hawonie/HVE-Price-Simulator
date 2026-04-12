"use client";

import { useStore } from "@/lib/store";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { translations } from "@/lib/translations";
import { formatCurrency } from "@/lib/price-utils";
import { AlertTriangle, TrendingUp, TrendingDown, X, CheckCircle2, Loader2 } from "lucide-react";

const FLAG_EMOJIS: Record<string, string> = {
  AE: "🇦🇪",
  SA: "🇸🇦",
  AU: "🇦🇺",
  US: "🇺🇸",
  UK: "🇬🇧",
  DE: "🇩🇪",
  FR: "🇫🇷",
  IT: "🇮🇹",
  ES: "🇪🇸",
  JP: "🇯🇵",
  IN: "🇮🇳",
};

export function OutlierAlerts() {
  const { 
    outlierAlerts, 
    alertsByMarketplace, 
    dismissAlert, 
    lang, 
    isLoading,
    refreshAllPrices,
    getDataSource
  } = useStore();
  const t = translations[lang];

  const marketplacesWithAlerts = Object.keys(alertsByMarketplace).sort();

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            <CardTitle className="text-lg font-semibold text-card-foreground">
              {t.outlierAlerts}
            </CardTitle>
            {outlierAlerts.length > 0 && (
              <Badge variant="destructive" className="ml-2">
                {outlierAlerts.length}
              </Badge>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={refreshAllPrices}
            disabled={isLoading}
            className="gap-1.5"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                {t.refreshing}
              </>
            ) : (
              t.refresh
            )}
          </Button>
        </div>
        <CardDescription className="text-muted-foreground">
          {t.outlierAlertsSub}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[280px] pr-4">
          {marketplacesWithAlerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-8 text-center">
              <CheckCircle2 className="h-12 w-12 text-emerald-500/50 mb-3" />
              <p className="text-sm font-medium text-muted-foreground">
                {t.noAlerts}
              </p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                {t.allNormal}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {marketplacesWithAlerts.map((marketplace) => {
                const alerts = alertsByMarketplace[marketplace];
                const dataSource = getDataSource(marketplace);
                
                return (
                  <div key={marketplace} className="space-y-2">
                    <div className="flex items-center gap-2 sticky top-0 bg-card py-1">
                      <span className="text-lg">{FLAG_EMOJIS[marketplace] || ""}</span>
                      <span className="font-semibold text-sm text-foreground">
                        {marketplace}
                      </span>
                      <Badge 
                        variant="outline" 
                        className={`text-xs ${
                          dataSource === "scraperapi" 
                            ? "border-cyan-500/50 text-cyan-400" 
                            : "border-amber-500/50 text-amber-400"
                        }`}
                      >
                        {dataSource === "scraperapi" ? "ScraperAPI" : "Keepa"}
                      </Badge>
                      <Badge variant="secondary" className="text-xs ml-auto">
                        {alerts.length} {alerts.length === 1 ? "alert" : "alerts"}
                      </Badge>
                    </div>
                    
                    <div className="space-y-2 pl-6">
                      {alerts.map((alert) => (
                        <div
                          key={alert.id}
                          className={`flex items-center gap-3 p-3 rounded-lg border ${
                            alert.type === "spike"
                              ? "bg-rose-500/10 border-rose-500/30"
                              : "bg-emerald-500/10 border-emerald-500/30"
                          }`}
                        >
                          <div className={`p-1.5 rounded-full ${
                            alert.type === "spike" 
                              ? "bg-rose-500/20" 
                              : "bg-emerald-500/20"
                          }`}>
                            {alert.type === "spike" ? (
                              <TrendingUp className="h-4 w-4 text-rose-400" />
                            ) : (
                              <TrendingDown className="h-4 w-4 text-emerald-400" />
                            )}
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-xs text-muted-foreground">
                                {alert.asin}
                              </span>
                              <Badge 
                                variant="outline" 
                                className={`text-xs ${
                                  alert.type === "spike"
                                    ? "border-rose-500/50 text-rose-400"
                                    : "border-emerald-500/50 text-emerald-400"
                                }`}
                              >
                                {alert.pctChange > 0 ? "+" : ""}
                                {alert.pctChange.toFixed(1)}%
                              </Badge>
                            </div>
                            <p className="text-xs text-muted-foreground truncate mt-0.5">
                              {alert.title}
                            </p>
                            <div className="flex items-center gap-2 mt-1 text-xs">
                              <span className="text-muted-foreground">
                                {formatCurrency(alert.previousPrice, alert.currency)}
                              </span>
                              <span className="text-muted-foreground">→</span>
                              <span className={`font-medium ${
                                alert.type === "spike" ? "text-rose-400" : "text-emerald-400"
                              }`}>
                                {formatCurrency(alert.currentPrice, alert.currency)}
                              </span>
                            </div>
                          </div>
                          
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-foreground"
                            onClick={() => dismissAlert(alert.id)}
                          >
                            <X className="h-4 w-4" />
                            <span className="sr-only">{t.dismiss}</span>
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
