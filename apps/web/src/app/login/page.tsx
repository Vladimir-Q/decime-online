import { Suspense } from "react";

import { LoginForm } from "./LoginForm";

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="page"><p className="muted">…</p></main>}>
      <LoginForm />
    </Suspense>
  );
}
