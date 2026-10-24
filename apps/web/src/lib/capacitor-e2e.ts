import { isCapacitorMobileBuild } from "@/lib/capacitor-build";

export interface DecimeE2EState {
  incomingText: string;
  userReply: string;
  error: string | null;
  audioLoading: boolean;
  understandLoading: boolean;
  replyLoading: boolean;
  translation: string | null;
  replySpanish: string | null;
}

export interface DecimeE2EActions {
  translate: () => Promise<void>;
  generate: (intent: string) => Promise<void>;
  pasteText: () => Promise<void>;
}

declare global {
  interface Window {
    __decimeE2E?: DecimeE2EState;
    __decimeActions?: DecimeE2EActions;
  }
}

export function syncDecimeE2E(state: DecimeE2EState, actions: DecimeE2EActions): void {
  if (!isCapacitorMobileBuild()) {
    return;
  }
  window.__decimeE2E = state;
  window.__decimeActions = actions;
  console.log(`DECIME_E2E_STATE|${JSON.stringify(state)}`);
}

export function clearDecimeE2E(): void {
  delete window.__decimeE2E;
  delete window.__decimeActions;
}
