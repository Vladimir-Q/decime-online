package com.decime.uy;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.LinkAddress;
import android.net.LinkProperties;
import android.net.Network;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

public final class LanScanHelper {
    private static final String TAG = "DecimeLanScan";

    private LanScanHelper() {}

    public static String getPhoneIpv4(Context context) {
        try {
            ConnectivityManager cm =
                (ConnectivityManager) context.getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm != null) {
                Network network = cm.getActiveNetwork();
                if (network != null) {
                    LinkProperties props = cm.getLinkProperties(network);
                    if (props != null) {
                        for (LinkAddress address : props.getLinkAddresses()) {
                            InetAddress inet = address.getAddress();
                            if (inet instanceof Inet4Address && !inet.isLoopbackAddress()) {
                                return inet.getHostAddress();
                            }
                        }
                    }
                }
            }
        } catch (Exception error) {
            Log.w(TAG, "ConnectivityManager IP lookup failed", error);
        }

        try {
            WifiManager wm = (WifiManager) context.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if (wm != null) {
                WifiInfo info = wm.getConnectionInfo();
                if (info != null) {
                    int ip = info.getIpAddress();
                    if (ip != 0) {
                        return String.format(
                            Locale.US,
                            "%d.%d.%d.%d",
                            (ip & 0xff),
                            (ip >> 8 & 0xff),
                            (ip >> 16 & 0xff),
                            (ip >> 24 & 0xff)
                        );
                    }
                }
            }
        } catch (Exception error) {
            Log.w(TAG, "WifiManager IP lookup failed", error);
        }

        return "";
    }

    public static String getSubnetPrefix(Context context) {
        String phoneIp = getPhoneIpv4(context);
        if (phoneIp.isEmpty()) {
            return "192.168.1";
        }

        int lastDot = phoneIp.lastIndexOf('.');
        if (lastDot <= 0) {
            return "192.168.1";
        }
        return phoneIp.substring(0, lastDot);
    }

    public static JSONObject probeHealth(String baseUrl) {
        JSONObject result = new JSONObject();
        String normalized = ApiConfigHelper.normalizeUrlPublic(baseUrl);
        if (normalized.isEmpty()) {
            try {
                result.put("ok", false);
                result.put("error", "URL is empty");
            } catch (Exception ignored) {
                // ignore
            }
            return result;
        }

        HttpURLConnection connection = null;
        try {
            URL url = new URL(normalized + "/health");
            connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(8000);
            connection.setReadTimeout(8000);
            int status = connection.getResponseCode();
            InputStream stream = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
            String body = readStream(stream);
            if (status < 200 || status >= 300) {
                result.put("ok", false);
                result.put("error", "HTTP " + status);
                return result;
            }

            JSONObject health = new JSONObject(body);
            String app = health.optString("app", "");
            String healthStatus = health.optString("status", "");
            boolean ok = "ok".equalsIgnoreCase(healthStatus) || app.toLowerCase(Locale.US).contains("decime");
            result.put("ok", ok);
            result.put("app", app);
            result.put("env", health.optString("env", ""));
            if (!ok) {
                result.put("error", "Not a Decime API");
            }
            return result;
        } catch (Exception error) {
            try {
                result.put("ok", false);
                result.put(
                    "error",
                    error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage()
                );
            } catch (Exception ignored) {
                // ignore
            }
            return result;
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    public static JSONArray scanForDecimeApi(String subnetPrefix, int port) {
        String prefix = subnetPrefix == null ? "" : subnetPrefix.trim().replaceAll("\\.$", "");
        if (!prefix.matches("\\d{1,3}(\\.\\d{1,3}){2}")) {
            return new JSONArray();
        }

        ExecutorService pool = Executors.newFixedThreadPool(32);
        List<Callable<JSONObject>> tasks = new ArrayList<>();

        for (int host = 1; host <= 254; host++) {
            final String candidate = "http://" + prefix + "." + host + ":" + port;
            tasks.add(() -> probeCandidate(candidate));
        }

        JSONArray found = new JSONArray();
        try {
            List<Future<JSONObject>> futures = pool.invokeAll(tasks, 45, TimeUnit.SECONDS);
            for (Future<JSONObject> future : futures) {
                if (!future.isDone() || future.isCancelled()) {
                    continue;
                }
                try {
                    JSONObject item = future.get();
                    if (item != null) {
                        found.put(item);
                    }
                } catch (Exception ignored) {
                    // ignore single host failures
                }
            }
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
        } finally {
            pool.shutdownNow();
        }

        List<JSONObject> sorted = new ArrayList<>();
        for (int index = 0; index < found.length(); index++) {
            sorted.add(found.optJSONObject(index));
        }
        Collections.sort(
            sorted,
            (left, right) -> {
                String leftUrl = left == null ? "" : left.optString("url", "");
                String rightUrl = right == null ? "" : right.optString("url", "");
                return leftUrl.compareTo(rightUrl);
            }
        );

        JSONArray ordered = new JSONArray();
        for (JSONObject item : sorted) {
            if (item != null) {
                ordered.put(item);
            }
        }
        return ordered;
    }

    private static JSONObject probeCandidate(String candidate) {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(candidate + "/health").openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(700);
            connection.setReadTimeout(700);
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) {
                return null;
            }
            String body = readStream(connection.getInputStream());
            JSONObject health = new JSONObject(body);
            String app = health.optString("app", "");
            String healthStatus = health.optString("status", "");
            if (!"ok".equalsIgnoreCase(healthStatus) && !app.toLowerCase(Locale.US).contains("decime")) {
                return null;
            }
            JSONObject result = new JSONObject();
            result.put("url", candidate);
            result.put("app", app);
            result.put("env", health.optString("env", ""));
            return result;
        } catch (Exception ignored) {
            return null;
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    private static String readStream(InputStream stream) throws Exception {
        if (stream == null) {
            return "";
        }
        StringBuilder builder = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (builder.length() > 0) {
                    builder.append('\n');
                }
                builder.append(line);
            }
        }
        return builder.toString();
    }
}
