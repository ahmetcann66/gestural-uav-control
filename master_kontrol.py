import collections
import collections.abc
collections.MutableMapping = collections.abc.MutableMapping

import cv2
import mediapipe as mp
from dronekit import connect, VehicleMode
import time
from pymavlink import mavutil

print("Connecting to Virtual Drone (SITL)...")
vehicle = connect('tcp:127.0.0.1:5762', wait_ready=True)
print("Connection Successful! Drone Mode: %s" % vehicle.mode.name)

def arm_and_takeoff(target_altitude):
    print("Arming motors...")
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True
    while not vehicle.armed:
        time.sleep(1)
    print("Taking off!")
    vehicle.simple_takeoff(target_altitude)
    while True:
        if vehicle.location.global_relative_frame.alt >= target_altitude * 0.95:
            break
        time.sleep(1)

def send_velocity_command(velocity_x, velocity_y, velocity_z):
    msg = vehicle.message_factory.set_position_target_local_ned_encode(
        0, 0, 0, mavutil.mavlink.MAV_FRAME_LOCAL_NED, 0b0000111111000111,
        0, 0, 0, velocity_x, velocity_y, velocity_z, 0, 0, 0, 0, 0)
    vehicle.send_mavlink(msg)

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.75)

cap = cv2.VideoCapture(0)

is_flying = False

actual_vx, actual_vy, actual_vz = 0.0, 0.0, 0.0
smooth_factor = 0.05

tipIds = [8, 12, 16, 20]
pipIds = [6, 10, 14, 18]

print("\n--- SYSTEM READY (HYBRID GESTURE CONTROL) ---")
print("Press 't' to takeoff when camera feed appears.")

while True:
    success, img = cap.read()
    if not success:
        break

    img = cv2.flip(img, 1)
    h, w, c = img.shape
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    center_x, center_y = w // 2, h // 2
    tolerance = 70

    cv2.rectangle(img, (center_x - tolerance, center_y - tolerance),
                  (center_x + tolerance, center_y + tolerance), (255, 0, 0), 2)

    active_command = "HOVER"
    target_vx, target_vy, target_vz = 0.0, 0.0, 0.0

    if results.multi_hand_landmarks:
        for handLms in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)
            
            wrist = handLms.landmark[0]
            cx = int(wrist.x * w)
            cy = int(wrist.y * h)
            cv2.circle(img, (cx, cy), 10, (0, 0, 255), cv2.FILLED)

            fingers = []
            for id in range(0, 4):
                if handLms.landmark[tipIds[id]].y < handLms.landmark[pipIds[id]].y:
                    fingers.append(1)
                else:
                    fingers.append(0)

            cmd_y = ""
            if fingers == [1, 0, 0, 0]:
                cmd_y = "1 FINGER -> FWD"
                target_vx = 1.5
                
            elif fingers == [1, 1, 0, 0]:
                cmd_y = "2 FINGERS -> BWD"
                target_vx = -1.5

            cmd_x = ""
            if cx > center_x + tolerance:
                cmd_x = "RIGHT"
                target_vy = 1.5   
            elif cx < center_x - tolerance:
                cmd_x = "LEFT"
                target_vy = -1.5  

            if cmd_y and cmd_x:
                active_command = f"{cmd_y} & {cmd_x}"
            elif cmd_y:
                active_command = cmd_y
            elif cmd_x:
                active_command = cmd_x

    else:
        active_command = "HOVER (Hand Lost)"

    actual_vx += (target_vx - actual_vx) * smooth_factor
    actual_vy += (target_vy - actual_vy) * smooth_factor
    actual_vz += (target_vz - actual_vz) * smooth_factor

    if is_flying:
        send_velocity_command(actual_vx, actual_vy, actual_vz)
        color = (0, 255, 0) if "HOVER" in active_command else (0, 165, 255)
        
        cv2.putText(img, f"VX (Pitch): {actual_vx:.2f} m/s", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(img, f"VY (Roll) : {actual_vy:.2f} m/s", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    else:
        active_command = "Press 't' to arm & takeoff"
        color = (0, 0, 255)

    cv2.putText(img, f"CMD: {active_command}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 3)
    cv2.imshow("Hybrid Gestural UAV Control", img)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('t') and not is_flying:
        arm_and_takeoff(2.0)
        is_flying = True
    elif key == ord('q'):
        break

print("\nSystem shut down. Triggering Failsafe / RTL.")
vehicle.close()
cap.release()
cv2.destroyAllWindows()