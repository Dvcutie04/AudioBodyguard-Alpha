package com.aqss.nativefeedback

import java.util.Locale

private const val PHOTO_TEXT_BYTES = 8192
private const val PHOTO_TEXT_ROWS = 100
private fun photoLineBreak(value: Char): Boolean = value in "\n\r\u000B\u000C\u0085\u2028\u2029"

private fun photoTextFits(text: String): Boolean {
    if (text.length > PHOTO_TEXT_BYTES || text.toByteArray(Charsets.UTF_8).size > PHOTO_TEXT_BYTES) return false
    var rows = 1
    var previousCR = false
    for (value in text) {
        if (photoLineBreak(value) && !(value == '\n' && previousCR)) {
            rows++
            if (rows > PHOTO_TEXT_ROWS) return false
        }
        previousCR = value == '\r'
    }
    return true
}

/** Reject the whole OCR collection rather than hiding a row in a shortened prefix. */
fun boundedTVPhotoText(rows: Sequence<String?>): String? {
    val text = StringBuilder()
    var count = 0
    var bytes = 0
    for (row in rows) {
        if (count == PHOTO_TEXT_ROWS || row == null || row.length > PHOTO_TEXT_BYTES ||
            row.isBlank() || row.any(::photoLineBreak)) return null
        val size = row.toByteArray(Charsets.UTF_8).size
        val separator = if (count == 0) 0 else 1
        if (size > PHOTO_TEXT_BYTES - bytes - separator) return null
        if (count > 0) text.append('\n')
        text.append(row)
        bytes += size + separator
        count++
    }
    return text.toString()
}

/** Untrusted presentation hints; there is intentionally no connection or authority API. */
class TVPhotoHints(text: String) {
    val brand: String?
    val model: String?
    val address: String?
    init {
        val modelLabel = "MODEL(?:[ \\t]+(?:NAME|CODE|NUMBER|NO\\.?))?"
        val addressLabel = "(?:IPV4[ \\t]+IP[ \\t]+ADDRESS|IP(?:V4)?(?:[ \\t]+ADDRESS)?)"
        val upper = if (photoTextFits(text))
            text.uppercase(Locale.ROOT).replace(Regex("(?m)^[ \\t]*($modelLabel|$addressLabel)[ \\t]*[:=]?[ \\t]*\\r?\\n[ \\t]*"), "$1: ") else ""
        fun matches(pattern: String) = Regex(pattern, RegexOption.MULTILINE).findAll(upper).map { it.groupValues[1] }.toSet()
        // Include malformed labelled values before checking uniqueness: do not salvage
        // one readable candidate from a conflicting or unreadable second row.
        fun labelled(label: String): String? {
            val explicit = matches("^[ \\t]*$label[ \\t]*[:=][ \\t]*([^\\r\\n]*)[ \\t]*\\r?$")
            // With no separator, a whole value may follow the label. Do not let
            // bare IPv4 consume the start of 'IPv4 Default Gateway: ...'.
            val spaced = matches("^[ \\t]*$label[ \\t]+([^:=\\r\\n]*)[ \\t]*\\r?$")
            return (explicit + spaced).map { it.trim(' ', '\t') }.toSet().singleOrNull()
        }
        brand = matches("\\b(SAMSUNG|LG|SONY|TCL|HISENSE|VIZIO|PANASONIC|PHILIPS)\\b").singleOrNull()
        model = labelled(modelLabel)?.takeIf { Regex("[A-Z0-9][A-Z0-9._-]{1,39}").matches(it) && it.any { c -> c in '0'..'9' } }
        address = labelled(addressLabel)?.takeIf(::isPrivateIPv4)
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
