"use client";

import { useStore } from "@/lib/store";
import { translations } from "@/lib/translations";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Bell, RefreshCw, Loader2 } from "lucide-react";
import type { Lang } from "@/lib/types";

export function Header() {
  const { 
    page, 
    lang, 
    setLang, 
    preferredCurrency, 
    setPreferredCurrency, 
    marketplaces,
    isLoading,
    refreshAllPrices,
    outlierAlerts
  } = useStore();
  const t = translations[lang];

  const pageTitle = {
    dashboard: t.dashboard,
    add: t.addTracking,
    analytics: t.analytics,
  }[page];

  const uniqueCurrencies = [...new Set(marketplaces.map((m) => m.currency))];

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-6">
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold text-card-foreground">{pageTitle}</h1>
        <div className="hidden md:flex items-center gap-2">
          <Badge variant="outline" className="border-cyan-500/50 text-cyan-400 text-xs">
            ScraperAPI: AE, SA, AU
          </Badge>
          <Badge variant="outline" className="border-amber-500/50 text-amber-400 text-xs">
            Keepa: Others
          </Badge>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Currency Selector */}
        <Select
          value={preferredCurrency || "native"}
          onValueChange={(val) => setPreferredCurrency(val === "native" ? null : val)}
        >
          <SelectTrigger className="w-28 bg-secondary">
            <SelectValue placeholder={t.displayCurrency} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="native">Native</SelectItem>
            {uniqueCurrencies.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Language Selector */}
        <Select value={lang} onValueChange={(val) => setLang(val as Lang)}>
          <SelectTrigger className="w-24 bg-secondary">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="en">EN</SelectItem>
            <SelectItem value="ko">KO</SelectItem>
          </SelectContent>
        </Select>

        {/* Refresh Button */}
        <Button 
          variant="ghost" 
          size="icon" 
          className="text-muted-foreground hover:text-foreground"
          onClick={refreshAllPrices}
          disabled={isLoading}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          <span className="sr-only">{t.refresh}</span>
        </Button>

        {/* Notifications */}
        <Button 
          variant="ghost" 
          size="icon" 
          className="text-muted-foreground hover:text-foreground relative"
        >
          <Bell className="h-4 w-4" />
          {outlierAlerts.length > 0 && (
            <span className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground flex items-center justify-center">
              {outlierAlerts.length > 9 ? "9+" : outlierAlerts.length}
            </span>
          )}
          <span className="sr-only">Notifications</span>
        </Button>
      </div>
    </header>
  );
}
