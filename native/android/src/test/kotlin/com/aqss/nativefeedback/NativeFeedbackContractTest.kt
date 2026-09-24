package com.aqss.nativefeedback

import java.nio.file.Files
import java.nio.file.Path
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.decodeFromJsonElement
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFails
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class NativeFeedbackContractTest {
    private fun contractPath(): Path {
        val workingDirectory = Path.of(System.getProperty("user.dir"))
        val candidates = listOf(
            workingDirectory.resolve("../../contracts/tv_selection_native_feedback_v1.json").normalize(),
            workingDirectory.resolve("contracts/tv_selection_native_feedback_v1.json").normalize(),
        )
        return candidates.firstOrNull(Files::exists)
            ?: error("tv_selection_native_feedback_v1.json not found")
    }

    @Test
    fun sharedFixtureDecodesWithKotlinModels() {
        val text = String(Files.readAllBytes(contractPath()), Charsets.UTF_8)
        val root = Json.parseToJsonElement(text).jsonObject
        assertEquals(1, root.getValue("schema_version").jsonPrimitive.int)
        assertEquals("feedback_sync_only", root.getValue("capability").jsonPrimitive.content)
        val cases = root.getValue("cases").jsonArray
        assertTrue(cases.isNotEmpty())

        for (fixtureElement in cases) {
            val fixture = fixtureElement.jsonObject
            val request = fixture.getValue("request")
            val expected = fixture.getValue("expected")
            val expectedObject = expected.jsonObject
            val errorCode = (expectedObject["error"] as? JsonObject)
                ?.get("code")
                ?.jsonPrimitive
                ?.content

            if (errorCode == "INVALID_FEEDBACK") {
                assertFails {
                    Json.decodeFromJsonElement<NativeFeedbackSyncRequest>(request)
                }
            } else {
                val decodedRequest = Json.decodeFromJsonElement<NativeFeedbackSyncRequest>(request)
                assertTrue(decodedRequest.events.isNotEmpty())
                assertEquals(1, decodedRequest.events.first().schemaVersion)
            }

            val response = Json.decodeFromJsonElement<NativeFeedbackSyncResponse>(expected)
            assertEquals(1, response.schemaVersion)
            assertEquals(expectedObject.getValue("ok").jsonPrimitive.boolean, response.ok)
            assertFalse(response.applied?.any(String::isBlank) ?: false)
        }
    }
}
