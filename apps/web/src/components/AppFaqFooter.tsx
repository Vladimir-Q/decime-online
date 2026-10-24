"use client";

import { AppNavLink } from "@/components/AppNavLink";
import { useAppLanguage } from "@/components/AppLanguageProvider";

/** Quiet Help link one line under the main app window. */
export function AppFaqFooter() {
  const { t } = useAppLanguage();

  return (
    <p className="app-faq-footer">
      <AppNavLink href="/faq/">{t.footerFaq}</AppNavLink>
    </p>
  );
}
