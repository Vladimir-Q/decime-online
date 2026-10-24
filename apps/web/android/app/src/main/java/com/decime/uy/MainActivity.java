package com.decime.uy;

import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import com.getcapacitor.BridgeActivity;
import com.getcapacitor.CapConfig;

import android.util.Base64;

import java.nio.charset.StandardCharsets;

public class MainActivity extends BridgeActivity {
    private static final String TAG = "DecimeApiDiag";

    private static final String QUICK_REPLY_PATH = "/app/quick-reply/index.html";
    private static final String QUICK_REPLY_URL = "https://localhost/app/quick-reply/index.html";
    private static final String SETTINGS_URL = "https://localhost/app/settings/index.html";

    private final Handler navHandler = new Handler(Looper.getMainLooper());
    private boolean quickReplyNavigationRequested = false;
    private boolean apiPromptOpen = false;
    private boolean apiSetupComplete = false;
    private boolean initialSmokeCheckDone = false;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(DecimeApiPlugin.class);
        super.onCreate(savedInstanceState);
        if ((getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0) {
            WebView.setWebContentsDebuggingEnabled(true);
        }
    }

    @Override
    protected void load() {
        Intent launchIntent = getIntent();
        boolean shareLaunch = ShareReceiveHelper.isShareIntent(launchIntent);
        if (shareLaunch) {
            ShareReceiveHelper.handleSendIntent(this, launchIntent);
        }

        CapConfig baseConfig = CapConfig.loadDefault(this);
        bridgeBuilder.setConfig(buildQuickReplyConfig(baseConfig));

        super.load();
        navHandler.postDelayed(this::ensureApiConfigured, 400);
        if (shareLaunch) {
            navHandler.postDelayed(this::notifyWebShareUpdated, 800);
        }
        handleE2EIntentExtra(launchIntent);
    }

    @Override
    public void onResume() {
        super.onResume();
        configureWebViewNetworking();
        if (apiSetupComplete) {
            scheduleApiInjection(6);
        }
        if (apiSetupComplete && !initialSmokeCheckDone) {
            initialSmokeCheckDone = true;
            runApiSmokeCheck();
        }
        handleE2EIntentExtra(getIntent());
    }

    public void scheduleApiInjectionFromPlugin(int attempts) {
        scheduleApiInjection(attempts);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (!ShareReceiveHelper.isShareIntent(intent)) {
            return;
        }
        ShareReceiveHelper.handleSendIntent(this, intent);
        navHandler.postDelayed(this::notifyWebShareUpdated, 350);
        handleE2EIntentExtra(intent);
    }

    private void notifyWebShareUpdated() {
        if (bridge == null || bridge.getWebView() == null) {
            return;
        }
        bridge.getWebView()
            .evaluateJavascript(
                "window.dispatchEvent(new CustomEvent('decime-share-updated'));",
                null
            );
    }

    private void dispatchE2EAction(String action, String payload) {
        if (bridge == null || bridge.getWebView() == null || action == null || action.isEmpty()) {
            return;
        }
        String quotedAction = org.json.JSONObject.quote(action);
        String quotedPayload = payload == null ? "null" : org.json.JSONObject.quote(payload);
        bridge.getWebView()
            .evaluateJavascript(
                "window.dispatchEvent(new CustomEvent('decime-e2e-action',{detail:{action:"
                    + quotedAction
                    + ",payload:"
                    + quotedPayload
                    + "}}));",
                null
            );
    }

    private void handleE2EIntentExtra(Intent intent) {
        if (intent == null || !intent.hasExtra("e2e_action")) {
            return;
        }
        String action = intent.getStringExtra("e2e_action");
        String payload = null;
        if (intent.hasExtra("e2e_payload_b64")) {
            String encoded = intent.getStringExtra("e2e_payload_b64");
            if (encoded != null && !encoded.isEmpty()) {
                payload = new String(Base64.decode(encoded, Base64.DEFAULT), StandardCharsets.UTF_8);
            }
            intent.removeExtra("e2e_payload_b64");
        }
        intent.removeExtra("e2e_action");
        String finalPayload = payload;
        navHandler.postDelayed(() -> dispatchE2EAction(action, finalPayload), 400);
    }

    private CapConfig buildQuickReplyConfig(CapConfig baseConfig) {
        return new CapConfig.Builder(this)
            .setHTML5mode(baseConfig.isHTML5Mode())
            .setHostname(baseConfig.getHostname())
            .setAndroidScheme(baseConfig.getAndroidScheme())
            .setAllowMixedContent(baseConfig.isMixedContentAllowed())
            .setLoggingEnabled(baseConfig.isLoggingEnabled())
            .setStartPath(QUICK_REPLY_PATH)
            .create();
    }

    private void configureWebViewNetworking() {
        if (bridge == null || bridge.getWebView() == null) {
            return;
        }
        WebSettings settings = bridge.getWebView().getSettings();
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        settings.setDomStorageEnabled(true);
    }

    private void ensureApiConfigured() {
        configureWebViewNetworking();
        if (apiPromptOpen || bridge == null || bridge.getWebView() == null) {
            if (!apiPromptOpen) {
                navHandler.postDelayed(this::ensureApiConfigured, 200);
            }
            return;
        }

        WebView webView = bridge.getWebView();
        if (!ApiConfigHelper.needsSetup(this)) {
            apiSetupComplete = true;
            scheduleApiInjection(8);
            return;
        }

        apiPromptOpen = true;
        ApiConfigHelper.promptIfNeeded(
            this,
            webView,
            () -> {
                apiPromptOpen = false;
                apiSetupComplete = true;
                scheduleApiInjection(8);
                if (ApiConfigHelper.needsSetup(this)) {
                    webView.loadUrl(SETTINGS_URL);
                }
            }
        );
    }

    private void scheduleApiInjection(int attempts) {
        String url = ApiConfigHelper.readApiUrl(this);
        if (url.isEmpty()) {
            return;
        }

        for (int attempt = 0; attempt < attempts; attempt++) {
            int delayMs = 150 + attempt * 200;
            navHandler.postDelayed(
                () -> {
                    if (bridge == null || bridge.getWebView() == null) {
                        return;
                    }
                    ApiConfigHelper.injectApiUrl(bridge.getWebView(), ApiConfigHelper.readApiUrl(this));
                },
                delayMs
            );
        }
    }

    private void openQuickReplyWarm(int attempt) {
        if (bridge == null || bridge.getWebView() == null) {
            if (attempt < 50) {
                navHandler.postDelayed(() -> openQuickReplyWarm(attempt + 1), 100);
            }
            return;
        }

        WebView webView = bridge.getWebView();
        String currentUrl = webView.getUrl();
        if (currentUrl != null && currentUrl.contains("/app/quick-reply")) {
            quickReplyNavigationRequested = false;
            return;
        }

        if (!quickReplyNavigationRequested) {
            webView.loadUrl(QUICK_REPLY_URL);
            quickReplyNavigationRequested = true;
        }

        if (attempt < 50) {
            navHandler.postDelayed(() -> openQuickReplyWarm(attempt + 1), 100);
        }
    }

    private void runApiSmokeCheck() {
        final String apiUrl = ApiConfigHelper.readApiUrl(this);
        if (apiUrl == null || apiUrl.trim().isEmpty()) {
            Log.w(TAG, "Smoke check skipped: API URL is empty");
            return;
        }

        if (ApiConfigHelper.isProductionApiUrl(apiUrl)) {
            new Thread(
                    () -> {
                        JSONObject probe = LanScanHelper.probeHealth(apiUrl);
                        if (probe.optBoolean("ok", false)) {
                            Log.i(TAG, "Production smoke check OK: " + apiUrl);
                            return;
                        }
                        Log.w(
                            TAG,
                            "Production API unreachable: "
                                + probe.optString("error", "unknown")
                        );
                    }
                )
                .start();
            return;
        }

        new Thread(
                () -> {
                    JSONObject probe = LanScanHelper.probeHealth(apiUrl);
                    if (probe.optBoolean("ok", false)) {
                        Log.i(TAG, "Smoke check OK: " + apiUrl);
                        return;
                    }
                    Log.w(
                        TAG,
                        "Smoke check failed for "
                            + apiUrl
                            + ": "
                            + probe.optString("error", "unreachable")
                            + " — scanning LAN"
                    );
                    autoDiscoverApiUrl();
                }
            )
            .start();
    }

    private void autoDiscoverApiUrl() {
        final String subnet = LanScanHelper.getSubnetPrefix(this);
        JSONArray found = LanScanHelper.scanForDecimeApi(subnet, 8000);
        if (found.length() == 0) {
            Log.w(TAG, "LAN scan found no Decime API on " + subnet + ".x — check firewall port 8000");
            return;
        }

        try {
            JSONObject first = found.getJSONObject(0);
            final String discovered = first.optString("url", "");
            if (discovered.isEmpty()) {
                return;
            }
            ApiConfigHelper.saveApiUrl(this, discovered);
            Log.i(TAG, "Auto-discovered API: " + discovered);
            navHandler.post(
                () -> {
                    if (bridge != null && bridge.getWebView() != null) {
                        ApiConfigHelper.injectApiUrl(bridge.getWebView(), discovered);
                    }
                    Toast.makeText(
                            this,
                            "Found API: " + discovered,
                            Toast.LENGTH_LONG
                        )
                        .show();
                }
            );
        } catch (Exception error) {
            Log.e(TAG, "Auto-discover failed", error);
        }
    }
}
