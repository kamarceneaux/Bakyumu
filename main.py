import network
import socket
import time
from machine import Pin, PWM

WIFI_SSID = 'GeauxSweep'
WIFI_PASS = '12345678'

MOTOR_LEFT_PIN = 21
MOTOR_RIGHT_PIN = 19

# motor PWM values in nanoseconds
MOTOR_STOP_NS = 1_500_000 #1500 in arduino
MOTOR_FWD_NS = 2_000_000 #2000 in arduino
MOTOR_REV_NS = 1_000_000 #1000 in arduino

leftServo = PWM(Pin(MOTOR_LEFT_PIN, mode=Pin.OUT), freq=50)
rightServo = PWM(Pin(MOTOR_RIGHT_PIN, mode=Pin.OUT), freq=50)

def stop_motors():
    leftServo.duty_ns(MOTOR_STOP_NS)
    rightServo.duty_ns(MOTOR_STOP_NS)

def move_forward():
    leftServo.duty_ns(MOTOR_FWD_NS)
    rightServo.duty_ns(MOTOR_REV_NS)

def move_backward():
    leftServo.duty_ns(MOTOR_REV_NS)
    rightServo.duty_ns(MOTOR_FWD_NS)

def turn_left():
    leftServo.duty_ns(MOTOR_REV_NS)
    rightServo.duty_ns(MOTOR_REV_NS)

def turn_right():
    leftServo.duty_ns(MOTOR_FWD_NS)
    rightServo.duty_ns(MOTOR_FWD_NS)



HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
  <title>ESP32 Robot Control</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
  <style>
    body {
      font-family: Arial, sans-serif;
      background-color: #2c3e50;
      color: white;
      text-align: center;
      padding-top: 50px;
    }
    h1 {
      font-weight: 300;
    }
    .grid-container {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      grid-template-rows: repeat(3, 1fr);
      max-width: 400px;
      margin: 50px auto;
      gap: 10px;
    }
    .btn {
      display: flex;
      justify-content: center;
      align-items: center;
      font-size: 2.5em;
      padding: 30px;
      border: none;
      border-radius: 15px;
      background-color: #3498db;
      color: white;
      cursor: pointer;
      user-select: none; /* Prevents text selection on hold */
      transition: background-color 0.1s ease;
    }
    .btn:active {
      background-color: #2980b9;
    }
    .btn-stop {
      grid-column: 2 / 3;
      grid-row: 2 / 3;
      background-color: #e74c3c;
    }
    .btn-stop:active {
      background-color: #c0392b;
    }
    .btn-fwd { grid-column: 2 / 3; grid-row: 1 / 2; }
    .btn-bwd { grid-column: 2 / 3; grid-row: 3 / 4; }
    .btn-left { grid-column: 1 / 2; grid-row: 2 / 3; }
    .btn-right { grid-column: 3 / 4; grid-row: 2 / 3; }
  </style>
</head>
<body>

  <h1>BIG SWEEEPERR</h1>

  <div class="grid-container">
    <button class="btn btn-fwd" onmousedown="sendCmd('fwd')" ontouchstart="sendCmd('fwd')">&#8679;</button>
    <button class="btn btn-left" onmousedown="sendCmd('left')" ontouchstart="sendCmd('left')" >&#8678;</button>
    <button class="btn btn-stop" onclick="sendCmd('stop')">STOP</button>
    <button class="btn btn-right" onmousedown="sendCmd('right')" ontouchstart="sendCmd('right')">&#8680;</button>
    <button class="btn btn-bwd" onmousedown="sendCmd('bwd')" ontouchstart="sendCmd('bwd')">&#8681;</button>
  </div>

  <script>
    // This function sends a command to the ESP32 server
    function sendCmd(dir) {
      console.log('Sending command: ' + dir);
      // Send the request to a new '/control' endpoint
      fetch('/control?dir=' + dir)
        .catch(error => console.error('Error:', error));
    }
  </script>

</body>
</html>
"""

ap = network.WLAN(network.AP_IF)
ap.config(essid=WIFI_SSID, password=WIFI_PASS)
ap.active(True)

while not ap.active():
    time.sleep(1)

print("Access Point Started! Connect to", WIFI_SSID)
print("IP Address:", ap.ifconfig()[0])

# Stop motors on startup
stop_motors()

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

print("Listening on port 80...")

while True:
    try:
        conn, addr = s.accept()

        # Receive and parse the request
        request = conn.recv(1024)
        request_str = str(request)

        # Check for a CONTROL command first
        cmd_start = request_str.find('GET /control?dir=')
        if cmd_start != -1:
            cmd_start += 17
            cmd_end = request_str.find(' ', cmd_start)
            cmd = request_str[cmd_start:cmd_end]

            print("Received command:", cmd) # Optional

            if cmd == 'fwd':
                print("Go forward")
                move_forward()
            elif cmd == 'bwd':
                print("Go backward")
                move_backward()
            elif cmd == 'left':
                print("Go left")
                turn_left()
            elif cmd == 'right':
                print("Go right")
                turn_right()
            elif cmd == 'stop':
                print("Go stop")
                stop_motors()

            conn.send('HTTP/1.1 200 OK\n')
            conn.send('Content-Type: text/plain\n')
            conn.send('Connection: close\n\n')
            conn.send('OK')

        elif request_str.find('GET / HTTP/1.1') != -1:
            print("Client requested main page, sending HTML...")
            conn.send('HTTP/1.1 200 OK\n')
            conn.send('Content-Type: text/html\n')
            conn.send('Connection: close\n\n')
            conn.sendall(HTML_CONTENT)

        else:
            conn.send('HTTP/1.1 404 Not Found\n')
            conn.send('Connection: close\n\n')

        conn.close()

    except OSError as e:
        conn.close()