package com.aqss.nativefeedback

import java.util.Locale

/** Untrusted presentation hints; there is intentionally no connection or authority API. */
class TVPhotoHints(text: String) {
    val brand: String?
    val model: String?
    val address: String?
    init {
        val upper = if (text.toByteArray(Charsets.UTF_8).size <= 8192) text.uppercase(Locale.ROOT).replace(Regex("(?m)^(MODEL(?: CODE| NUMBER| NO\\.?)?|IP(?:V4)?(?: ADDRESS)?)[ \\t]*[:=]?[ \\t]*\\r?\\n[ \\t]*"), "$1: ") else ""
        fun matches(pattern: String) = Regex(pattern, RegexOption.MULTILINE).findAll(upper).map { it.groupValues[1] }.toSet()
        brand = matches("\\b(SAMSUNG|LG|SONY|TCL|HISENSE|VIZIO|PANASONIC|PHILIPS)\\b").singleOrNull()
        model = matches("^[ \\t]*MODEL(?: CODE| NUMBER| NO\\.?)?(?:[ \\t]*[:=][ \\t]*|[ \\t]+)([A-Z0-9][A-Z0-9._-]{1,39})[ \\t]*$").singleOrNull()?.takeIf { it.any(Char::isDigit) }
        address = matches("^[ \\t]*IP(?:V4)?(?: ADDRESS)?(?:[ \\t]*[:=][ \\t]*|[ \\t]+)([0-9.]+)[ \\t]*$").singleOrNull()?.takeIf(::isPrivateIPv4)
    }
    companion object {
        fun isPrivateIPv4(value: String): Boolean {
            val parts = value.split('.')
            if (parts.size != 4) return false
            val octets = parts.map { part ->
                if (part.isEmpty() || part.length > 3 || part.any { it !in '0'..'9' } || (part.length > 1 && part.startsWith('0'))) return false
                part.toIntOrNull()?.takeIf { it <= 255 } ?: return false
            }
            return octets[0] == 10 || (octets[0] == 172 && octets[1] in 16..31) || (octets[0] == 192 && octets[1] == 168)
        }
    }
}
