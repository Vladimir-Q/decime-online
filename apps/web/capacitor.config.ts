import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.decime.uy",
  appName: "Decime UY",
  webDir: "out",
  server: {
    androidScheme: "https",
    appStartPath: "/app/quick-reply/index.html",
  },
  android: {
    allowMixedContent: true,
  },
  // Native JSON/multipart uses DecimeApiPlugin (Java HttpURLConnection). CapacitorHttp
  // breaks LAN requests from WebView on many devices.
  plugins: {},
};

export default config;
