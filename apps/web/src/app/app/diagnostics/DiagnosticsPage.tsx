"use client";

import Link from "next/link";

import { ApiDiagnosticsPanel } from "@/components/ApiDiagnosticsPanel";
import { AppNav } from "@/components/AppNav";
import { MobileApiConnection } from "@/components/MobileApiConnection";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";

export function DiagnosticsPage() {
  const mobile = isCapacitorMobileBuild();

  return (
    <main className="page">
      <AppNav variant={mobile ? "compact" : "full"} />
      <section className="hero">
        <p className="eyebrow">Diagnostics</p>
        <h1>Связь с API на ПК</h1>
        <p className="lead">
          Укажите IP ПК, сохраните, затем «Проверить связь». Основной сценарий —{" "}
          <Link href="/app/quick-reply/">Quick Reply</Link>.
        </p>
      </section>

      <MobileApiConnection />
      <ApiDiagnosticsPanel />
    </main>
  );
}
