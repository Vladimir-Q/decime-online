import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { isNativePlatform } from "@/lib/native-share";

export function shouldUseStaticHtmlPaths(): boolean {
  return isCapacitorMobileBuild() || isNativePlatform();
}

/** Next static export in Capacitor WebView requires explicit index.html paths. */
export function toCapacitorStaticUrl(href: string): string {
  if (!shouldUseStaticHtmlPaths()) {
    return href;
  }

  try {
    const base = typeof window !== "undefined" ? window.location.origin : "https://localhost";
    const url = new URL(href, base);

    if (url.pathname.endsWith(".html")) {
      return `${url.pathname}${url.search}${url.hash}`;
    }

    if (url.pathname === "/" || url.pathname === "") {
      return `/index.html${url.search}${url.hash}`;
    }

    let pathname = url.pathname.endsWith("/") ? url.pathname : `${url.pathname}/`;
    pathname = `${pathname}index.html`;
    return `${pathname}${url.search}${url.hash}`;
  } catch {
    return href;
  }
}

export function navigateInApp(href: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.location.assign(toCapacitorStaticUrl(href));
}

export function patchInternalAnchorHrefs(root: ParentNode = document): void {
  if (!shouldUseStaticHtmlPaths()) {
    return;
  }

  root.querySelectorAll("a[href]").forEach((anchor) => {
    const href = anchor.getAttribute("href");
    if (
      !href ||
      href.startsWith("http") ||
      href.startsWith("//") ||
      href.startsWith("mailto:") ||
      href.startsWith("tel:") ||
      href.startsWith("#")
    ) {
      return;
    }

    if (!normalizeAppPath(href)) {
      return;
    }

    const staticHref = toCapacitorStaticUrl(href);
    if (anchor.getAttribute("href") !== staticHref) {
      anchor.setAttribute("href", staticHref);
    }
  });
}

export function installCapacitorAnchorHrefObserver(): () => void {
  if (!shouldUseStaticHtmlPaths() || typeof document === "undefined") {
    return () => undefined;
  }

  patchInternalAnchorHrefs();

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach((node) => {
        if (node instanceof HTMLAnchorElement) {
          patchInternalAnchorHrefs(node.parentNode ?? document);
          return;
        }
        if (node instanceof Element) {
          patchInternalAnchorHrefs(node);
        }
      });
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  const onPageShow = () => {
    patchInternalAnchorHrefs();
  };
  window.addEventListener("pageshow", onPageShow);

  return () => {
    observer.disconnect();
    window.removeEventListener("pageshow", onPageShow);
  };
}

export function normalizeAppPath(href: string): string | null {
  if (!href.startsWith("/") || href.startsWith("//")) {
    return null;
  }
  let pathOnly = href.split(/[?#]/)[0];
  if (pathOnly.endsWith("/index.html")) {
    pathOnly = pathOnly.slice(0, -"index.html".length);
  }
  if (pathOnly === "/" || pathOnly === "") {
    return "/";
  }
  return pathOnly.endsWith("/") ? pathOnly : `${pathOnly}/`;
}
