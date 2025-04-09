from django.contrib.auth.models import AbstractUser,Group, Permission
from django.db import models
from django.utils.timezone import now
import json

# Custom User Model (For Teachers & Students)
class User(AbstractUser):
    is_teacher = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)
    
    # Add these to resolve the clashes
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="custom_user_groups",  # Unique related_name
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="custom_user_permissions",  # Unique related_name
        related_query_name="custom_user",
    )

    def __str__(self):
        return self.username

# Student Model
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    course = models.CharField(max_length=100)
    year_of_study = models.IntegerField()
    face_encoding = models.TextField()  # Store face encoding as JSON string

    def set_face_encoding(self, encoding):
        """Save face encoding as JSON string"""
        self.face_encoding = json.dumps(encoding.tolist())

    def get_face_encoding(self):
        """Retrieve face encoding as NumPy array"""
        return np.array(json.loads(self.face_encoding))
    
    def __str__(self):
        return self.user.get_full_name()

# Class/Subject Model
class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'is_teacher': True})

    def __str__(self):
        return self.name

# Attendance Model (Finalized Attendance)
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.timestamp}"

# Face Encoding Model (For AI Processing)
class FaceEncoding(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    encoding_data = models.JSONField()  # Store face embeddings as a JSON array

    def __str__(self):
        return f"Face Data for {self.student.user.get_full_name()}"

# Live Attendance Log (For Real-Time Tracking)
class LiveAttendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(default=now)
    status = models.CharField(max_length=20, choices=[("detected", "Detected"), ("verified", "Verified")])

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.status}"
    

