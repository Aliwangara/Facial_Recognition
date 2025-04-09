from django.views import View
from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views.decorators import gzip
from django.utils.decorators import method_decorator
from django.core.exceptions import ObjectDoesNotExist
from django.apps import apps
from django.db import transaction
from django.utils import timezone
from datetime import date
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from users.forms import StudentRegistrationForm, FaceUploadForm,FaceUploadSelectForm
from .models import Student, Attendance, FaceEncoding, LiveAttendance, Subject

import cv2
import base64
import io
from io import BytesIO
import json
import face_recognition
import numpy as np
import threading
import time
from datetime import datetime
import logging
import atexit
from queue import Queue, Empty
from PIL import Image
import csv



logger = logging.getLogger(__name__)


# Home and Dashboard Views
def home(request):
    return render(request, 'mainscreen/index.html')


@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()

    if user.is_superuser:
        total_students = Student.objects.count()
        total_subjects = Subject.objects.count()
        present_today = Attendance.objects.filter(timestamp__date=today).count()
        absent_today = total_students - present_today
        attendance_rate = round((present_today / total_students) * 100, 2) if total_students > 0 else 0

        context = {
            'role': 'Admin',
            'total_students': total_students,
            'total_subjects': total_subjects,
            'present_today': present_today,
            'absent_today': absent_today,
            'attendance_rate': attendance_rate,
        }
        return render(request, 'dashboard/d_index.html', context)

    elif user.is_teacher:
        subjects = Subject.objects.filter(teacher=user)
        subject_ids = subjects.values_list('id', flat=True)

        students = Student.objects.filter(subjects__in=subject_ids).distinct()
        total_students = students.count()
        present_today = Attendance.objects.filter(
            timestamp__date=today,
            student__in=students
        ).count()
        absent_today = total_students - present_today
        attendance_rate = round((present_today / total_students) * 100, 2) if total_students > 0 else 0

        context = {
            'role': 'Teacher',
            'subjects': subjects,
            'total_students': total_students,
            'present_today': present_today,
            'absent_today': absent_today,
            'attendance_rate': attendance_rate,
        }
        return render(request, 'dashboard/d_index.html', context)

    elif hasattr(user, 'student'):
        student = user.student
        attendance_today = Attendance.objects.filter(
            student=student,
            timestamp__date=today
        ).exists()

        context = {
            'role': 'Student',
            'attendance_today': attendance_today
        }
        return render(request, 'dashboard/d_index.html', context)

    return render(request, 'dashboard/d_index.html', {'error': 'Role not recognized'})


@csrf_exempt
def upload_face(request):
    if request.method == 'POST':
        try:
            # Parse JSON body
            import json
            data = json.loads(request.body)
            student_id = data.get('student_id')
            image_data = data.get('image')

            if not student_id or not image_data:
                return JsonResponse({'success': False, 'message': 'Missing student or image data'})

            from users.models import Student  # adjust as needed
            student = Student.objects.get(pk=student_id)

            # Decode base64 image
            header, base64_img = image_data.split(',')
            image_bytes = base64.b64decode(base64_img)
            image = Image.open(BytesIO(image_bytes)).convert('RGB')
            frame = np.array(image)

            # Face encoding
            encodings = face_recognition.face_encodings(frame)
            if not encodings:
                return JsonResponse({'success': False, 'message': 'No face detected'})

            encoding = encodings[0]

            # Save encoding
            face_obj, created = FaceEncoding.objects.update_or_create(
                student=student,
                defaults={'encoding_data': encoding.tolist()}
            )

            return JsonResponse({'success': True, 'message': 'Face uploaded successfully!'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    else:
        form = FaceUploadSelectForm()
        return render(request, 'mainscreen/upload_face.html', {'form': form})




def register_student_view(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
             # or wherever you want
    else:
        form = StudentRegistrationForm()
    return render(request, 'mainscreen/register_student.html', {'form': form})


def capture_face_view(request):
    if request.method == "POST":
        image_data = request.POST.get("image_data")

        # Decode base64 image
        format, imgstr = image_data.split(';base64,')
        image_bytes = base64.b64decode(imgstr)
        image = Image.open(BytesIO(image_bytes)).convert('RGB')
        image_np = np.array(image)

        encodings = face_recognition.face_encodings(image_np)

        if encodings:
            student = Student.objects.get(user=request.user)
            student.set_face_encoding(encodings[0])
            student.save()
            return redirect('student_dashboard')  # or any success page
        else:
            return render(request, 'mainscreen/capture_face.html', {'error': 'No face detected. Try again!'})

    return render(request, 'mainscreen/capture_face.html')



@login_required
def today_attendance(request):
    today = date.today()
    present_attendance = Attendance.objects.filter(timestamp__date=today).select_related('student__user')

    # Prepare clean list of data for the template
    students_data = []
    for entry in present_attendance:
        students_data.append({
            'student_id': entry.student.student_id,
            'name': entry.student.user.get_full_name(),
            'time': entry.timestamp.strftime('%H:%M:%S'),
        })

    context = {
        'students_data': students_data,
    }
    return render(request, 'dashboard/present_today.html', context)



@login_required
def attendance_api(request):
    today = timezone.now().date()
    attendance_records = Attendance.objects.filter(timestamp__date=today).select_related('student')

    logs = []
    for record in attendance_records:
        student = record.student
        logs.append({
            'student_id': student.student_id,
            'name': student.user.get_full_name(),
            'time': record.timestamp.strftime('%H:%M:%S'),
            'status': 'Present'
        })

    total_students = Student.objects.count()
    present_today = len(logs)
    absent_today = total_students - present_today
    attendance_rate = round((present_today / total_students) * 100, 1) if total_students else 0

    return JsonResponse({
        'logs': logs,
        'total_students': total_students,
        'present_today': present_today,
        'absent_today': absent_today,
        'attendance_rate': attendance_rate
    })


@login_required
def absent_today_view(request):
    today = timezone.now().date()
    
    # All students
    all_students = Student.objects.select_related('user').all()
    
    # Students who are present today
    present_students = Attendance.objects.filter(timestamp__date=today).values_list('student_id', flat=True)
    
    # Students who are NOT in the attendance records = absent
    absent_students = all_students.exclude(id__in=present_students)

    return render(request, 'dashboard/absent_today.html', {
        'absent_students': absent_students,
        'date': today
    })


@login_required
def attendance_report_view(request):
   
    students = Student.objects.select_related('user').all()
    attendance_records = Attendance.objects.all().order_by('-timestamp')

    # Build a dict: {student_id: {date1: True, date2: True, ...}, ...}
    student_attendance = {}
    dates = sorted(set(record.date for record in attendance_records))

    for student in students:
        student_attendance[student] = {}
        for date in dates:
            student_attendance[student][date] = False  # default to absent

    for record in attendance_records:
        student_attendance[record.student][record.date] = True

    context = {
        'students': students,
        'dates': dates,
        'student_attendance': student_attendance
    }
    return render(request, 'dashboard/attendance_report.html', context)





# # Face Recognition Utilities
class FaceRecognitionUtils:
    @staticmethod
    def load_known_faces():
        
        try:
            FaceEncoding = apps.get_model('users', 'FaceEncoding')
            face_data = FaceEncoding.objects.select_related('student__user').all()
            return (
                [np.array(student.encoding_data) for student in face_data],
                [student.student.user.get_full_name() for student in face_data]
            )
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
            return [], []

    @staticmethod
    def capture_face_encoding():
     video_capture = None
     try:
        video_capture = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not video_capture.isOpened():
            raise ValueError("Could not open camera")
        
        time.sleep(1)

        ret, frame = video_capture.read()
        video_capture.release()
        if not ret:
            raise ValueError("Could not capture frame from camera")

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(rgb_frame)
        return encodings[0] if encodings else None
     except Exception as e:
        logger.error(f"Error capturing face encoding: {e}")
        raise
     finally:
        if video_capture is not None:
            video_capture.release()
  

@method_decorator(gzip.gzip_page, name='dispatch')
class VideoFeed(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._shutdown = False
        self.camera_lock = threading.Lock()
        self.frame_queue = Queue(maxsize=1)
        self.processing_enabled = True
        self.last_error = ""
        
        # Initialize models
        self.FaceEncoding = apps.get_model('users', 'FaceEncoding')
        self.Student = apps.get_model('users', 'Student')
        self.Attendance = apps.get_model('users', 'Attendance')
        
        # Initialize components
        self._load_known_faces()
        self._init_camera()
        
        # Start processing thread if camera is available
        if self.cap and self.cap.isOpened():
            self.frame_thread = threading.Thread(
                target=self._frame_generator,
                daemon=True,
                name="CameraThread"
            )
            self.frame_thread.start()
            logger.info("Frame processing thread started")
        else:
            logger.error("Camera initialization failed - running in error mode")
        
        atexit.register(self.cleanup)

    def _init_camera(self):
     if hasattr(self, 'cap') and self.cap:
        self.cap.release()

    # Try different camera indices and backends
     backends = [
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_MSMF, "Media Foundation"),
        (cv2.CAP_V4L2, "Video4Linux"),
        (cv2.CAP_ANY, "Auto-Detect")
     ]

     for index in range(3):  # Try first 3 camera indices
        for backend, name in backends:
            try:
                self.cap = cv2.VideoCapture(index, backend)
                if self.cap.isOpened():
                    # Set camera properties
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self.cap.set(cv2.CAP_PROP_FPS, 30)
                    logger.info(f"Camera {index} initialized with {name}")
                    return
                else:
                    self.cap.release()
            except Exception as e:
                logger.warning(f"Camera {index} failed with {name}: {str(e)}")
                if hasattr(self, 'cap') and self.cap:
                    self.cap.release()

     logger.error("All camera initialization attempts failed!")
     self.cap = None
     self.last_error = "Camera initialization failed. Please check:\n1. Camera is connected\n2. No other app is using it\n3. Drivers are installed"


    def _load_known_faces(self):
        """Load known face encodings from database"""
        try:
            face_encodings = self.FaceEncoding.objects.select_related('student__user').all()
            self.known_face_encodings = [np.array(enc.encoding_data) for enc in face_encodings]
            self.known_face_names = [
                f"{enc.student.user.first_name} {enc.student.user.last_name}" 
                for enc in face_encodings
            ]
            logger.info(f"Loaded {len(self.known_face_encodings)} known faces")
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
            self.known_face_encodings = []
            self.known_face_names = []

    def _frame_generator(self):
     while not self._shutdown:
        if not self.cap or not self.cap.isOpened():
            logger.warning("Camera not available, attempting to reinitialize")
            self._init_camera()
            time.sleep(1)
            continue

        try:
            with self.camera_lock:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("Frame capture failed, reinitializing camera")
                    self._init_camera()
                    time.sleep(0.1)
                    continue

                # Process frame if needed
                if self.processing_enabled:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    face_locations = face_recognition.face_locations(rgb_frame)
                    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

                    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                        name = self.recognize_face(face_encoding)
                        self.annotate_frame(frame, (top, right, bottom, left), name)
                        self.mark_attendance(name)

                # Put frame in queue (replace old frame if queue is full)
                _, buffer = cv2.imencode('.jpg', frame)
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except Empty:
                        pass
                self.frame_queue.put(buffer.tobytes())

        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            time.sleep(1)


    def get(self, request):
        """Handle HTTP streaming request"""
        return StreamingHttpResponse(
            self.stream_frames(),
            content_type='multipart/x-mixed-replace; boundary=frame'
        )

    def stream_frames(self):
        """Generate streaming response"""
        while not self._shutdown:
            try:
                if not self.cap or not self.cap.isOpened():
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + 
                          self._get_error_frame() + b'\r\n')
                    time.sleep(1)
                    continue

                try:
                    frame = self.frame_queue.get_nowait()
                except Empty:
                    frame = self._get_error_frame()

                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + 
                      frame + b'\r\n')

            except Exception as e:
                logger.error(f"Streaming error: {e}")
                time.sleep(0.1)

    def _get_error_frame(self):
        """Generate error frame with message"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        error_msg = getattr(self, 'last_error', "Camera Not Available")
        
        # Split long messages into multiple lines
        lines = []
        for i in range(0, len(error_msg), 40):
            lines.append(error_msg[i:i+40])
        
        y = 200
        for line in lines:
            cv2.putText(frame, line, (50, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y += 40
        
        _, buffer = cv2.imencode('.jpg', frame)
        return buffer.tobytes()

    def recognize_face(self, encoding):
        """Match face against known encodings"""
        try:
            matches = face_recognition.compare_faces(
                self.known_face_encodings,
                encoding,
                tolerance=0.5
            )
            if True in matches:
                return self.known_face_names[matches.index(True)]
        except Exception as e:
            logger.error(f"Face recognition error: {e}")
        return "Unknown"

    def mark_attendance(self, name):
        """Record attendance if not already marked"""
        if name != "Unknown":
            try:
                first_name = name.split()[0]
                student = self.Student.objects.get(user__first_name=first_name)
                
                with transaction.atomic():
                    today = timezone.now().date()
                    if not self.Attendance.objects.filter(student=student, date=today).exists():
                        self.Attendance.objects.create(student=student, date=today)
                        logger.info(f"Attendance recorded for {name}")
            except ObjectDoesNotExist:
                logger.warning(f"Student not found: {name}")
            except Exception as e:
                logger.error(f"Error recording attendance: {e}")

    @staticmethod
    def annotate_frame(frame, location, name):
        """Draw face bounding box and name"""
        top, right, bottom, left = location
        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(frame, name, (left, top - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    def cleanup(self):
     self._shutdown = True

    # Signal frame queue to unblock
     try:
        if hasattr(self, 'frame_queue'):
            self.frame_queue.put(None)
     except Exception as e:
        logger.error(f"Error signaling frame queue: {e}")

    # Release camera
     if hasattr(self, 'cap') and self.cap:
        try:
            self.cap.release()
            logger.info("Camera released successfully")
        except Exception as e:
            logger.error(f"Error releasing camera: {e}")

    # Stop thread
     if hasattr(self, 'frame_thread') and self.frame_thread.is_alive():
        try:
            self.frame_thread.join(timeout=2.0)
            if self.frame_thread.is_alive():
                logger.warning("Frame thread did not stop gracefully")
            else:
                logger.info("Frame thread stopped successfully")
        except Exception as e:
            logger.error(f"Error joining thread: {e}")

    logger.info("Cleanup completed")


    def __del__(self):
        """Destructor for additional cleanup safety"""
        self.cleanup()

def camera_status(request):
    """Diagnostic endpoint to check camera status"""
    video_feed = VideoFeed()
    status = {
        'camera_initialized': video_feed.cap is not None,
        'camera_opened': video_feed.cap.isOpened() if video_feed.cap else False,
        'last_error': getattr(video_feed, 'last_error', ''),
        'thread_alive': video_feed.frame_thread.is_alive() if hasattr(video_feed, 'frame_thread') else False
    }
    return JsonResponse(status)


# Student Registration
def register_student(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            try:
                student = form.save(commit=False)
                encoding = FaceRecognitionUtils.capture_face_encoding()

                if encoding is None:
                    form.add_error(None, "No face detected! Please try again.")
                    return render(request, 'register.html', {'form': form})

                student.save()
                FaceEncoding = apps.get_model('users', 'FaceEncoding')  # Access the model here
                FaceEncoding.objects.create(
                    student=student,
                    encoding_data=encoding.tolist()
                )
                return redirect('home')
            except Exception as e:
                logger.error(f"Registration error: {e}")
                form.add_error(None, "An error occurred during registration")
    else:
        form = StudentRegistrationForm()

    return render(request, 'dashboard/register.html', {'form': form})


def get_attendance_report(request):
    """
    View to get attendance report.
    """
    if request.method == "GET":
        try:
            Attendance = apps.get_model('users', 'Attendance')
            Student = apps.get_model('users', 'Student')
            # Fetch all attendance records
            attendance_records = Attendance.objects.all().order_by('date')

            # Prepare the report data
            report_data = []
            for record in attendance_records:
                report_data.append({
                    'student_name': record.student.user.get_full_name(),
                    'date': record.date.strftime('%Y-%m-%d'),  # Format the date
                })

            return JsonResponse({'status': 'success', 'data': report_data})

        except Exception as e:
            logger.error(f"Error fetching attendance report: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})



@csrf_exempt
@require_POST
def auto_recognize(request):
    try:
        data = json.loads(request.body)
        frame_data = data.get('frame')
        if not frame_data:
            return JsonResponse({'message': 'No frame data provided'}, status=400)

        # Decode base64 image
        image_bytes = base64.b64decode(frame_data)
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert('RGB')
        np_image = np.array(image)

        # Detect faces
        unknown_encodings = face_recognition.face_encodings(np_image)
        if not unknown_encodings:
            return JsonResponse({'message': 'No face detected'}, status=200)

        unknown_encoding = unknown_encodings[0]

        # Compare with known encodings
        students = FaceEncoding.objects.select_related('student').all()
        for student_data in students:
            known_encoding = np.array(student_data.encoding_data)
            match = face_recognition.compare_faces([known_encoding], unknown_encoding, tolerance=0.5)[0]
            if match:
                student = student_data.student
                # Prevent duplicate LiveAttendance
                if not LiveAttendance.objects.filter(student=student, status='verified', timestamp__date=now().date()).exists():
                    LiveAttendance.objects.create(
                        student=student,
                        subject=Subject.objects.first(),  # You might change this to actual subject/session
                        status="verified"
                    )
                return JsonResponse({
                    'recognized': True,
                    'student_id': student.student_id,
                    'name': student.user.get_full_name()
                })

        return JsonResponse({'recognized': False, 'message': 'Face not recognized'})
    
    except Exception as e:
     import traceback
     traceback.print_exc()  # 👈 Logs full error to the console
     return JsonResponse({'message': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def mark_absent(request):
    try:
        data = json.loads(request.body)
        recognized_ids = data.get('recognized_ids', [])
        session_start = data.get('session_start')

        if not session_start:
            return JsonResponse({'message': 'Missing session start time'}, status=400)

        all_students = Student.objects.all()
        absent_students = all_students.exclude(student_id__in=recognized_ids)

        # Mark attendance for recognized students
        for sid in recognized_ids:
            student = Student.objects.filter(student_id=sid).first()
            if student:
                Attendance.objects.get_or_create(student=student, timestamp__date=now().date())

        # Optionally log absentees
        absent_count = 0
        for student in absent_students:
            absent_count += 1
            # No DB entry needed unless you want to log it

        return JsonResponse({'message': 'Absent students processed', 'absent_count': absent_count})
    
    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)
    

def student_list(request):
    students = Student.objects.select_related('user').all()
    return render(request, 'dashboard/student_list.html', {'students': students})



@login_required
def export_attendance_csv(request):
    attendance_records = Attendance.objects.all().order_by('date')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Student', 'Date'])

    for record in attendance_records:
        writer.writerow([record.student.user.get_full_name(), record.date])

    return response