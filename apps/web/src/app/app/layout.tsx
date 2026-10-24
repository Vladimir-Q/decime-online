import { AuthGate } from "@/components/AuthGate";

export default function AppSectionLayout({ children }: { children: React.ReactNode }) {
  return <AuthGate>{children}</AuthGate>;
}
