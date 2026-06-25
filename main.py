from machine import Pin, I2C
import time

# I2C + PCA9685 SETUP
i2c = I2C(0, scl=Pin(7), sda=Pin(6), freq=400000)

PCA_ADDR  = 0x40
MODE1     = 0x00
PRESCALE  = 0xFE
LED0_ON_L = 0x06

def pca_write(reg, val):
    i2c.writeto_mem(PCA_ADDR, reg, bytes([val]))

def pca_init():
    pca_write(MODE1, 0x00)
    time.sleep_ms(10)
    pca_write(MODE1, 0x10)
    time.sleep_ms(10)
    pca_write(PRESCALE, 121)
    pca_write(MODE1, 0x00)
    time.sleep_ms(10)
    pca_write(MODE1, 0xA0)
    time.sleep_ms(10)

# SERVO CONTROL
MIN_PULSE = 150
MAX_PULSE = 600

def set_servo(channel, angle):
    angle = max(0, min(180, angle))
    pulse = int(MIN_PULSE + (angle / 180.0) * (MAX_PULSE - MIN_PULSE))
    reg = LED0_ON_L + (channel * 4)
    i2c.writeto_mem(PCA_ADDR, reg, bytes([
        0x00, 0x00,
        pulse & 0xFF,
        pulse >> 8
    ]))

def slow_move(channel, start_angle, end_angle, steps, delay_ms):
    for i in range(steps + 1):
        angle = start_angle + (end_angle - start_angle) * i / steps
        set_servo(channel, int(angle))
        time.sleep_ms(delay_ms)

# PARAMETERS — change via serial monitor
params = {
    "channel"      : 0,
    "home"         : 0,
    "square_angle" : 92,
    "sweep_steps"  : 30,
    "sweep_delay"  : 15,
    "hold_time"    : 800,
    "retract_steps": 20,
    "retract_delay": 10,
}

# SQUARING SEQUENCE
def square_box():
    ch = params["channel"]
    set_servo(ch, params["home"])
    time.sleep_ms(500)
    print("sweeping...")
    slow_move(ch, params["home"], params["square_angle"],
              params["sweep_steps"], params["sweep_delay"])
    print("holding " + str(params["hold_time"]) + "ms...")
    time.sleep_ms(params["hold_time"])
    print("retracting...")
    slow_move(ch, params["square_angle"], params["home"],
              params["retract_steps"], params["retract_delay"])
    print("Done squaring......")

# SERIAL COMMAND PARSER
def print_params():
    for k, v in params.items():
        print(f"  {k} = {v}")

def parse_command(cmd):
    parts = cmd.strip().split()
    if not parts:
        return

    command = parts[0].lower()

    if command == "run": # Run square cycle
        square_box()

    elif command == "set": # change param via set <param> <value>
        if len(parts) != 3:
            print("usage: set <param> <value>")
            return
        key = parts[1].lower()
        if key not in params:
            print(f"unknown parameter: {key}")
            print(f"valid: {list(params.keys())}")
            return
        try:
            val = int(parts[2])
            params[key] = val
            print(f"set {key} = {val}")
        except ValueError:
            print(f"value must be an integer")

    elif command == "get": # print all params
        print_params()

    elif command == "move": # move servo by angle
        if len(parts) != 2:
            print("usage: move <angle>")
            return
        try:
            angle = int(parts[1])
            set_servo(params["channel"], angle)
            print(f"moved channel {params['channel']} to {angle}°")
        except ValueError:
            print("angle must be an integer")

    elif command == "home": # move servo to home
        set_servo(params["channel"], params["home"])
        print(f"homed to {params['home']}°")

    elif command == "quit": # home servo
        set_servo(params["channel"], params["home"])
        print("homed and exiting")
        return "quit"

    else:
        print(f"unknown command: {command}")


# MAIN
print("initializing PCA9685...")
pca_init()
print("PCA9685 ready")
set_servo(params["channel"], params["home"])
time.sleep_ms(500)
print("servo homed")
print("")
print_params()

while True:
    try:
        cmd = input("> ")
        result = parse_command(cmd)
        if result == "quit":
            break
    except KeyboardInterrupt:
        print("interrupted")
        set_servo(params["channel"], params["home"])
        break
    except Exception as e:
        print(f"error: {e}")