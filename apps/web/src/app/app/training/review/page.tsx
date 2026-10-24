"use client";

import { useEffect } from "react";

import { navigateInApp } from "@/lib/capacitor-navigation";

export default function TrainingReviewPage() {
  useEffect(() => {
    navigateInApp("/app/training/?tab=review");
  }, []);

  return (
    <main className="page">
      <p className="muted">Redirecting to Training review…</p>
    </main>
  );
}
