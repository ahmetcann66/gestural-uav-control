import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

cap = cv2.VideoCapture(0)

prev_x, prev_y = None, None
aktif_komut = "HOVER (Stationary)"
komut_sayaci = 0

print("High-precision motor active... Press 'q' to exit.")

while True:
    success, img = cap.read()
    if not success:
        break
import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

cap = cv2.VideoCapture(0)

prev_x, prev_y = None, None
active_command = "HOVER (Stay Still)"
command_counter = 0

print("High-precision motor active... Press 'q' to exit.")

while True:
    success, img = cap.read()
    if not success:
        break

    img = cv2.flip(img, 1)
    h, w, c = img.shape

    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    current_command = "HOVER (Stay Still)"

    if results.multi_hand_landmarks:
        for handLms in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, handLms, mp_hands.HAND_CONNECTIONS)

            wrist = handLms.landmark[0]
            cx, cy = int(wrist.x * w), int(wrist.y * h)

            if prev_x is None or prev_y is None:
                prev_x, prev_y = cx, cy

            diff_x = cx - prev_x
            diff_y = cy - prev_y

            sensitivity = 10

            if abs(diff_x) > abs(diff_y):
                if diff_x > sensitivity:
                    current_command = "-> TURN RIGHT"
                elif diff_x < -sensitivity:
                    current_command = "<- TURN LEFT"
            else:
                if diff_y < -sensitivity:
                    current_command = "^ UP"
                elif diff_y > sensitivity:
                    current_command = "v DOWN"

            if current_command != "HOVER (Stay Still)":
                active_command = current_command
                command_counter = 5
                prev_x, prev_y = cx, cy
            else:
                if command_counter > 0:
                    command_counter -= 1
                else:
                    active_command = "HOVER (Stay Still)"
                    prev_x, prev_y = cx, cy

    else:
        active_command = "HOVER (Frame Lost!)"
        command_counter = 0
        prev_x, prev_y = None, None

    color = (0, 255, 0) if "HOVER" in active_command else (0, 165, 255)

    cv2.putText(img, f"Active Command: {active_command}", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

    cv2.imshow("Drone Hand Control - Precision Motor", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
