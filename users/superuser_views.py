# users/views.py

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import User

@login_required
@staff_member_required
def manage_teachers_view(request):
    pending_teachers = User.objects.filter(is_teacher=True, is_approved_teacher=False)

    if request.method == 'POST':
        teacher_id = request.POST.get('teacher_id')
        action = request.POST.get('action')
        teacher = get_object_or_404(User, id=teacher_id)

        if action == 'approve':
            teacher.is_approved_teacher = True
            teacher.save()
        elif action == 'block':
            teacher.is_active = False
            teacher.save()

        return redirect('manage_teachers')

    return render(request, 'admin/manage_teachers.html', {'pending_teachers': pending_teachers})
