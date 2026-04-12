"use client";

import { useStore } from "@/lib/store";
import { translations } from "@/lib/translations";
import { StatsCards } from "./stats-cards";
import { RecentActivity } from "./recent-activity";
import { OutlierAlerts } from "./outlier-alerts";

export function DashboardView() {
  const { lang } = useStore();
  const t = translations[lang];

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex flex-col gap-1">
        <h2 className="text-2xl font-bold text-foreground">{t.overview}</h2>
        <p className="text-sm text-muted-foreground">{t.overviewSub}</p>
      </div>

      {/* Stats Cards */}
      <StatsCards />

      {/* Outlier Alerts and Recent Activity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <OutlierAlerts />
        <RecentActivity />
      </div>
    </div>
  );
}
