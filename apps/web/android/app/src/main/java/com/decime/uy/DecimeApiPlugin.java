package com.decime.uy;

import android.util.Log;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import android.util.Base64;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

@CapacitorPlugin(name = "DecimeApi")
public class DecimeApiPlugin extends Plugin {
    private static final String TAG = "DecimeApiPlugin";

    @PluginMethod
    public void probeHealth(PluginCall call) {
        String url = call.getString("url");
        if (url == null || url.trim().isEmpty()) {
            call.reject("Missing url");
            return;
        }

        new Thread(
                () -> {
                    org.json.JSONObject probe = LanScanHelper.probeHealth(url);
                    JSObject result = new JSObject();
                    try {
                        result.put("ok", probe.optBoolean("ok", false));
                        result.put("app", probe.optString("app", ""));
                        result.put("env", probe.optString("env", ""));
                        result.put("error", probe.optString("error", ""));
                    } catch (Exception error) {
                        rejectOnMain(call, error.getMessage());
                        return;
                    }
                    resolveOnMain(call, result);
                }
            )
            .start();
    }

    @PluginMethod
    public void getNetworkInfo(PluginCall call) {
        String phoneIp = LanScanHelper.getPhoneIpv4(getContext());
        String subnetPrefix = LanScanHelper.getSubnetPrefix(getContext());
        JSObject result = new JSObject();
        result.put("phoneIp", phoneIp);
        result.put("subnetPrefix", subnetPrefix);
        call.resolve(result);
    }

    @PluginMethod
    public void scanLan(PluginCall call) {
        String subnetPrefix = call.getString("subnetPrefix", LanScanHelper.getSubnetPrefix(getContext()));
        int port = call.getInt("port", 8000);

        new Thread(
                () -> {
                    try {
                        org.json.JSONArray found = LanScanHelper.scanForDecimeApi(subnetPrefix, port);
                        JSObject result = new JSObject();
                        result.put("resultsJson", found.toString());
                        resolveOnMain(call, result);
                    } catch (Exception error) {
                        rejectOnMain(call, error.getMessage());
                    }
                }
            )
            .start();
    }

    @PluginMethod
    public void openApiSetup(PluginCall call) {
        MainActivity activity = (MainActivity) getActivity();
        if (activity == null || getBridge() == null || getBridge().getWebView() == null) {
            call.reject("WebView not ready");
            return;
        }

        activity.runOnUiThread(
            () ->
                ApiConfigHelper.showSetupDialog(
                    activity,
                    getBridge().getWebView(),
                    true,
                    () -> {
                        String url = ApiConfigHelper.readApiUrl(activity);
                        ApiConfigHelper.injectApiUrl(getBridge().getWebView(), url);
                        activity.scheduleApiInjectionFromPlugin(6);
                        JSObject result = new JSObject();
                        result.put("url", url);
                        call.resolve(result);
                    }
                )
        );
    }

    @PluginMethod
    public void getApiUrl(PluginCall call) {
        String url = ApiConfigHelper.readApiUrl(getContext());
        Log.i(TAG, "getApiUrl -> " + url);
        JSObject result = new JSObject();
        result.put("url", url);
        call.resolve(result);
    }

    @PluginMethod
    public void setApiUrl(PluginCall call) {
        String url = call.getString("url");
        if (url == null || url.trim().isEmpty()) {
            call.reject("Missing url");
            return;
        }
        String normalized = ApiConfigHelper.normalizeUrlPublic(url);
        ApiConfigHelper.saveApiUrl(getContext(), normalized);
        if (getBridge() != null && getBridge().getWebView() != null) {
            ApiConfigHelper.injectApiUrl(getBridge().getWebView(), normalized);
            MainActivity activity = (MainActivity) getActivity();
            if (activity != null) {
                activity.scheduleApiInjectionFromPlugin(4);
            }
        }
        JSObject result = new JSObject();
        result.put("url", normalized);
        call.resolve(result);
    }

    @PluginMethod
    public void request(PluginCall call) {
        String url = call.getString("url");
        if (url == null || url.trim().isEmpty()) {
            call.reject("Missing url");
            return;
        }

        String method = call.getString("method", "GET").toUpperCase();
        String body = call.getString("body");
        JSObject headersObj = call.getObject("headers", new JSObject());
        final String requestUrl = ApiConfigHelper.normalizeRequestUrl(url);
        Log.i(TAG, "request " + method + " " + requestUrl);

        new Thread(
                () -> {
                    HttpURLConnection connection = null;
                    try {
                        connection = (HttpURLConnection) new URL(requestUrl).openConnection();
                        connection.setRequestMethod(method);
                        connection.setConnectTimeout(30000);
                        connection.setReadTimeout(300000);
                        connection.setInstanceFollowRedirects(true);

                        if (headersObj != null) {
                            java.util.Iterator<String> keys = headersObj.keys();
                            while (keys.hasNext()) {
                                String key = keys.next();
                                String value = headersObj.optString(key, null);
                                if (value != null) {
                                    connection.setRequestProperty(key, value);
                                }
                            }
                        }

                        if (body != null
                            && !body.isEmpty()
                            && ("POST".equals(method)
                                || "PUT".equals(method)
                                || "PATCH".equals(method))) {
                            connection.setDoOutput(true);
                            byte[] payload = body.getBytes(StandardCharsets.UTF_8);
                            connection.setFixedLengthStreamingMode(payload.length);
                            try (OutputStream output = connection.getOutputStream()) {
                                output.write(payload);
                            }
                        }

                        int status = connection.getResponseCode();
                        String contentType = connection.getContentType();
                        if (contentType == null || contentType.isEmpty()) {
                            contentType = "application/octet-stream";
                        }
                        InputStream stream =
                            status >= 400 ? connection.getErrorStream() : connection.getInputStream();
                        byte[] rawBytes = readAllBytes(stream);

                        JSObject result = new JSObject();
                        result.put("status", status);
                        result.put("contentType", contentType);

                        String mime = contentType.toLowerCase();
                        String pathLower = requestUrl.toLowerCase();
                        boolean binaryByUrl =
                            pathLower.contains("/audio/files/")
                                || pathLower.endsWith(".wav")
                                || pathLower.endsWith(".mp3")
                                || pathLower.endsWith(".ogg")
                                || pathLower.endsWith(".m4a")
                                || pathLower.endsWith(".webm");
                        boolean binary =
                            binaryByUrl
                                || mime.startsWith("audio/")
                                || mime.startsWith("image/")
                                || mime.startsWith("video/")
                                || mime.contains("octet-stream")
                                || mime.contains("wav")
                                || mime.contains("mpeg");

                        if (binary) {
                            String encoded = Base64.encodeToString(rawBytes, Base64.NO_WRAP);
                            result.put("body", "");
                            result.put("bodyBase64", encoded);
                            Log.i(
                                TAG,
                                "request done HTTP "
                                    + status
                                    + " binaryBytes="
                                    + rawBytes.length
                                    + " type="
                                    + contentType
                            );
                        } else {
                            String responseBody = new String(rawBytes, StandardCharsets.UTF_8);
                            result.put("body", responseBody);
                            Log.i(
                                TAG,
                                "request done HTTP " + status + " bytes=" + responseBody.length()
                            );
                        }
                        resolveOnMain(call, result);
                    } catch (Exception error) {
                        Log.e(TAG, "request failed", error);
                        rejectOnMain(call, formatNetworkError(error, requestUrl));
                    } finally {
                        if (connection != null) {
                            connection.disconnect();
                        }
                    }
                }
            )
            .start();
    }

    @PluginMethod
    public void multipartRequest(PluginCall call) {
        final String url = ApiConfigHelper.normalizeRequestUrl(call.getString("url", ""));
        if (url.isEmpty()) {
            call.reject("Missing url");
            return;
        }

        String filePath = call.getString("filePath");
        String fileBase64 = call.getString("fileBase64");
        String fileName = call.getString("fileName", "audio.ogg");
        String mimeType = call.getString("mimeType", "application/octet-stream");
        JSObject fieldsObj = call.getObject("fields", new JSObject());
        JSObject headersObj = call.getObject("headers", new JSObject());
        Log.i(TAG, "multipartRequest " + url + " filePath=" + filePath + " fileName=" + fileName);

        new Thread(
                () -> {
                    HttpURLConnection connection = null;
                    try {
                        byte[] fileBytes;
                        if (filePath != null && !filePath.trim().isEmpty()) {
                            File file = new File(filePath.trim());
                            if (!file.exists() || file.length() == 0) {
                                call.reject("Audio file not found or empty");
                                return;
                            }
                            fileBytes = readFileBytes(file);
                        } else if (fileBase64 != null && !fileBase64.isEmpty()) {
                            fileBytes = Base64.decode(fileBase64, Base64.DEFAULT);
                            if (fileBytes.length == 0) {
                                call.reject("Audio payload is empty");
                                return;
                            }
                        } else {
                            call.reject("Missing filePath or fileBase64");
                            return;
                        }

                        String boundary = "----DecimeFormBoundary" + System.currentTimeMillis();
                        connection = (HttpURLConnection) new URL(url).openConnection();
                        connection.setRequestMethod("POST");
                        connection.setConnectTimeout(30000);
                        connection.setReadTimeout(300000);
                        connection.setDoOutput(true);
                        connection.setRequestProperty(
                            "Content-Type",
                            "multipart/form-data; boundary=" + boundary
                        );
                        if (headersObj != null) {
                            java.util.Iterator<String> headerKeys = headersObj.keys();
                            while (headerKeys.hasNext()) {
                                String key = headerKeys.next();
                                String value = headersObj.optString(key, null);
                                if (value != null && !"Content-Type".equalsIgnoreCase(key)) {
                                    connection.setRequestProperty(key, value);
                                }
                            }
                        }

                        try (OutputStream output = connection.getOutputStream()) {
                            if (fieldsObj != null) {
                                java.util.Iterator<String> keys = fieldsObj.keys();
                                while (keys.hasNext()) {
                                    String key = keys.next();
                                    String value = fieldsObj.optString(key, "");
                                    writeFormField(output, boundary, key, value);
                                }
                            }
                            writeFileField(output, boundary, "file", fileName, mimeType, fileBytes);
                            output.write(("--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8));
                        }

                        int status = connection.getResponseCode();
                        InputStream stream = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
                        String responseBody = readStream(stream);

                        JSObject result = new JSObject();
                        result.put("status", status);
                        result.put("body", responseBody);
                        Log.i(
                            TAG,
                            "multipartRequest done HTTP " + status + " bytes=" + responseBody.length()
                        );
                        resolveOnMain(call, result);
                    } catch (Exception error) {
                        Log.e(TAG, "multipartRequest failed", error);
                        rejectOnMain(call, formatNetworkError(error, url));
                    } finally {
                        if (connection != null) {
                            connection.disconnect();
                        }
                    }
                }
            )
            .start();
    }

    private void resolveOnMain(PluginCall call, JSObject result) {
        if (getActivity() == null) {
            call.resolve(result);
            return;
        }
        getActivity().runOnUiThread(() -> call.resolve(result));
    }

    private void rejectOnMain(PluginCall call, String message) {
        if (getActivity() == null) {
            call.reject(message);
            return;
        }
        getActivity().runOnUiThread(() -> call.reject(message));
    }

    private static String formatNetworkError(Exception error, String url) {
        String detail = error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage();
        if (error instanceof java.net.ConnectException || detail.contains("failed to connect")) {
            return "Телефон не достучался до ПК по "
                + url
                + ". Проверьте: API запущен с --host 0.0.0.0 --port 8000, Windows Firewall разрешает порт 8000, "
                + "телефон и ПК в одной Wi‑Fi. ("
                + detail
                + ")";
        }
        if (error instanceof java.net.SocketTimeoutException) {
            return "Таймаут при обращении к " + url + ". Проверьте Wi‑Fi и что API на ПК не завис.";
        }
        return detail + " (" + url + ")";
    }

    private static byte[] readFileBytes(File file) throws Exception {
        byte[] data = new byte[(int) file.length()];
        try (FileInputStream input = new FileInputStream(file)) {
            int read = input.read(data);
            if (read != data.length) {
                throw new Exception("Could not read full audio file");
            }
        }
        return data;
    }

    private static void writeFormField(OutputStream output, String boundary, String name, String value)
        throws Exception {
        output.write(("--" + boundary + "\r\n").getBytes(StandardCharsets.UTF_8));
        output.write(
            ("Content-Disposition: form-data; name=\"" + name + "\"\r\n\r\n").getBytes(StandardCharsets.UTF_8)
        );
        output.write((value + "\r\n").getBytes(StandardCharsets.UTF_8));
    }

    private static void writeFileField(
        OutputStream output,
        String boundary,
        String fieldName,
        String fileName,
        String mimeType,
        byte[] fileBytes
    ) throws Exception {
        output.write(("--" + boundary + "\r\n").getBytes(StandardCharsets.UTF_8));
        output.write(
            ("Content-Disposition: form-data; name=\"" + fieldName + "\"; filename=\"" + fileName + "\"\r\n")
                .getBytes(StandardCharsets.UTF_8)
        );
        output.write(("Content-Type: " + mimeType + "\r\n\r\n").getBytes(StandardCharsets.UTF_8));
        output.write(fileBytes);
        output.write("\r\n".getBytes(StandardCharsets.UTF_8));
    }

    private static byte[] readAllBytes(InputStream stream) throws Exception {
        if (stream == null) {
            return new byte[0];
        }
        java.io.ByteArrayOutputStream buffer = new java.io.ByteArrayOutputStream();
        byte[] chunk = new byte[8192];
        int read;
        while ((read = stream.read(chunk)) != -1) {
            buffer.write(chunk, 0, read);
        }
        stream.close();
        return buffer.toByteArray();
    }

    private static String readStream(InputStream stream) throws Exception {
        return new String(readAllBytes(stream), StandardCharsets.UTF_8);
    }
}
