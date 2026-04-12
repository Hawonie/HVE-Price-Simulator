"use client";

import { StoreProvider, useStore } from "@/lib/store";
import { Sidebar } from "@/components/dashboard/sidebar";
import { Header } from "@/components/dashboard/header";
import { Notification } from "@/components/dashboard/notification";
import { DashboardView } from "@/components/dashboard/dashboard-view";
import { AddTrackingView } from "@/components/dashboard/add-tracking-view";
import { AnalyticsView } from "@/components/dashboard/analytics-view";

function AppContent() {
  const { page } = useStore();

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6">
          {page === "dashboard" && <DashboardView />}
          {page === "add" && <AddTrackingView />}
          {page === "analytics" && <AnalyticsView />}
        </main>
      </div>
      <Notification />
    </div>
  );
}

export default function Home() {
  return (
    <StoreProvider>
      <AppContent />
    </StoreProvider>
  );
}
