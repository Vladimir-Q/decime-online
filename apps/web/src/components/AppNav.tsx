"use client";

import { AppNavLink } from "@/components/AppNavLink";
import { useAppLanguage } from "@/components/AppLanguageProvider";
import { isCapacitorMobileBuild } from "@/lib/capacitor-build";

interface AppNavProps {
  variant?: "full" | "compact";
  isAdmin?: boolean;
}

export function AppNav({ variant = "full", isAdmin = false }: AppNavProps) {
  const mobile = isCapacitorMobileBuild();
  const compact = variant === "compact" || mobile;
  const { t } = useAppLanguage();

  return (
    <nav className={compact ? "app-nav app-nav-compact" : "app-nav"}>
      <AppNavLink href="/app/live/">{t.navLiveChat}</AppNavLink>
      <AppNavLink href="/app/quick-reply/">{t.navQuickReply}</AppNavLink>
      <AppNavLink href="/app/training/">{t.navTraining}</AppNavLink>
      <AppNavLink href="/app/settings/">{t.navSettings}</AppNavLink>
      {!mobile && isAdmin ? (
        <>
          <AppNavLink href="/app/admin/users/">{t.navAdminUsers}</AppNavLink>
          <AppNavLink href="/app/admin/ai/">{t.navAdminAi}</AppNavLink>
          <AppNavLink href="/app/admin/usage/">{t.navAdminUsage}</AppNavLink>
        </>
      ) : null}
    </nav>
  );
}
