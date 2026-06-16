import time
from secrets import secrets
from hiibot_bluefi.wifi import WIFI
from adafruit_esp32spi import adafruit_esp32spi_socketpool as socketpool
import adafruit_minimqtt.adafruit_minimqtt as MQTT

BROKER = "broker.emqx.io"
PORT = 1883

TOPIC_B_TO_A = "bluefi/qzy/secure/b_to_a"
TOPIC_A_TO_B = "bluefi/qzy/secure/a_to_b"

SECRET_KEY = "BlueFi_QZY_2026"
HEX = "0123456789ABCDEF"

print("===== BlueFi B Encrypted MQTT Sender =====")


def crc8_text(text):
    crc = 0
    for ch in text:
        crc = crc ^ ord(ch)
        for i in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def byte_to_hex(value):
    return HEX[(value >> 4) & 0x0F] + HEX[value & 0x0F]


def bytes_to_hex(data):
    result = ""
    for b in data:
        result = result + byte_to_hex(b)
    return result


def hex_value(ch):
    ch = ch.upper()
    for i in range(16):
        if HEX[i] == ch:
            return i
    return 0


def hex_to_bytes(text):
    result = bytearray()
    for i in range(0, len(text), 2):
        high = hex_value(text[i])
        low = hex_value(text[i + 1])
        result.append(high * 16 + low)
    return bytes(result)


def xor_crypt(data):
    key = SECRET_KEY.encode("utf-8")
    result = bytearray()

    for i in range(len(data)):
        result.append(data[i] ^ key[i % len(key)])

    return bytes(result)


def make_check(seq, cmd, length, data_text):
    text = str(seq) + "|" + cmd + "|" + str(length) + "|" + data_text + "|" + SECRET_KEY
    return byte_to_hex(crc8_text(text))


def build_frame(seq, cmd, data_text):
    plain = data_text.encode("utf-8")
    encrypted = xor_crypt(plain)
    encrypted_hex = bytes_to_hex(encrypted)
    length = len(plain)
    check = make_check(seq, cmd, length, data_text)

    frame = "BF1|SEQ=" + str(seq)
    frame = frame + "|CMD=" + cmd
    frame = frame + "|LEN=" + str(length)
    frame = frame + "|DATA=" + encrypted_hex
    frame = frame + "|CHK=" + check

    return frame


def parse_frame(frame):
    frame = frame.strip()
    parts = frame.split("|")

    if len(parts) < 6:
        raise ValueError("frame too short")

    if parts[0] != "BF1":
        raise ValueError("bad frame header")

    info = {}

    for part in parts[1:]:
        pair = part.split("=", 1)
        if len(pair) == 2:
            info[pair[0]] = pair[1]

    seq = int(info["SEQ"])
    cmd = info["CMD"]
    length = int(info["LEN"])
    encrypted_hex = info["DATA"]
    received_check = info["CHK"]

    encrypted = hex_to_bytes(encrypted_hex)
    plain = xor_crypt(encrypted)
    data_text = plain.decode("utf-8")

    real_length = len(plain)

    if real_length != length:
        raise ValueError("length error")

    calculated_check = make_check(seq, cmd, length, data_text)

    if calculated_check != received_check:
        raise ValueError("check error")

    return seq, cmd, data_text


wifi = WIFI()

print("ESP32 status:", wifi.esp.status)

if wifi.esp.status == 0xFF:
    print("ESP32 not found")
    while True:
        time.sleep(1)

ssid = secrets["ssid"]
password = secrets["password"]

print("Connecting to", ssid)

while not wifi.esp.is_connected:
    try:
        wifi.esp.connect_AP(ssid, password)
    except OSError as e:
        print("Could not connect, retrying:", e)
        time.sleep(2)

print("WiFi connected!")
print("B board IP:", wifi.esp.ipv4_address)

pool = socketpool.SocketPool(wifi.esp)


def connected(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    print("Subscribing:", TOPIC_A_TO_B)
    client.subscribe(TOPIC_A_TO_B)


def disconnected(client, userdata, rc):
    print("Disconnected from MQTT broker")


def message(client, topic, msg):
    print("Raw topic:", topic)
    print("Raw frame:", msg)

    try:
        seq, cmd, data_text = parse_frame(str(msg))

        print("Frame check OK")
        print("SEQ:", seq)
        print("CMD:", cmd)
        print("DATA:", data_text)

        if cmd == "ACK":
            print("Received valid ACK from A")
        else:
            print("Received non-ACK message")

    except Exception as e:
        print("Frame parse error:", e)


mqtt_client = MQTT.MQTT(
    broker=BROKER,
    port=PORT,
    socket_pool=pool,
    is_ssl=False,
)

mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message

print("Connecting to MQTT broker:", BROKER)
mqtt_client.connect()

last_send_time = 0
seq = 1

while True:
    try:
        mqtt_client.loop(timeout=1)

        now = time.monotonic()

        if now - last_send_time >= 3:
            last_send_time = now

            frame = build_frame(seq, "HELLO", "hello")

            print("Publishing encrypted HELLO")
            print("HELLO frame:", frame)

            mqtt_client.publish(TOPIC_B_TO_A, frame)

            seq = seq + 1

            if seq > 9999:
                seq = 1

    except Exception as e:
        print("MQTT error:", e)
        time.sleep(2)

        try:
            mqtt_client.reconnect()
        except Exception as e2:
            print("Reconnect failed:", e2)
            time.sleep(3)
