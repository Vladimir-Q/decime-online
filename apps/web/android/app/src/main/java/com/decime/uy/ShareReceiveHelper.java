package com.decime.uy;

import android.content.ClipData;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Build;
import android.util.Log;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.List;

public final class ShareReceiveHelper {

    private static final String TAG = "DecimeShare";

    public static final String PREFS_NAME = "CapacitorStorage";
    public static final String FORCE_QUICK_REPLY_KEY = "decime_force_quick_reply";
    public static final String PENDING_SHARE_TEXT_KEY = "decime_pending_share_text";
    public static final String PENDING_SHARE_AUDIO_URI_KEY = "decime_pending_share_audio_uri";
    public static final String PENDING_SHARE_ERROR_KEY = "decime_pending_share_error";

    private static boolean navigateToQuickReply = false;

    private ShareReceiveHelper() {}

    public static boolean isShareIntent(Intent intent) {
        if (intent == null) {
            return false;
        }
        String action = intent.getAction();
        return Intent.ACTION_SEND.equals(action) || Intent.ACTION_SEND_MULTIPLE.equals(action);
    }

    public static boolean shouldNavigateToQuickReply() {
        return navigateToQuickReply;
    }

    public static void clearNavigateToQuickReply() {
        navigateToQuickReply = false;
    }

    public static void handleSendIntent(Context context, Intent intent) {
        if (!isShareIntent(intent)) {
            return;
        }

        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);

        Log.d(
            TAG,
            "Share intent action=" + intent.getAction() + " type=" + intent.getType() + " extras=" + intent.getExtras()
        );

        clearPendingShare(context);
        putPreference(context, FORCE_QUICK_REPLY_KEY, "1");
        navigateToQuickReply = true;

        if (Intent.ACTION_SEND_MULTIPLE.equals(intent.getAction())) {
            handleSendMultiple(context, intent);
            ensureShareMessage(context);
            return;
        }

        String type = intent.getType();
        if ("text/plain".equals(type)) {
            Uri streamUri = getStreamUri(intent);
            if (streamUri == null) {
                String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
                if (sharedText != null && !sharedText.trim().isEmpty()) {
                    putPreference(context, PENDING_SHARE_TEXT_KEY, sanitizeSharedText(sharedText));
                    Log.d(TAG, "Stored shared text");
                    return;
                }
            }
        }

        Uri streamUri = getStreamUri(intent);
        if (streamUri != null) {
            handleStreamShare(context, streamUri, type);
            ensureShareMessage(context);
            return;
        }

        String sharedText = intent.getStringExtra(Intent.EXTRA_TEXT);
        if (sharedText != null && !sharedText.trim().isEmpty()) {
            putPreference(context, PENDING_SHARE_TEXT_KEY, sanitizeSharedText(sharedText));
            Log.d(TAG, "Stored shared text from generic SEND");
            return;
        }

        Log.w(TAG, "Share intent had no readable payload");
        ensureShareMessage(context);
    }

    private static void handleSendMultiple(Context context, Intent intent) {
        List<Uri> streams = getStreamUris(intent);
        if (streams.isEmpty()) {
            Log.w(TAG, "ACTION_SEND_MULTIPLE without stream URIs");
            return;
        }
        handleStreamShare(context, streams.get(0), intent.getType());
    }

    private static void handleStreamShare(Context context, Uri streamUri, String type) {
        String resolvedMime = type;
        if (resolvedMime == null || "*/*".equals(resolvedMime)) {
            resolvedMime = context.getContentResolver().getType(streamUri);
        }
        Log.d(TAG, "Stream uri=" + streamUri + " resolvedMime=" + resolvedMime);

        if (!isAudioLike(resolvedMime, streamUri)) {
            putPreference(
                context,
                PENDING_SHARE_ERROR_KEY,
                "Shared file is not audio. Paste text or use Upload audio on Quick Reply."
            );
            Log.w(TAG, "Shared stream is not treated as audio");
            return;
        }

        String fileUrl = copySharedAudioToCache(context, streamUri, resolvedMime);
        if (fileUrl != null) {
            putPreference(context, PENDING_SHARE_AUDIO_URI_KEY, fileUrl);
            Log.d(TAG, "Stored shared audio at " + fileUrl);
        } else {
            putPreference(
                context,
                PENDING_SHARE_ERROR_KEY,
                "Could not read shared audio. Use Upload audio on Quick Reply."
            );
            Log.w(TAG, "Failed to copy shared audio");
        }
    }

    private static void ensureShareMessage(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        if (prefs.contains(PENDING_SHARE_TEXT_KEY) || prefs.contains(PENDING_SHARE_AUDIO_URI_KEY)) {
            return;
        }
        if (!prefs.contains(PENDING_SHARE_ERROR_KEY)) {
            putPreference(
                context,
                PENDING_SHARE_ERROR_KEY,
                "Could not read WhatsApp share. Paste the message or use Upload audio."
            );
        }
    }

    private static void clearPendingShare(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit()
            .remove(FORCE_QUICK_REPLY_KEY)
            .remove(PENDING_SHARE_TEXT_KEY)
            .remove(PENDING_SHARE_AUDIO_URI_KEY)
            .remove(PENDING_SHARE_ERROR_KEY)
            .commit();
    }

    private static Uri getStreamUri(Intent intent) {
        Uri streamUri = getParcelableStream(intent);
        if (streamUri != null) {
            return streamUri;
        }

        ClipData clipData = intent.getClipData();
        if (clipData != null && clipData.getItemCount() > 0) {
            return clipData.getItemAt(0).getUri();
        }

        return null;
    }

    @SuppressWarnings("deprecation")
    private static List<Uri> getStreamUris(Intent intent) {
        List<Uri> streams = new ArrayList<>();

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ArrayList<Uri> extraStreams = intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri.class);
            if (extraStreams != null) {
                streams.addAll(extraStreams);
            }
        } else {
            ArrayList<Uri> extraStreams = intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM);
            if (extraStreams != null) {
                streams.addAll(extraStreams);
            }
        }

        if (!streams.isEmpty()) {
            return streams;
        }

        Uri single = getStreamUri(intent);
        if (single != null) {
            streams.add(single);
        }
        return streams;
    }

    @SuppressWarnings("deprecation")
    private static Uri getParcelableStream(Intent intent) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            return intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri.class);
        }
        return intent.getParcelableExtra(Intent.EXTRA_STREAM);
    }

    private static boolean isAudioLike(String mimeType, Uri uri) {
        if (mimeType != null) {
            String mime = mimeType.toLowerCase();
            if (mime.startsWith("audio/")) {
                return true;
            }
            if ("application/octet-stream".equals(mime)) {
                return true;
            }
            if ("video/mp4".equals(mime) || "video/3gpp".equals(mime)) {
                return true;
            }
            if ("*/*".equals(mime)) {
                return true;
            }
        }

        String path = uri != null ? uri.toString().toLowerCase() : "";
        return path.contains("opus")
            || path.contains(".ogg")
            || path.contains(".m4a")
            || path.contains(".mp3")
            || path.contains(".aac")
            || path.contains(".wav")
            || path.contains(".3gp")
            || path.contains("audio")
            || path.contains("ptt")
            || path.contains("voice")
            || path.contains("whatsapp");
    }

    private static void putPreference(Context context, String key, String value) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().putString(key, value).commit();
    }

    private static String sanitizeSharedText(String raw) {
        if (raw == null) {
            return "";
        }
        return raw
            .replaceAll("[\\u200B-\\u200D\\uFEFF\\u202A-\\u202E]", "")
            .replace("\r\n", "\n")
            .trim();
    }

    private static String copySharedAudioToCache(Context context, Uri uri, String mimeType) {
        try {
            String extension = extensionFromMime(mimeType, uri);
            File dest = new File(context.getCacheDir(), "decime-shared-audio." + extension);

            try (InputStream in = context.getContentResolver().openInputStream(uri);
                 OutputStream out = new FileOutputStream(dest)) {
                if (in == null) {
                    return null;
                }
                byte[] buffer = new byte[8192];
                int read;
                while ((read = in.read(buffer)) != -1) {
                    out.write(buffer, 0, read);
                }
            }

            if (dest.length() == 0) {
                return null;
            }

            Log.d(TAG, "Stored shared audio at " + dest.getAbsolutePath() + " bytes=" + dest.length());
            return "https://localhost/_capacitor_file_" + dest.getAbsolutePath();
        } catch (Exception error) {
            Log.e(TAG, "copySharedAudioToCache failed", error);
            return null;
        }
    }

    private static String extensionFromMime(String mimeType, Uri uri) {
        String mime = mimeType != null ? mimeType.toLowerCase() : "";
        if (mime.contains("ogg") || mime.contains("opus")) {
            return "ogg";
        }
        if (mime.contains("mpeg") || mime.contains("mp3")) {
            return "mp3";
        }
        if (mime.contains("mp4") || mime.contains("m4a") || mime.contains("aac")) {
            return "m4a";
        }
        if (mime.contains("3gpp")) {
            return "3gp";
        }
        if (mime.contains("wav")) {
            return "wav";
        }

        String path = uri != null ? uri.toString().toLowerCase() : "";
        if (path.contains(".ogg") || path.contains("opus")) {
            return "ogg";
        }
        if (path.contains(".mp3")) {
            return "mp3";
        }
        if (path.contains(".m4a") || path.contains(".aac")) {
            return "m4a";
        }
        if (path.contains(".3gp")) {
            return "3gp";
        }
        if (path.contains(".wav")) {
            return "wav";
        }
        return "ogg";
    }
}
