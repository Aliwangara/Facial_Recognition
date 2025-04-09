import cv2
import numpy as np
import face_recognition
from .models import FaceEncoding, Student
import logging

# Set up logging
logger = logging.getLogger(__name__)

def load_known_faces():
    """Load known faces from database with error handling"""
    known_face_encodings = []
    known_face_names = []
    
    try:
        students = FaceEncoding.objects.select_related('student__user').all()
        for student in students:
            try:
                encoding = np.array(student.encoding_data)
                known_face_encodings.append(encoding)
                known_face_names.append(student.student.user.get_full_name())
            except Exception as e:
                logger.error(f"Error processing student {student.id}: {str(e)}")
                
        logger.info(f"Loaded {len(known_face_encodings)} known faces")
        return known_face_encodings, known_face_names
        
    except Exception as e:
        logger.error(f"Error loading known faces: {str(e)}")
        return [], []

def recognize_faces():
    """Main face recognition function with proper resource handling"""
    # Load known faces
    known_face_encodings, known_face_names = load_known_faces()
    
    if not known_face_encodings:
        logger.warning("No known faces loaded - recognition will be limited")
    
    # Initialize camera with multiple backend attempts
    video_capture = None

    for index in range(3):  # Try multiple indexes
        for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
            try:
                video_capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                if video_capture.isOpened():
                    logger.info(f"Camera opened at index {index} with backend: {backend}")
                    break
            except Exception as e:
                logger.warning(f"Camera index {index} with backend {backend} failed: {str(e)}")
        if video_capture and video_capture.isOpened():
            break
    
    if video_capture is None or not video_capture.isOpened():
        logger.error("Failed to open any camera.")
        return # return if no camera is opened.

    try:
        while True:
            # Capture frame-by-frame
            ret, frame = video_capture.read()
            if not ret:
                logger.warning("Failed to capture frame")
                break

            # Resize frame to 1/4 size for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            # Find all face locations and encodings
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Scale back up face locations since we scaled down the frame
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                matches = face_recognition.compare_faces(
                    known_face_encodings, 
                    face_encoding,
                    tolerance=0.5
                )
                name = "Unknown"

                # Use the known face with the smallest distance
                face_distances = face_recognition.face_distance(
                    known_face_encodings, 
                    face_encoding
                )
                if len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]

                # Draw rectangle and label
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, name, (left, top - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            # Display the resulting image
            cv2.imshow('Face Recognition', frame)

            # Exit on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except Exception as e:
        logger.error(f"Error during face recognition: {str(e)}")
        
    finally:
        # Release resources
        if video_capture:
            video_capture.release()
        cv2.destroyAllWindows()
        logger.info("Face recognition stopped")