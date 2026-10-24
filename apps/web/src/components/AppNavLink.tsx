"use client";

import Link from "next/link";

import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { navigateInApp, toCapacitorStaticUrl } from "@/lib/capacitor-navigation";

interface AppNavLinkProps {
  href: string;
  children: React.ReactNode;
}

export function AppNavLink({ href, children }: AppNavLinkProps) {
  const mobile = isCapacitorMobileBuild();

  if (mobile) {
    const staticHref = toCapacitorStaticUrl(href);
    return (
      <a
        href={staticHref}
        onClick={(event) => {
          event.preventDefault();
          navigateInApp(href);
        }}
      >
        {children}
      </a>
    );
  }

  return <Link href={href}>{children}</Link>;
}
