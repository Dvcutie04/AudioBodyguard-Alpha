package com.aqss.nativefeedback

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class GuideProgressTest {
    @Test fun choicesGateEachStepAndReplayResetsSelections() {
        val guide = GuideProgress()
        assertFalse(guide.next()); assertFalse(guide.start("unknown"))
        assertTrue(guide.start("getting_started")); guide.back(); assertEquals(0, guide.index)
        assertTrue(guide.next()); assertEquals("chooseTV", guide.step?.target)
        assertFalse(guide.next()); assertFalse(guide.select("alexa")); assertFalse(guide.select("invented"))
        assertTrue(guide.select("samsung")); assertTrue(guide.next())
        assertEquals("chooseHome", guide.step?.target); assertFalse(guide.next())
        assertTrue(guide.select("alexa")); assertTrue(guide.next()); assertEquals("connectionPlan", guide.step?.target)
        assertEquals("Samsung", guide.selected("chooseTV")?.title)
        guide.back(); assertEquals("alexa", guide.selected("chooseHome")?.id)
        assertTrue(guide.select("neither")); assertTrue(guide.next())
        while (guide.next()) { }
        assertTrue(guide.isLast); assertEquals(6, guide.index); assertFalse(guide.next())
        guide.close(); assertNull(guide.topic); assertTrue(guide.snapshot().isEmpty())
        guide.start("getting_started"); assertEquals(0, guide.index); assertNull(guide.selected("chooseTV"))
    }
    @Test fun restoreCannotBypassUnansweredOrInvalidChoices() {
        val guide = GuideProgress()
        guide.restore("getting_started", 100, emptyMap()); assertEquals(1, guide.index)
        guide.restore("getting_started", 6, mapOf("chooseTV" to "invalid", "chooseHome" to "alexa")); assertEquals(1, guide.index)
        guide.restore("getting_started", 6, mapOf("chooseTV" to "unsure")); assertEquals(2, guide.index)
        guide.restore("getting_started", 6, mapOf("chooseTV" to "unsure", "chooseHome" to "neither")); assertEquals(6, guide.index)
        guide.restore("getting_started", -9, emptyMap()); assertEquals(0, guide.index)
    }
    @Test fun everyTopicHasAReachableEnd() {
        TutorialContent.topics.forEach { topic ->
            val guide = GuideProgress(); guide.start(topic.id)
            repeat(topic.steps.size) {
                guide.choices.lastOrNull()?.let { assertTrue(guide.select(it.id)) }
                guide.next()
            }
            assertTrue(guide.isLast, topic.id)
        }
    }
}
