package com.aqss.nativefeedback

import java.nio.file.Files
import java.nio.file.Path
import java.nio.charset.StandardCharsets
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class SessionEvidenceViewTest {
    @Test
    fun callersCannotTurnAReadOnlyProjectionIntoActuationPermission() {
        val view = CapabilityView("AVAILABLE_FOR_REVIEW", emptyList())
        assertFalse(view.canActuate)
        assertFailsWith<IllegalArgumentException> {
            CapabilityView("AVAILABLE_FOR_REVIEW", emptyList(), canActuate = true)
        }
        assertFailsWith<IllegalArgumentException> { view.copy(canActuate = true) }
        assertFalse(view.copy(label = "UNKNOWN").canActuate)
    }

    private fun fixture(): JsonObject {
        val cwd = Path.of(System.getProperty("user.dir"))
        val candidates = listOf(
            cwd.resolve("../../contracts/session_evidence_view_v1.json").normalize(),
            cwd.resolve("contracts/session_evidence_view_v1.json").normalize(),
        )
        val path = candidates.firstOrNull(Files::isRegularFile)
            ?: error("session_evidence_view_v1.json not found")
        return Json.parseToJsonElement(String(Files.readAllBytes(path), StandardCharsets.UTF_8)).jsonObject
    }

    private fun optionalBool(fields: JsonObject, name: String): Boolean? {
        val element = fields.getValue(name)
        return if (element == JsonNull) null else element.jsonPrimitive.boolean
    }

    @Test
    fun sharedCoverageVectorsStayFailClosed() {
        val document = fixture()
        assertEquals(1, document.getValue("schema_version").jsonPrimitive.int)
        assertEquals("read_only_reference_projection_not_physical_qualification",
                     document.getValue("purpose").jsonPrimitive.content)
        val cases = document.getValue("coverage_cases").jsonArray
        assertTrue(cases.size >= 10)
        for (item in cases) {
            val entry = item.jsonObject
            val sampleElement = entry.getValue("sample")
            val sample = if (sampleElement == JsonNull) null else {
                val fields = sampleElement.jsonObject
                CoverageSample(
                    runtimeId = fields.getValue("runtime").jsonPrimitive.content,
                    clockDomainId = fields.getValue("clock").jsonPrimitive.content,
                    receivedMonotonic = fields.getValue("received").jsonPrimitive.double,
                    expiresMonotonic = fields.getValue("expires").jsonPrimitive.double,
                    state = SessionState.valueOf(fields.getValue("state").jsonPrimitive.content),
                    reason = fields.getValue("reason").jsonPrimitive.content,
                    userPaused = fields.getValue("user_paused").jsonPrimitive.boolean,
                )
            }
            val view = SessionEvidenceView.coverage(
                sample,
                runtimeId = entry.getValue("current_runtime").jsonPrimitive.content,
                clockDomainId = entry.getValue("current_clock").jsonPrimitive.content,
                nowMonotonic = entry.getValue("now").jsonPrimitive.double,
            )
            assertEquals(entry.getValue("expected_state").jsonPrimitive.content,
                         view.state.name, entry.getValue("id").jsonPrimitive.content)
            assertEquals(entry.getValue("expected_reason").jsonPrimitive.content,
                         view.reason, entry.getValue("id").jsonPrimitive.content)
        }
    }

    @Test
    fun sharedCapabilityVectorsCannotAuthorizeExecution() {
        val cases = fixture().getValue("capability_cases").jsonArray
        assertTrue(cases.size >= 9)
        for (item in cases) {
            val entry = item.jsonObject
            val fields = entry.getValue("facts").jsonObject
            val facts = CapabilityFacts(
                hardware = optionalBool(fields, "hardware"),
                qualification = optionalBool(fields, "qualification"),
                permission = optionalBool(fields, "permission"),
                route = optionalBool(fields, "route"),
                runtime = optionalBool(fields, "runtime"),
                evidence = optionalBool(fields, "evidence"),
                observedMonotonic = fields.getValue("observed").jsonPrimitive.double,
                expiresMonotonic = fields.getValue("expires").jsonPrimitive.double,
                clockDomainId = fields.getValue("clock").jsonPrimitive.content,
            )
            val view = SessionEvidenceView.capability(
                facts,
                clockDomainId = entry.getValue("current_clock").jsonPrimitive.content,
                nowMonotonic = entry.getValue("now").jsonPrimitive.double,
            )
            assertEquals(entry.getValue("expected").jsonPrimitive.content,
                         view.label, entry.getValue("id").jsonPrimitive.content)
            assertFalse(view.canActuate)
        }
    }

    @Test
    fun malformedLocalEvidenceNeverShowsActive() {
        val sample = CoverageSample("runtime", "clock", Double.NaN, 3.0,
                                    SessionState.ACTIVE, "VALIDATED")
        assertEquals(SessionState.UNKNOWN_PHYSICAL_STATE,
                     SessionEvidenceView.coverage(sample, "runtime", "clock", 2.0).state)
    }
}
