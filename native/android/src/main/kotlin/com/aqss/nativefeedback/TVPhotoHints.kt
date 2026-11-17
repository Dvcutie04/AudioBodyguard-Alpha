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

/** Session-only TV label details for the picture guide. */
data class TVModelIdentity private constructor(val model: String, val brand: String?, val make: String?, val year: String?) {
    val summary: String get() = "Model: $model\nBrand: ${brand ?: "Unknown"} · Make: ${make ?: "Unknown"}\nModel year: ${year ?: "Unknown"}"

    companion object {
        fun fromNumber(number: String, brand: String? = null, make: String? = null, year: String? = null): TVModelIdentity? {
            if (number.length > 128) return null
            val code = number.trim(' ', '\t')
            if (code.length !in 2..40 || !Regex("[A-Za-z0-9]+(?:[._/-][A-Za-z0-9]+)*").matches(code) ||
                code.none { it in '0'..'9' } || ('.' in code && code.none { it.isLetter() })) return null
            val model = code.uppercase(Locale.ROOT)
            val entry = SetupContent.modelCatalog[model]
            if (brand != null && entry != null && !entry.brand.equals(brand, ignoreCase = true)) return null
            return TVModelIdentity(model, entry?.brand ?: brand, make ?: entry?.make, year ?: entry?.year)
        }
    }
}

/** Untrusted presentation hints; there is intentionally no connection or authority API. */
class TVPhotoHints(text: String) {
    val brand: String?
    val model: String?
    val identity: TVModelIdentity?
    val address: String?
    val vizioCheckTarget: LocalTVTarget?
    init {
        val modelLabel = "(?:FULL[ \\t]+)?MODEL(?![ \\t]+YEAR\\b)(?:[ \\t]+(?:NAME|CODE|NUMBER|NO\\.?))?"
        val addressLabel = "(?:IPV4[ \\t]+IP[ \\t]+ADDRESS|IP(?:V4)?(?:[ \\t]+ADDRESS)?)"
        val upper = if (photoTextFits(text))
            text.uppercase(Locale.ROOT).replace(Regex("(?m)^[ \\t]*($modelLabel|$addressLabel|BRAND|MAKE|MANUFACTURER|MODEL[ \\t]+YEAR)[ \\t]*[:=]?[ \\t]*\\r?\\n[ \\t]*"), "$1: ") else ""
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
        val brands = matches("\\b(SAMSUNG|LG|SONY|TCL|HISENSE|VIZIO|PANASONIC|PHILIPS)\\b")
        brand = brands.singleOrNull()
        val modelRows = matches("^[ \\t]*($modelLabel)(?=[ \\t:=]|$)")
        val loneCodes = upper.lineSequence().map { it.trim() }.filter(SetupContent.modelCatalog::containsKey).toSet()
        val bare = upper.trim()
        val candidate = if (modelRows.isEmpty() && bare in SetupContent.modelCatalog) bare else labelled(modelLabel)
        model = candidate?.let { TVModelIdentity.fromNumber(it)?.model }
        fun name(label: String) = labelled(label)?.takeIf { Regex("[A-Z][A-Z0-9 &.,'()-]{0,55}").matches(it) }
        val namedBrand = name("BRAND")
        val year = labelled("MODEL[ \\t]+YEAR")?.takeIf { Regex("(19|20)[0-9]{2}").matches(it) }
        identity = if (model != null && brands.size <= 1 && loneCodes.all { it == model } &&
            (namedBrand == null || brand == null || namedBrand == brand))
            TVModelIdentity.fromNumber(model, namedBrand ?: brand, name("(?:MANUFACTURER|MAKE)"), year) else null
        address = labelled(addressLabel)?.takeIf(::isPrivateIPv4)
        vizioCheckTarget = if (brands.isEmpty() || brand == "VIZIO") address?.let { LocalTVTarget.parse(it) } else null
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
