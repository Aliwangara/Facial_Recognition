from django.contrib import admin
from .models import User, Student, Subject, Attendance, LiveAttendance, FaceEncoding

# Register your models here.
admin.site.register(User)
admin.site.register(Student)
admin.site.register(Subject)
admin.site.register(Attendance)
admin.site.register(LiveAttendance)
admin.site.register(FaceEncoding)
