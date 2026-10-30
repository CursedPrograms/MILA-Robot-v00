package com.synthwomb.mila

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotTest {
    private class Recorder : Http {
        val calls = ArrayList<String>()
        override fun get(path: String): String? { calls.add(path); return "{}" }
        override fun post(path: String, json: String): String? { calls.add("$path $json"); return "{}" }
    }

    @Test fun lettingGoStopsOnceAndOnlyOnce() {
        val http = Recorder()
        val driver = Driver(Robot(http))
        driver.tick(0f, 0f, 0f)
        assertTrue("nothing to stop yet", http.calls.isEmpty())
        driver.tick(1f, 0f, 0f)
        val driving = http.calls.size
        assertTrue(driving >= 1)
        driver.tick(0f, 0f, 0f)
        val stopped = http.calls.size
        assertEquals(driving + 1, stopped)
        driver.tick(0f, 0f, 0f)
        assertEquals(stopped, http.calls.size)
    }

    @Test fun callsAreWhatTheRobotTakes() {
        val http = Recorder()
        val r = Robot(http)
        r.connect("1234")
        r.drive(1f, 0f, 0f)
        r.stop()
        assertEquals(listOf("/unlock?pw=1234", "/motorlockOff?pw=1234", "/mode?v=wasd", "/cmd?v=FORWARD", "/cmd?v=STOP"), http.calls)
    }

    @Test fun tilesReadItsStatus() {
        val tiles = Robot(Recorder()).tiles(org.json.JSONObject("""{"dist":33,"left":"---","right":"80","temp":22.0,"hum":45.0,"speed":100,"guard":0}"""))
        assertTrue(tiles.toString(), tiles.contains("Front" to "33 cm"))
    }

    @Test fun nearbyRobotsGetARoughDistance() {
        val near = Tiles.near("""{"robots":[{"name":"WHIP","rssi":-50},{"name":"NORA","rssi":-75}]}""")
        assertEquals(listOf("WHIP" to "~1.0 m", "NORA" to "~10 m"), near)
        assertTrue(Tiles.near(null).isEmpty())
        assertTrue(Tiles.near("not json").isEmpty())
    }

    @Test fun everyButtonSendsSomething() {
        val http = Recorder()
        Robot(http).buttons.forEach { (_, act) -> act() }
        assertEquals(Robot(http).buttons.size, http.calls.size)
    }
}
