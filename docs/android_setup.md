# Decime UY — Android setup (Capacitor)

Install Decime on Android: WhatsApp share in/out, Quick Reply, Live Chat, Training, and Review — connected to **https://api.decime.online** by default.

## Prerequisites

- Node.js 20+
- [Android Studio](https://developer.android.com/studio) with SDK Platform Tools (`adb`) — to build the APK
- USB debugging (optional, for `adb install`)
- Decime account on production (`admin@decime.online` or your beta user)

## Production APK (recommended)

The default build bakes in the production API URL. No PC on the same Wi‑Fi required.

```powershell
# From repo root (Windows)
.\scripts\build-android-apk.ps1
```

Or manually:

```bash
cd apps/web
npm run cap:apk
```

Output:

```text
apps/web/android/app/build/outputs/apk/debug/app-debug.apk
```

### After install

1. Open **Decime UY** — API is preset to `https://api.decime.online`
2. **Sign in** at `/login/` (required on production)
3. Use **Quick Reply** (WhatsApp share), **Live Chat**, **Training**, **History**

Navigation (mobile): Quick Reply · Live Chat · Training · History · Settings

### Share flows

| Flow | Action |
|------|--------|
| WhatsApp → Decime | Share text or audio → Quick Reply opens prefilled |
| Decime → WhatsApp | **Share** button on generated reply |
| Live conversation | **Live Chat** → tap Mic or type |

## Local dev APK (LAN / emulator)

For testing against a PC API on Wi‑Fi or Android emulator (`10.0.2.2:8000`):

```powershell
.\scripts\build-android-apk.ps1 -Dev
```

Then open **Diagnostics** → enter `http://YOUR_PC_IP:8000` or use **Scan network** (Settings is language/logout only).

E2E tests (`scripts/android_e2e.py`) require `-Dev` build + emulator.

## One-time setup

```bash
cd apps/web
npm install
```

Regenerate launcher icons after changing `apps/web/android/icl.jpg`:

```bash
py scripts/generate_android_icons.py
cd apps/web && npm run cap:sync
```

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run build:cap` | Static export with production API URL |
| `npm run build:cap:dev` | Static export without production URL (LAN dev) |
| `npm run cap:apk` | Production debug APK |
| `npm run cap:apk:dev` | Dev debug APK |
| `npm run cap:sync` | Build + sync to Android project |
| `npm run cap:open` | Open in Android Studio |

## Native code

| File | Role |
|------|------|
| `MainActivity.java` | Share intents, API URL injection |
| `ApiConfigHelper.java` | Default `https://api.decime.online`, setup dialog |
| `ShareReceiveHelper.java` | Pending share text/audio → Quick Reply |
| `DecimeApiPlugin.java` | Native HTTP with JWT headers |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Sign in required | Log in at `/login/` — production always uses auth |
| API / network errors | Settings → Test connection; check mobile data/Wi‑Fi |
| Session expired | Log in again |
| Old APK after update | Reinstall: `adb install -r app-debug.apk` |
| Decime not in Share sheet | Reinstall; check `AndroidManifest.xml` intent filters |
| Play audio fails | Same API must be used for synth + playback (production URL) |
| Local dev on phone | Use `-Dev` build + PC IP in Diagnostics |

## Release builds

Debug APK is enough for personal/beta testing. For Play Store: Android Studio → **Build → Generate Signed Bundle/APK**.

## Related docs

- [deploy/README.md](../../deploy/README.md) — VM production deploy
- [vm_auth.md](vm_auth.md) — JWT auth
- [project_state.md](project_state.md) — current feature snapshot
