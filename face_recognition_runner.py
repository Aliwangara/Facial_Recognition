# face_recognition_runner.py

import os
import django
import cv2
import numpy as np
import face_recognition
from datetime import datetime
from django.utils.timezone import now

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'facialR_project.settings')  # ⛳️ Replace 'yourproject'
django.setup()

from users.models import FaceEncoding, LiveAttendance, Subject

def recognize_faces():
    known_encodings = []
    known_students = []

    for face in FaceEncoding.objects.select_related('student__user').all():
        known_encodings.append(np.array(face.encoding_data))
        known_students.append(face.student)

    video_capture = cv2.VideoCapture(0)

    if not video_capture.isOpened():
        print("Could not open webcam.")
        return

    print("[INFO] Starting face recognition...")

    try:
        while True:
            ret, frame = video_capture.read()
            if not ret:
                print("Failed to grab frame")
                break

            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            for face_encoding, location in zip(face_encodings, face_locations):
                matches = face_recognition.compare_faces(known_encodings, face_encoding)
                name = "Unknown"

                face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        student = known_students[best_match_index]
                        name = student.user.get_full_name()

                        # Avoid duplicate attendance logging
                        today = now().date()
                        subject = Subject.objects.get(name="Math")  # 🔁 Customize dynamically if needed

                        already_logged = LiveAttendance.objects.filter(
                            student=student,
                            subject=subject,
                            timestamp__date=today
                        ).exists()

                        if not already_logged:
                            LiveAttendance.objects.create(
                                student=student,
                                subject=subject,
                                status='verified'
                            )
                            print(f"[MARKED] {name} - {today}")

                # Draw result
                top, right, bottom, left = [v * 4 for v in location]
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            cv2.imshow('Live Attendance System', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        video_capture.release()
        cv2.destroyAllWindows()
        print("[INFO] Camera stopped.")

if __name__ == '__main__':
    recognize_faces()
