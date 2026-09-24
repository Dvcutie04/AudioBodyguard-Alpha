// Synthetic conformance only. This test cannot certify a native output boundary.
package com.aqss.nativefeedback

import java.nio.file.Files
import java.nio.file.Path
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class EndpointNativeBoundaryFixtureTest {
    private fun fixturePath(): Path {
        val workingDirectory = Path.of(System.getProperty("user.dir"))
        val candidates = listOf(
            workingDirectory.resolve("../../contracts/endpoint_native_boundary_v1.json").normalize(),
            workingDirectory.resolve("contracts/endpoint_native_boundary_v1.json").normalize(),
        )
        return candidates.firstOrNull(Files::exists)
            ?: error("endpoint_native_boundary_v1.json not found")
    }

    private fun syntheticEligible(trace: JsonObject): Boolean = runCatching {
        val claim = trace.getValue("claim").jsonObject
        if (trace.getValue("activation").jsonObject != claim || trace.getValue("submission").jsonObject != claim) {
            return@runCatching false
        }
        val native = trace.getValue("native").jsonObject
        val protection = trace.getValue("protection").jsonObject
        if (!protection.getValue("activation").jsonPrimitive.boolean || !protection.getValue("submission").jsonPrimitive.boolean) {
            return@runCatching false
        }
        val flags = listOf("backend_qualified", "registry_complete", "evidence_authorized", "history_authenticated", "route_enforced", "cut_closed", "admission_closed", "publication_closed")
        if (flags.any { !native.getValue(it).jsonPrimitive.boolean }) {
            return@runCatching false
        }
        val times = trace.getValue("times").jsonObject
        val issuedAt = times.getValue("issued_at").jsonPrimitive.int
        val expiresAt = times.getValue("expires_at").jsonPrimitive.int
        val activationAt = times.getValue("activation_at").jsonPrimitive.int
        val submissionAt = times.getValue("submission_at").jsonPrimitive.int
        if (issuedAt > activationAt || activationAt > submissionAt || submissionAt >= expiresAt) {
            return@runCatching false
        }
        if (native.getValue("output_disposition").jsonPrimitive.content !in setOf("completed", "discarded")) {
            return@runCatching false
        }
        val retained = native.getValue("retained_generations").jsonArray.map { it.jsonPrimitive.int }.toSet()
        val closed = native.getValue("closed_generations").jsonArray.map { it.jsonPrimitive.int }.toSet()
        if (!closed.containsAll(retained)) {
            return@runCatching false
        }
        val retiredThrough = native.getValue("retired_through_generation").jsonPrimitive.int
        if (native.getValue("work").jsonArray.any { item ->
                val work = item.jsonObject
                work.getValue("generation").jsonPrimitive.int <= retiredThrough && !work.getValue("settled").jsonPrimitive.boolean
            }) {
            return@runCatching false
        }
        native.getValue("actual_route_id") == claim.getValue("route_id") && native.getValue("actual_route_epoch") == claim.getValue("route_epoch")
    }.getOrDefault(false)

    @Test
    fun sharedSyntheticBoundaryVectors() {
        val document = Json.parseToJsonElement(String(Files.readAllBytes(fixturePath()), Charsets.UTF_8)).jsonObject
        assertEquals(1, document.getValue("schema_version").jsonPrimitive.int)
        assertEquals("AQSS/owned-pcm-gain-lab/v1", document.getValue("profile_id").jsonPrimitive.content)
        assertEquals("test_only_trace_conformance", document.getValue("capability").jsonPrimitive.content)
        val baseline = document.getValue("baseline").jsonObject
        val cases = document.getValue("cases").jsonArray
        assertEquals(18, cases.size)
        val identifiers = mutableSetOf<String>()
        for (fixtureCase in cases) {
            val item = fixtureCase.jsonObject
            val identifier = item.getValue("id").jsonPrimitive.content
            assertTrue(identifiers.add(identifier), identifier)
            val expected = item.getValue("eligible").jsonPrimitive.boolean
            val trace = baseline.toMutableMap()
            for ((section, patch) in item.getValue("changes").jsonObject) {
                trace[section] = JsonObject(trace.getValue(section).jsonObject + patch.jsonObject)
            }
            assertEquals(expected, syntheticEligible(JsonObject(trace)), identifier)
        }
    }
}
