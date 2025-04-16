from django import forms
from .models import Student, User  # Use your custom User

class StudentRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    username = forms.CharField(max_length=30, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = Student
        fields = ['student_id', 'course', 'year_of_study']

    def save(self, commit=True):
        # Create user with is_student flag
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            password=self.cleaned_data['password'],
            is_student=True  # ✅ Flag this user as a student
        )

        student = super().save(commit=False)
        student.user = user
        if commit:
            student.save()
        return student
    

class FaceUploadForm(forms.Form):
    image = forms.ImageField(required=True)

class FaceUploadSelectForm(forms.Form):
    student = forms.ModelChoiceField(queryset=Student.objects.select_related('user').all(), label="Select Student")

class StudentLoginForm(forms.Form):
    username = forms.CharField(max_length=30)
    password = forms.CharField(widget=forms.PasswordInput)