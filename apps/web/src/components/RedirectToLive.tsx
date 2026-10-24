"use client";

import { useEffect } from "react";

import { navigateInApp } from "@/lib/capacitor-navigation";

export function RedirectToLive() {
  useEffect(() => {
    navigateInApp("/app/live/");
  }, []);

  return (
    <main className="page">
      <p className="muted">Redirecting to Live Chat…</p>
    </main>
  );
}
