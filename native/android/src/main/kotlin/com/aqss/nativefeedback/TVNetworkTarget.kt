package com.aqss.nativefeedback

import java.util.Collections

/** One explicitly entered private IPv4 host; never a discovered or verified TV. */
class LocalTVTarget private constructor(val address: String, private val values: List<Int>) {
    fun addressBytes(): ByteArray = values.map { it.toByte() }.toByteArray()

    companion object {
        val PORTS: List<Int> = Collections.unmodifiableList(listOf(7345, 9000))
        const val TIMEOUT_MILLIS = 4000
        const val BOUNDARY = "TV identity, pairing and audio protection are not verified."
        const val INVALID_ADDRESS = "Enter the private IPv4 address shown in your TV’s network settings."

        fun parse(input: String): LocalTVTarget? {
            if (input.length > 64) return null
            val value = input.trim()
            if (value.isEmpty() || value.length > 15) return null
            val parts = value.split('.')
            if (parts.size != 4) return null
            val bytes = parts.map { part ->
                if (part.isEmpty() || part.any { it !in '0'..'9' } ||
                    (part.length > 1 && part.first() == '0')) return null
                part.toIntOrNull()?.takeIf { it in 0..255 } ?: return null
            }
            val privateRange = bytes[0] == 10 || (bytes[0] == 172 && bytes[1] in 16..31) ||
                (bytes[0] == 192 && bytes[1] == 168)
            if (!privateRange || bytes[3] !in 1..254) return null
            return LocalTVTarget(value, bytes)
        }
    }
}
