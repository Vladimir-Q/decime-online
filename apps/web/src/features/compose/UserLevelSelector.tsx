"use client";

import { useAppLanguage } from "@/components/AppLanguageProvider";
import type { UserLevel } from "@/types/compose";

interface UserLevelSelectorProps {
  value: UserLevel | null;
  onChange: (level: UserLevel | null) => void;
}

export function UserLevelSelector({ value, onChange }: UserLevelSelectorProps) {
  const { t } = useAppLanguage();
  const levels = [
    { value: null as UserLevel | null, label: t.toneRecommended },
    { value: "A2" as const, label: t.toneSimple },
  ];

  return (
    <div className="field-group">
      <label className="field-label">{t.toneLabel}</label>
      <div className="chip-row">
        {levels.map((level) => (
          <button
            key={level.value ?? "any"}
            type="button"
            className={`chip ${value === level.value ? "chip-active" : ""}`}
            onClick={() => onChange(level.value)}
          >
            {level.label}
          </button>
        ))}
      </div>
    </div>
  );
}
