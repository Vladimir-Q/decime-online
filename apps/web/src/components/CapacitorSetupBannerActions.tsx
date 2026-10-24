"use client";

import { isCapacitorMobileBuild } from "@/lib/capacitor-build";
import { openNativeApiSetup } from "@/lib/decime-api-native";

export function CapacitorSetupBannerActions() {
  if (!isCapacitorMobileBuild()) {
    return null;
  }

  return (
    <button
      type="button"
      className="button secondary small"
      onClick={() => {
        void openNativeApiSetup();
      }}
    >
      Изменить IP ПК
    </button>
  );
}
