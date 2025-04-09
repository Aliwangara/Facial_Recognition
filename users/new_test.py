import cv2

cap = cv2.VideoCapture(0)  # Try changing 0 to 1 or 2 if needed

if not cap.isOpened():
    print("Failed to open camera!")
else:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame!")
            break

        cv2.imshow("Test Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to exit
            break

cap.release()
cv2.destroyAllWindows()
