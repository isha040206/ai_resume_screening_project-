from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import CandidateProfile, JobPost, Application


class CandidateRegistrationForm(UserCreationForm):
    full_name = forms.CharField(max_length=200, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Full Name'}))
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={'class': 'form-control', 'placeholder': 'Email Address'}))
    phone = forms.CharField(max_length=20, required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Phone Number'}))

    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'phone', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            CandidateProfile.objects.create(
                user=user,
                full_name=self.cleaned_data['full_name'],
                email=self.cleaned_data['email'],
                phone=self.cleaned_data.get('phone', ''),
            )
        return user


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={'class': 'form-control', 'placeholder': 'Password'}))


class CandidateProfileForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = ['full_name', 'email', 'phone', 'education', 'experience']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'education': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                               'placeholder': 'e.g. B.Tech Computer Science, XYZ University, 2024'}),
            'experience': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                'placeholder': 'e.g. Intern at ABC Corp (6 months), Projects...'}),
        }


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = ['resume_file']
        widgets = {
            'resume_file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
        }

    def clean_resume_file(self):
        f = self.cleaned_data.get('resume_file')
        if f:
            if not f.name.endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are accepted.")
            if f.size > 5 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 5 MB.")
        return f


class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = ['job_title', 'job_description', 'required_skills', 'experience_required', 'education_required', 'is_active']
        widgets = {
            'job_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Python Backend Developer'}),
            'job_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 6,
                                                     'placeholder': 'Describe the role, responsibilities...'}),
            'required_skills': forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                     'placeholder': 'Python, Django, SQL, REST API, Git'}),
            'experience_required': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 0-2 years'}),
            'education_required': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "e.g. B.Tech / B.E."}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
