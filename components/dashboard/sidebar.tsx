"use client";

import { useStore } from "@/lib/store";
import { translations } from "@/lib/translations";
import { cn } from "@/lib/utils";
import { LayoutDashboard, PlusCircle, BarChart3, Globe } from "lucide-react";
import type { Page } from "@/lib/types";

const navItems: { page: Page; icon: typeof LayoutDashboard; labelKey: keyof typeof translations.en }[] = [
  { page: "dashboard", icon: LayoutDashboard, labelKey: "dashboard" },
  { page: "add", icon: PlusCircle, labelKey: "addTracking" },
  { page: "analytics", icon: BarChart3, labelKey: "analytics" },
];

export function Sidebar() {
  const { page, setPage, lang } = useStore();
  const t = translations[lang];

  return (
    <aside className="flex h-full w-64 flex-col border-r border-border bg-sidebar">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
          <Globe className="h-5 w-5 text-primary-foreground" />
        </div>
        <span className="text-lg font-semibold text-sidebar-foreground">ZonTrack</span>
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col gap-1 p-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = page === item.page;
          return (
            <button
              key={item.page}
              onClick={() => setPage(item.page)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
              )}
            >
              <Icon className="h-5 w-5" />
              {t[item.labelKey]}
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border p-4">
        <div className="flex items-center gap-3 rounded-lg bg-sidebar-accent/50 px-3 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20 text-primary">
            <span className="text-xs font-semibold">ZT</span>
          </div>
          <div className="flex flex-col">
            <span className="text-xs font-medium text-sidebar-foreground">Pro Plan</span>
            <span className="text-[10px] text-muted-foreground">Unlimited tracking</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
