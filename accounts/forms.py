from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from .models import User


DEPARTMENT_CHOICES = [
    ('', 'Select Department'),
    ('Computer Science', 'Computer Science'),
    ('Information Science', 'Information Science'),
    ('Electronics & Communication', 'Electronics & Communication'),
    ('Electrical Engineering', 'Electrical Engineering'),
    ('Mechanical Engineering', 'Mechanical Engineering'),
    ('Civil Engineering', 'Civil Engineering'),
    ('Chemical Engineering', 'Chemical Engineering'),
    ('Biotechnology', 'Biotechnology'),
    ('Mathematics', 'Mathematics'),
    ('Physics', 'Physics'),
    ('Other', 'Other'),
]

SEMESTER_CHOICES = [(i, f'Semester {i}') for i in range(1, 9)]


class StudentRegistrationForm(UserCreationForm):
    full_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'College Email'})
    )
    usn = forms.CharField(
        max_length=20,
        label='USN',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1XX22CS001'})
    )
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    department = forms.ChoiceField(
        choices=DEPARTMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    semester = forms.ChoiceField(
        choices=[('', 'Select Semester')] + SEMESTER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'usn', 'phone_number',
                  'department', 'semester', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_usn(self):
        usn = self.cleaned_data.get('usn', '').strip().upper()
        if User.objects.filter(usn=usn).exists():
            raise forms.ValidationError('A student with this USN already exists.')
        return usn

    def clean_semester(self):
        semester = self.cleaned_data.get('semester')
        if not semester:
            raise forms.ValidationError('Please select a semester.')
        return int(semester)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.full_name = self.cleaned_data['full_name']
        user.email = self.cleaned_data['email']
        user.usn = self.cleaned_data['usn']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.department = self.cleaned_data['department']
        user.semester = self.cleaned_data['semester']
        user.role = User.Role.STUDENT
        if commit:
            user.save()
        return user


class StudentLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        if username and password:
            user = User.objects.filter(username=username).first()
            if user and not user.is_active and user.check_password(password):
                raise forms.ValidationError('This account has been deactivated.')
            self.user = authenticate(username=username, password=password)
            if self.user is None:
                raise forms.ValidationError('Invalid username or password.')
        return cleaned_data

    def get_user(self):
        return getattr(self, 'user', None)


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone_number', 'department', 'semester']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(choices=DEPARTMENT_CHOICES, attrs={'class': 'form-select'}),
            'semester': forms.Select(choices=[('', '---')] + SEMESTER_CHOICES, attrs={'class': 'form-select'}),
        }
