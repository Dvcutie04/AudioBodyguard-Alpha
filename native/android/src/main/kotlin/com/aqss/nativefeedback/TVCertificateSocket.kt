package com.aqss.nativefeedback

import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Proxy
import java.net.Socket
import java.security.MessageDigest
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import java.util.concurrent.atomic.AtomicReference
import javax.net.ssl.KeyManager
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLException
import javax.net.ssl.SSLSocket
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

/** Reads one leaf fingerprint by rejecting TLS at the trust callback. */
internal class TVCertificateSocket(
    private val bindSocket: (Socket) -> Unit,
    private val fingerprint: AtomicReference<String>,
    private val socket: Socket = Socket(Proxy.NO_PROXY),
) : TVProbeSocket {
    @Volatile private var tlsSocket: SSLSocket? = null

    override fun connect(target: LocalTVTarget, port: Int, timeoutMillis: Int) {
        bindSocket(socket)
        socket.connect(InetSocketAddress(InetAddress.getByAddress(target.addressBytes()), port), timeoutMillis)

        val observed = AtomicReference<String>()
        val observer = object : X509TrustManager {
            override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()

            override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {
                throw CertificateException("Client certificate validation is unavailable")
            }

            override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {
                val der = chain?.firstOrNull()?.encoded
                if (der != null && der.size in 1..MAX_CERTIFICATE_BYTES) {
                    val digest = MessageDigest.getInstance("SHA-256").digest(der)
                    observed.set(digest.joinToString("") { "%02x".format(it) })
                }
                throw CertificateException("Certificate observation ends the TLS handshake")
            }
        }
        val context = SSLContext.getInstance("TLS").apply {
            init(emptyArray<KeyManager>(), arrayOf<TrustManager>(observer), null)
        }
        val tls = context.socketFactory.createSocket(socket, target.address, port, false) as SSLSocket
        tlsSocket = tls
        tls.useClientMode = true
        tls.soTimeout = timeoutMillis
        try {
            tls.startHandshake()
        } catch (error: SSLException) {
            fingerprint.set(observed.get() ?: throw error)
            return
        }
        throw SSLException("Certificate observation unexpectedly completed a TLS handshake")
    }

    override fun close() {
        // Close the transport first so a blocked TLS read can return.
        try { socket.close() } finally { tlsSocket?.close() }
    }

    private companion object {
        const val MAX_CERTIFICATE_BYTES = 16 * 1024
    }
}
