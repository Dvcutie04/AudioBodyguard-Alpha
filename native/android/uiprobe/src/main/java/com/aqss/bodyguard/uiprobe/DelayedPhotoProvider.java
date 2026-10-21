package com.aqss.bodyguard.uiprobe;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Test APK only: blocks an actual content-provider import until the observer releases it. */
public final class DelayedPhotoProvider extends ContentProvider {
    private File fixture;
    private volatile CountDownLatch gate = new CountDownLatch(1);
    private volatile boolean opened;
    private volatile boolean released;

    @Override public boolean onCreate() {
        try {
            fixture = new File(getContext().getCacheDir(), "deadline-label-fixture.png");
            java.security.MessageDigest digest = java.security.MessageDigest.getInstance("SHA-256");
            try (InputStream source = getContext().getAssets().open("tv-photo-labels.png");
                 OutputStream target = new java.io.FileOutputStream(fixture)) {
                byte[] buffer = new byte[8192]; int count;
                while ((count = source.read(buffer)) != -1) { target.write(buffer, 0, count); digest.update(buffer, 0, count); }
            }
            StringBuilder hex = new StringBuilder();
            for (byte value : digest.digest()) hex.append(String.format(java.util.Locale.ROOT, "%02x", value & 255));
            if (!"2f55775447c5d28841737a25713ae83a76b37bb6d614fa33007621ce92853f31".contentEquals(hex))
                throw new IllegalStateException("Delayed photo fixture differs");
            return true;
        } catch (Exception failure) { throw new IllegalStateException("Cannot prepare delayed photo fixture", failure); }
    }
    @Override public Bundle call(String method, String argument, Bundle extras) {
        if ("prepare".equals(method)) { gate.countDown(); gate = new CountDownLatch(1); opened = false; released = false; }
        else if ("release".equals(method)) { released = true; gate.countDown(); }
        else if (!"state".equals(method)) throw new IllegalArgumentException("Unknown photo test command");
        Bundle state = new Bundle(); state.putBoolean("opened", opened); state.putBoolean("released", released); return state;
    }
    @Override public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        if (!"r".equals(mode) || !("/delayed.png".equals(uri.getPath()) || "/fixture.png".equals(uri.getPath())))
            throw new FileNotFoundException("Unknown read-only test photo");
        if ("/delayed.png".equals(uri.getPath())) {
            CountDownLatch pending = gate; opened = true;
            try {
                if (!pending.await(60, TimeUnit.SECONDS)) throw new FileNotFoundException("Observer did not release test photo");
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt(); throw new FileNotFoundException("Test photo interrupted");
            }
        }
        return ParcelFileDescriptor.open(fixture, ParcelFileDescriptor.MODE_READ_ONLY);
    }
    @Override public String getType(Uri uri) { return "image/png"; }
    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] args, String sort) {
        String[] columns = projection == null ? new String[] {OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE} : projection;
        MatrixCursor cursor = new MatrixCursor(columns); Object[] values = new Object[columns.length];
        for (int i = 0; i < columns.length; i++) {
            if (OpenableColumns.DISPLAY_NAME.equals(columns[i])) values[i] = "deadline-label-fixture.png";
            if (OpenableColumns.SIZE.equals(columns[i])) values[i] = fixture.length();
        }
        cursor.addRow(values); return cursor;
    }
    @Override public Uri insert(Uri uri, ContentValues values) { throw new UnsupportedOperationException(); }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] args) { throw new UnsupportedOperationException(); }
    @Override public int delete(Uri uri, String selection, String[] args) { throw new UnsupportedOperationException(); }
}
