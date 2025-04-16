from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(user_signed_up)
def handle_teacher_signup(request, user, **kwargs):
    # Flag as teacher (not approved yet)
    user.is_teacher = True
    user.is_approved_teacher = False
    user.save()
