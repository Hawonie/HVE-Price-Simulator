"use client";

import { useStore } from "@/lib/store";
import { translations } from "@/lib/translations";
import { Card, CardContent } from "@/components/ui/card";
import { Package, Globe, Database, TrendingUp } from "lucide-react";

export function StatsCards() {
  const { products, marketplaces, priceObservations, lang } = useStore();
  const t = translations[lang];

  const uniqueAsins = new Set(products.map((p) => p.asin)).size;
  const activeMarketplaces = new Set(products.map((p) => p.marketplace)).size;
  const totalDataPoints = priceObservations.length;

  const stats = [
    {
      label: t.trackedAsins,
      value: uniqueAsins,
      sublabel: t.acrossAll,
      icon: Package,
      color: "text-primary",
      bgColor: "bg-primary/10",
    },
    {
      label: t.activeMkts,
      value: activeMarketplaces,
      sublabel: t.globalCoverage,
      icon: Globe,
      color: "text-chart-2",
      bgColor: "bg-chart-2/10",
    },
    {
      label: t.dataPoints,
      value: totalDataPoints.toLocaleString(),
      sublabel: t.lastUpdate,
      icon: Database,
      color: "text-chart-5",
      bgColor: "bg-chart-5/10",
    },
    {
      label: t.recentActivity,
      value: products.length,
      sublabel: t.viewAll,
      icon: TrendingUp,
      color: "text-chart-4",
      bgColor: "bg-chart-4/10",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <Card key={stat.label} className="bg-card border-border">
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    {stat.label}
                  </span>
                  <span className="text-2xl font-bold text-card-foreground">{stat.value}</span>
                  <span className="text-xs text-muted-foreground">{stat.sublabel}</span>
                </div>
                <div className={`rounded-lg p-2.5 ${stat.bgColor}`}>
                  <Icon className={`h-5 w-5 ${stat.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
