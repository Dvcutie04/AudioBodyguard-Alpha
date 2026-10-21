package com.aqss.bodyguard.prototype

import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.MediaStore
import android.util.Log
import androidx.core.content.FileProvider
import java.io.File

/** Only the dedicated temporary camera directory is exposed by this provider. */
class TVPhotoFileProvider : FileProvider()

/** One unique app-private output. Never published to MediaStore or retained as a gallery photo. */
internal class TVPhotoCapture private constructor(
    private val context: Context,
    private val file: File,
    val uri: Uri
) {
    fun intent(): Intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE).apply {
        putExtra(MediaStore.EXTRA_OUTPUT, uri)
        clipData = ClipData.newRawUri("TV photo", uri)
        addFlags(grants)
    }

    fun revokeAccess() {
        try { context.revokeUriPermission(uri, grants) }
        catch (_: RuntimeException) { Log.w("TVPhotoCapture", "Temporary camera access could not be revoked") }
    }

    // May also be called by Clear/Close while decoding. Repeated cleanup is safe;
    // an open descriptor is not promised to be canceled by unlinking its file.
    @Synchronized fun close() {
        revokeAccess()
        if (!file.delete() && file.exists()) Log.w("TVPhotoCapture", "Temporary camera file could not be removed")
    }

    companion object {
        private val grants = Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION
        private var prepared = false

        @Synchronized fun create(context: Context): TVPhotoCapture {
            val app = context.applicationContext
            val directory = File(app.cacheDir, "tv-camera")
            check(directory.isDirectory || directory.mkdirs()) { "Camera cache unavailable" }
            if (!prepared) {
                // First capture in a new process: old selections cannot be resumed.
                // Do this once, so another Activity cannot delete a live capture.
                val abandoned = checkNotNull(directory.listFiles()) { "Camera cache unavailable" }
                for (file in abandoned) {
                    if (!file.isFile || !file.name.startsWith("capture-")) continue
                    TVPhotoCapture(app, file, FileProvider.getUriForFile(app, app.packageName + ".tvphotos", file)).close()
                    check(!file.exists()) { "Previous camera photo could not be removed" }
                }
                prepared = true
            }
            val file = File.createTempFile("capture-", ".jpg", directory)
            return try { TVPhotoCapture(app, file, FileProvider.getUriForFile(app, app.packageName + ".tvphotos", file)) }
            catch (error: RuntimeException) { file.delete(); throw error }
        }
    }
}
