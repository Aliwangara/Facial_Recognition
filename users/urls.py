
from django.urls import path
from facialR_project import settings
from users import views, superuser_views

urlpatterns = [
    path('',views.home, name='home'),
    path('register/student/', views.register_student_view, name='register_student'),
    path('upload_face/', views.upload_face, name='upload_face'),
   path('dashboard/', views.dashboard, name='dashboard'),
    path('today/', views.today_attendance, name='today'),
    path('absent/', views.absent_today_view, name='absent'),
    path('api/attendance/', views.attendance_api, name='attendance_api'), 
    path('attendance/report/', views.attendance_report_view, name='attendance_report'),
    path('attendance/export/csv/', views.export_attendance_csv, name='export_attendance_csv'),


    # path('video_feed/', VideoFeed.as_view(), name='video_feed'),
    # path('register/', views.register_student, name='register'),
   path('auto_recognize/', views.auto_recognize, name='auto_recognize'),
    path('mark_absent/', views.mark_absent, name='mark_absent'),


    path('students/', views.student_list, name='student_list'),

    path('choose-role/', views.choose_role, name='choose_role'),
    path('login/student/', views.student_login_view, name='student_login'),

    path('admin/manage-teachers/', superuser_views.manage_teachers_view, name='manage_teachers'),
    


]