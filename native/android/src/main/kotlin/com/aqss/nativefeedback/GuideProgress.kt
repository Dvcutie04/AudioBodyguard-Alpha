package com.aqss.nativefeedback

/** Local learning state only; no device, account, permission or adapter API. */
class GuideProgress {
    var topicId: String? = null; private set
    var index = 0; private set
    private val selections = mutableMapOf<String, String>()
    val topic get() = TutorialContent.topics.firstOrNull { it.id == topicId }
    val step get() = topic?.steps?.getOrNull(index)
    val choices get() = TutorialContent.choices[step?.target].orEmpty()
    val canContinue get() = step != null && (choices.isEmpty() || choices.any { it.id == selections[step?.target] })
    val isLast get() = topic?.let { index == it.steps.lastIndex } ?: false
    fun selected(target: String) = TutorialContent.choices[target]?.firstOrNull { it.id == selections[target] }
    fun start(id: String): Boolean {
        if (TutorialContent.topics.none { it.id == id }) return false
        topicId = id; index = 0; selections.clear(); return true
    }
    fun select(id: String): Boolean {
        val current = step ?: return false
        if (choices.none { it.id == id }) return false
        selections[current.target] = id; return true
    }
    fun next(): Boolean {
        if (!canContinue || isLast) return false
        index++; return true
    }
    /** Finishing pictures advances learning only, never a verified connection. */
    fun completePictures(expectedTarget: String, routeId: String): Boolean {
        if (topicId != "getting_started" || step?.target != expectedTarget ||
            expectedTarget !in listOf("connectionPlan", "connectionCheck") ||
            routeId !in TutorialContent.pictureContinueRoutes) return false
        return next()
    }
    fun back() { if (index > 0) index-- }
    fun close() { topicId = null; index = 0; selections.clear() }
    fun snapshot(): Map<String, String> = selections.toMap()
    /** Untrusted restoration cannot skip an unanswered earlier question. */
    fun restore(id: String, requested: Int, saved: Map<String, String>) {
        if (!start(id)) return
        saved.forEach { (target, value) -> if (TutorialContent.choices[target]?.any { it.id == value } == true) selections[target] = value }
        val destination = requested.coerceIn(0, topic!!.steps.lastIndex)
        while (index < destination && next()) { /* one guarded step at a time */ }
    }
}
