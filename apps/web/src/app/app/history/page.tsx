"use client";

import { useEffect } from "react";

import { navigateInApp } from "@/lib/capacitor-navigation";

export default function HistoryPage() {
  useEffect(() => {
    navigateInApp("/app/training/?tab=history");
  }, []);

  return (
    <main className="page">
      <p className="muted">Redirecting to Training history…</p>
    </main>
  );
}
