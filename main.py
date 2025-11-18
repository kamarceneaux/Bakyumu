import uasyncio as asyncio
from machine import Pin, PWM
import network

AP_SSID = "GeauxSweep"
AP_PASSWORD = "12345678"

# PWM pins
LEFT_MOTOR_PIN = 21
RIGHT_MOTOR_PIN = 19
SERVO_PIN = 23

PWM_FREQ = 50

PULSE_FULL_REV = 1.0
PULSE_STOP = 1.5
PULSE_FULL_FWD = 2.0

SPRAY_FORWARD_MS = 2.0
SPRAY_REVERSE_MS = 1.0
SPRAY_FORWARD_TIME = 1500   # ms
SPRAY_REVERSE_TIME = 1200   # ms

def pulse_ms_to_duty(p_ms):
    period_ms = 1000.0 / PWM_FREQ
    duty_frac = p_ms / period_ms
    return int(duty_frac * 65535)

D_FULL_REV = pulse_ms_to_duty(PULSE_FULL_REV)
D_STOP = pulse_ms_to_duty(PULSE_STOP)
D_FULL_FWD = pulse_ms_to_duty(PULSE_FULL_FWD)
D_SPRAY_FWD = pulse_ms_to_duty(SPRAY_FORWARD_MS)
D_SPRAY_REV = pulse_ms_to_duty(SPRAY_REVERSE_MS)


pwm_left = PWM(Pin(LEFT_MOTOR_PIN), freq=PWM_FREQ)
pwm_right = PWM(Pin(RIGHT_MOTOR_PIN), freq=PWM_FREQ)
servo_pwm = PWM(Pin(SERVO_PIN), freq=PWM_FREQ)

current_command = {"cmd": "stop"}
cmd_lock = asyncio.Lock()

def parse_query(path):
    cmd = "stop"
    if "?" in path:
        try:
            query = path.split("?", 1)[1]
            for kv in query.split("&"):
                k, v = kv.split("=")
                if k == "c":
                    cmd = v
        except:
            pass
    return cmd


# --------------------
# WiFi Access Point
# --------------------
def setup_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, password=AP_PASSWORD)
    print("AP running at:", ap.ifconfig())

async def set_motors(cmd):
    if cmd == "forward":
        pwm_left.duty_u16(D_FULL_FWD)
        pwm_right.duty_u16(D_FULL_FWD)
    elif cmd == "back":
        pwm_left.duty_u16(D_FULL_REV)
        pwm_right.duty_u16(D_FULL_REV)
    elif cmd == "turn_left":
        pwm_left.duty_u16(D_FULL_REV)
        pwm_right.duty_u16(D_FULL_FWD)
    elif cmd == "turn_right":
        pwm_left.duty_u16(D_FULL_FWD)
        pwm_right.duty_u16(D_FULL_REV)
    elif cmd == "stop":
        pwm_left.duty_u16(D_STOP)
        pwm_right.duty_u16(D_STOP)

async def do_spray():
    print("Spray triggered")
    await set_motors("stop")
    servo_pwm.duty_u16(D_SPRAY_FWD)
    await asyncio.sleep_ms(SPRAY_FORWARD_TIME)
    servo_pwm.duty_u16(D_SPRAY_REV)
    await asyncio.sleep_ms(SPRAY_REVERSE_TIME)
    servo_pwm.duty_u16(D_STOP)
    async with cmd_lock:
        current_command["cmd"] = "stop"

async def motor_loop():
    last_cmd = None
    while True:
        async with cmd_lock:
            cmd = current_command["cmd"]

        if cmd != last_cmd:
            if cmd == "spray":
                asyncio.create_task(do_spray())
            else:
                await set_motors(cmd)
            last_cmd = cmd

        await asyncio.sleep_ms(10)

# --------------------
# HTML Web UI
# --------------------
INDEX_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>VacuumBot Remote</title>
<style>
body { font-family:sans-serif; display:flex; flex-direction:column; align-items:center; padding:20px; }
.row { display:flex; gap:10px; margin:8px; }
button { padding:12px 20px; font-size:18px; }
#status { margin-top:15px; font-size:18px; }
</style>
</head>
<body>
<h2>VacuumBot Remote</h2>
<div class="row">
<button onclick="sendCmd('forward')">Forward</button>
<button onclick="sendCmd('back')">Backward</button>
</div>
<div class="row">
<button onclick="sendCmd('turn_left')">Turn Left</button>
<button onclick="sendCmd('turn_right')">Turn Right</button>
</div>
<div class="row">
<button onclick="sendCmd('stop')">Stop</button>
<button onclick="sendCmd('spray')">Spray</button>
</div>
<div id="status">Status: idle</div>
<script>
function sendCmd(cmd){
  fetch(`/cmd?c=${cmd}`).then(()=>{document.getElementById('status').innerText="Status: "+cmd});
}
</script>
</body>
</html>
"""

# --------------------
# HTTP Server
# --------------------
async def handle_client(reader, writer):
    try:
        req_line = await reader.readline()
        if not req_line:
            await writer.aclose()
            return

        method, path, _ = req_line.decode().split(" ")
        while True:
            h = await reader.readline()
            if h in (b"\r\n", b""):
                break

        # Serve main page
        if path == "/" and method == "GET":
            response = "HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n" + INDEX_HTML
            await writer.awrite(response)

        # Handle lightweight command
        elif path.startswith("/cmd"):
            cmd = parse_query(path)
            async with cmd_lock:
                current_command["cmd"] = cmd
            await writer.awrite("HTTP/1.0 200 OK\r\n\r\nOK")

        else:
            await writer.awrite("HTTP/1.0 404 NOT FOUND\r\n\r\n")

        await writer.aclose()
    except Exception as e:
        print("Client error:", e)

# Main code for the functions
async def main():
    setup_ap()
    print("Starting motor loop")
    asyncio.create_task(motor_loop())
    server = await asyncio.start_server(handle_client, "0.0.0.0", 80)
    print("Server running on port 80")
    await server.wait_closed()

asyncio.run(main())
