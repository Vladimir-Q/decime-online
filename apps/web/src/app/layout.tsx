import type { Metadata, Viewport } from "next";

import { NativeShareBootstrap } from "@/components/NativeShareBootstrap";
import "./globals.css";

export const metadata: Metadata = {
  title: "Decime UY",
  description:
    "Uruguayan Spanish communication copilot for WhatsApp and everyday life in Montevideo.",
  applicationName: "Decime UY",
  icons: {
    icon: [{ url: "/favicon.png", type: "image/png", sizes: "192x192" }],
    shortcut: "/favicon.png",
    apple: "/apple-touch-icon.png",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#000000",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>
        <NativeShareBootstrap />
        {children}
      </body>
    </html>
  );
}
