package com.aqss.nativefeedback

import java.io.IOException
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Proxy
import java.net.ServerSocket
import java.net.Socket
import java.net.SocketAddress
import java.math.BigInteger
import java.security.KeyStore
import java.security.MessageDigest
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
import javax.net.ssl.KeyManagerFactory
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLServerSocket
import javax.net.ssl.SSLSocket
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class TVCertificateSocketTest {
    private val target = LocalTVTarget.parse("192.168.1.105")!!
    private val loopback = InetAddress.getByName("127.0.0.1")

    @Test fun observesTheActualLeafAndTheServerNeverCompletesTls() {
        val password = "fixture-only".toCharArray()
        val keys = KeyStore.getInstance("PKCS12")
        val resource = assertNotNull(javaClass.getResourceAsStream("/tv-loopback-fixture.p12.fixture"))
        resource.use { keys.load(it, password) }
        val digest = MessageDigest.getInstance("SHA-256").digest(keys.getCertificate("loopback-tv").encoded)
        val expected = BigInteger(1, digest).toString(16).padStart(64, '0')
        val keyManager = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm())
        keyManager.init(keys, password)
        val context = SSLContext.getInstance("TLS").apply { init(keyManager.keyManagers, null, null) }
        val server = context.serverSocketFactory.createServerSocket(0, 1, loopback) as SSLServerSocket
        server.use {
            server.soTimeout = 4000
            val handshakeSucceeded = AtomicBoolean()
            val handshakeError = AtomicReference<IOException>()
            val served = CountDownLatch(1)
            Thread({
                try {
                    (server.accept() as SSLSocket).use { peer ->
                        peer.soTimeout = 4000
                        peer.startHandshake()
                        handshakeSucceeded.set(true)
                    }
                } catch (error: IOException) {
                    handshakeError.set(error)
                } finally { served.countDown() }
            }, "test-tv-tls-server").apply { isDaemon = true; start() }
            val observed = AtomicReference<String>()
            val probe = TVCertificateSocket({}, observed, mappedSocket(server.localPort))
            try {
                probe.connect(target, 9000, 4000)
                assertEquals(expected, observed.get())
            } finally { probe.close() }
            assertTrue(served.await(5, TimeUnit.SECONDS))
            assertFalse(handshakeSucceeded.get())
            assertNotNull(handshakeError.get())
        }
    }

    @Test fun aServiceWithoutTlsProducesNoFingerprint() {
        ServerSocket(0, 1, loopback).use { server ->
            server.soTimeout = 4000
            Thread({
                server.accept().use { it.getOutputStream().write("plain service".toByteArray()) }
            }, "test-tv-plain-server").apply { isDaemon = true; start() }
            val observed = AtomicReference<String>()
            val probe = TVCertificateSocket({}, observed, mappedSocket(server.localPort))
            try {
                assertFailsWith<IOException> { probe.connect(target, 9000, 4000) }
                assertNull(observed.get())
            } finally { probe.close() }
        }
    }

    @Test fun certificateDeadlineClosesTheOwnedSocketWithoutTryingAnotherPort() {
        val runner = TVNetworkRunner()
        val done = CountDownLatch(1)
        val result = AtomicReference<TVNetworkResult>()
        val boundSocket = AtomicReference<Socket>()
        assertNotNull(runner.readCertificate(target, 9000, { socket ->
            check(boundSocket.compareAndSet(null, socket)) { "Certificate reading tried a second socket" }
            val limit = System.nanoTime() + TimeUnit.SECONDS.toNanos(7)
            while (!socket.isClosed && System.nanoTime() < limit) Thread.sleep(20)
            throw IOException("Fixture ends before any socket connection")
        }) { _, value -> result.set(value); done.countDown() })
        assertTrue(done.await(8, TimeUnit.SECONDS))
        assertTrue(assertNotNull(boundSocket.get()).isClosed)
        assertEquals(TVNetworkResult(TVNetworkOutcome.STOPPED), result.get())
    }

    @Test fun aPortOutsideTheTrialCannotStartACertificateRead() {
        assertNull(TVNetworkRunner().readCertificate(target, 443, { error("Must not bind") }) { _, _ ->
            error("Must not complete an invalid request")
        })
    }

    private fun mappedSocket(fixturePort: Int) = object : Socket(Proxy.NO_PROXY) {
        override fun connect(endpoint: SocketAddress, timeout: Int) {
            val requested = endpoint as InetSocketAddress
            assertEquals(target.address, requested.address.hostAddress)
            assertEquals(9000, requested.port)
            super.connect(InetSocketAddress(loopback, fixturePort), timeout)
        }
    }
}
