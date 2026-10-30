package com.synthwomb.mila

import org.json.JSONObject
import java.util.Locale

// What MILA takes: the same calls as RITA and her PC controller.
class Robot(private val http: Http) : RobotApi {
    private fun n(v: Float) = String.format(Locale.ROOT, "%.2f", v)

    private var last = "STOP"

    override fun connect(pin: String) {
        http.get("/unlock?pw=$pin")
        http.get("/motorlockOff?pw=$pin")
        http.get("/mode?v=wasd")
    }
    // Her tracks are one command at a time, and it holds until the next: only send a change
    override fun drive(forward: Float, side: Float, turn: Float) {
        val cmd = when {
            forward > 0.3f && forward >= kotlin.math.abs(turn) -> "FORWARD"
            forward < -0.3f && -forward >= kotlin.math.abs(turn) -> "BACKWARD"
            turn > 0.3f -> "LEFT"
            turn < -0.3f -> "RIGHT"
            else -> "STOP"
        }
        if (cmd != last) {
            last = cmd
            http.get("/cmd?v=$cmd")
        }
    }
    override fun stop() {
        last = "STOP"
        http.get("/cmd?v=STOP")
    }
    override fun tiles(s: JSONObject) = listOf(
        "Front" to Tiles.cm(s.opt("dist")),
        "Left" to Tiles.cm(s.opt("left")),
        "Right" to Tiles.cm(s.opt("right")),
        "Temp" to "${s.optString("temp", "--")}\u00b0C",
        "Humidity" to "${s.optString("hum", "--")}%",
        "Speed" to "${s.optString("speed", "--")}%",
        "Guard" to if (s.optInt("guard") != 0) "WALL" else "clear",
    )

    override val buttons = listOf(
        "WASD" to { http.get("/mode?v=wasd"); Unit },
        "OBSTACLE" to { http.get("/mode?v=obstacle"); Unit },
        "FOLLOW" to { http.get("/mode?v=follow"); Unit },
        "HELLO" to { http.get("/cmd?v=HELLO"); Unit },
        "DANCE" to { http.get("/cmd?v=DANCE"); Unit },
        "SPEED" to { http.get("/cmd?v=SPEEDCYCLE"); Unit },
        "LOCK" to { http.get("/motorlockOn"); Unit },
    )
}
