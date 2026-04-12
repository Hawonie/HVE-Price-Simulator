"use client";

import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { CheckCircle2, Info, XCircle, X } from "lucide-react";

export function Notification() {
  const { notification, showNotification } = useStore();

  if (!notification) return null;

  const icons = {
    success: CheckCircle2,
    info: Info,
    error: XCircle,
  };

  const Icon = icons[notification.type];

  return (
    <div
      className={cn(
        "fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-lg px-4 py-3 shadow-lg animate-in slide-in-from-bottom-4",
        notification.type === "success" && "bg-success/20 text-success border border-success/30",
        notification.type === "info" && "bg-info/20 text-info border border-info/30",
        notification.type === "error" && "bg-destructive/20 text-destructive border border-destructive/30"
      )}
    >
      <Icon className="h-5 w-5 shrink-0" />
      <span className="text-sm font-medium">{notification.message}</span>
      <button
        onClick={() => showNotification("", "info")}
        className="ml-2 rounded p-0.5 hover:bg-foreground/10"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
