package com.decime.uy;

import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.text.InputType;
import android.webkit.WebView;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Toast;

import org.json.JSONObject;

public final class ApiConfigHelper {

    public static final String STORAGE_NAME = "CapacitorStorage";
    public static final String BACKUP_STORAGE_NAME = "decime_prefs";
    public static final String API_URL_KEY = "decime_api_base_url";

    private ApiConfigHelper() {}

    public static boolean isStaleExampleUrl(String url) {
        if (url == null || url.isEmpty()) {
            return false;
        }
        return url.contains("192.168.1.5");
    }

    public static String getDefaultApiUrl(Context context) {
        return context.getString(R.string.decime_default_api_url).trim();
    }

    public static boolean isProductionApiUrl(String url) {
        if (url == null || url.isEmpty()) {
            return false;
        }
        return url.startsWith("https://");
    }

    public static String readApiUrl(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(STORAGE_NAME, Context.MODE_PRIVATE);
        String value = prefs.getString(API_URL_KEY, "");
        if (value == null || value.trim().isEmpty()) {
            value = context.getSharedPreferences(BACKUP_STORAGE_NAME, Context.MODE_PRIVATE).getString(API_URL_KEY, "");
        }
        value = value == null ? "" : value.trim();
        if (isStaleExampleUrl(value)) {
            saveApiUrl(context, "");
            value = "";
        }
        if (value.isEmpty()) {
            return getDefaultApiUrl(context);
        }
        return value;
    }

    public static void saveApiUrl(Context context, String url) {
        String normalized = normalizeBaseUrl(url);
        context
            .getSharedPreferences(STORAGE_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(API_URL_KEY, normalized)
            .apply();
        context
            .getSharedPreferences(BACKUP_STORAGE_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(API_URL_KEY, normalized)
            .apply();
    }

    public static boolean needsSetup(Context context) {
        String url = readApiUrl(context);
        if (isStaleExampleUrl(url)) {
            return true;
        }
        if (isProductionApiUrl(url)) {
            return false;
        }
        return url.contains("localhost") || url.contains("127.0.0.1");
    }

    public static void injectApiUrl(WebView webView, String url) {
        if (webView == null || url == null || url.isEmpty()) {
            return;
        }

        String quoted = JSONObject.quote(url);
        String script =
            "(function(){"
                + "window.__DECIME_API_BASE_URL__="
                + quoted
                + ";"
                + "try{localStorage.setItem('decime_api_base_url',"
                + quoted
                + ");}catch(e){}"
                + "try{if(window.__decimeResetApiCache){window.__decimeResetApiCache();}}catch(e){}"
                + "try{window.dispatchEvent(new CustomEvent('decime-api-url',{detail:{url:"
                + quoted
                + "}}));}catch(e){}"
                + "})();";
        webView.evaluateJavascript(script, null);
    }

    public static void promptIfNeeded(MainActivity activity, WebView webView, Runnable onComplete) {
        if (!needsSetup(activity)) {
            injectApiUrl(webView, readApiUrl(activity));
            onComplete.run();
            return;
        }

        showSetupDialog(activity, webView, false, onComplete);
    }

    public static void showSetupDialog(
        MainActivity activity,
        WebView webView,
        boolean allowCancel,
        Runnable onComplete
    ) {
        LinearLayout layout = new LinearLayout(activity);
        layout.setOrientation(LinearLayout.VERTICAL);
        int pad = (int) (16 * activity.getResources().getDisplayMetrics().density);
        layout.setPadding(pad, pad, pad, 0);

        EditText input = new EditText(activity);
        String subnet = LanScanHelper.getSubnetPrefix(activity);
        String phoneIp = LanScanHelper.getPhoneIpv4(activity);
        String productionDefault = getDefaultApiUrl(activity);
        String hint = isEmulator() ? "http://10.0.2.2:8000" : productionDefault;
        input.setHint(hint);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        String current = readApiUrl(activity);
        if (!current.isEmpty()) {
            input.setText(current);
            input.setSelection(current.length());
        } else {
            input.setText(productionDefault);
            input.setSelection(productionDefault.length());
        }
        layout.addView(input);

        String networkHint =
            phoneIp.isEmpty()
                ? "Production: " + productionDefault
                : "Phone: " + phoneIp + " · production: " + productionDefault;

        AlertDialog.Builder builder =
            new AlertDialog.Builder(activity)
                .setTitle("API connection")
                .setMessage(
                    networkHint
                        + "\n\nUse the production URL above, or enter your PC IP for local dev (e.g. http://"
                        + subnet
                        + ".2:8000)."
                )
                .setView(layout)
                .setPositiveButton("Save", null);

        if (allowCancel) {
            builder.setNegativeButton("Cancel", (dialog, which) -> {
                if (onComplete != null) {
                    onComplete.run();
                }
            });
        } else {
            builder.setCancelable(false);
        }

        AlertDialog dialog = builder.create();
        dialog.setOnShowListener(
            shown -> {
                android.widget.Button saveButton = dialog.getButton(AlertDialog.BUTTON_POSITIVE);
                saveButton.setOnClickListener(
                    view -> {
                        String raw = input.getText().toString().trim();
                        if (raw.isEmpty()) {
                            Toast.makeText(
                                    activity,
                                    "Enter a URL, e.g. " + productionDefault,
                                    Toast.LENGTH_LONG
                                )
                                .show();
                            return;
                        }

                        final String normalized = normalizeBaseUrl(raw);
                        saveApiUrl(activity, normalized);
                        injectApiUrl(webView, normalized);
                        dialog.dismiss();
                        Toast.makeText(activity, "Saved: " + normalized, Toast.LENGTH_LONG).show();
                        if (onComplete != null) {
                            onComplete.run();
                        }

                        new Thread(
                                () -> {
                                    org.json.JSONObject probe = LanScanHelper.probeHealth(normalized);
                                    activity.runOnUiThread(
                                        () -> {
                                            if (probe.optBoolean("ok", false)) {
                                                Toast.makeText(
                                                        activity,
                                                        "Connected: " + probe.optString("app", "Decime"),
                                                        Toast.LENGTH_SHORT
                                                    )
                                                    .show();
                                                return;
                                            }
                                            Toast.makeText(
                                                    activity,
                                                    isProductionApiUrl(normalized)
                                                        ? "Saved, but API did not respond. Check internet."
                                                        : "Saved, but API did not respond. Check Wi‑Fi and PC firewall (port 8000).",
                                                    Toast.LENGTH_LONG
                                                )
                                                .show();
                                        }
                                    );
                                }
                            )
                            .start();
                    }
                );
            }
        );

        dialog.show();
    }

    public static boolean isEmulator() {
        return Build.FINGERPRINT.startsWith("generic")
            || Build.FINGERPRINT.startsWith("unknown")
            || Build.MODEL.contains("google_sdk")
            || Build.MODEL.contains("Emulator")
            || Build.MODEL.contains("Android SDK built for x86")
            || Build.MANUFACTURER.contains("Genymotion")
            || (Build.BRAND.startsWith("generic") && Build.DEVICE.startsWith("generic"))
            || "google_sdk".equals(Build.PRODUCT);
    }

    public static String normalizeUrlPublic(String raw) {
        return normalizeBaseUrl(raw);
    }

    /** Full request URL — keeps path/query; only fixes scheme/host typos. */
    public static String normalizeRequestUrl(String raw) {
        String url = raw == null ? "" : raw.trim();
        if (url.isEmpty()) {
            return url;
        }
        while (url.contains(":///")) {
            url = url.replace(":///", "://");
        }
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://" + url;
        }
        return url;
    }

    private static String normalizeBaseUrl(String raw) {
        String url = raw.trim();
        while (url.startsWith("/")) {
            url = url.substring(1);
        }
        if (url.isEmpty()) {
            return url;
        }
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://" + url;
        }
        while (url.contains(":///")) {
            url = url.replace(":///", "://");
        }
        while (url.endsWith("/")) {
            url = url.substring(0, url.length() - 1);
        }
        try {
            java.net.URI uri = java.net.URI.create(url);
            String host = uri.getHost();
            if (host == null || host.isEmpty()) {
                return url;
            }
            int port = uri.getPort();
            String scheme = uri.getScheme() == null ? "http" : uri.getScheme();
            if (port > 0) {
                return scheme + "://" + host + ":" + port;
            }
            return scheme + "://" + host;
        } catch (Exception error) {
            return url;
        }
    }
}
