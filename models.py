from django.db import models
from django.contrib.auth.models import User


class CandidateProfile(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
        ('shortlisted', 'Shortlisted'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='candidate_profile')
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    education = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    resume_file = models.FileField(upload_to='resumes/', blank=True, null=True)
    score = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = 'Candidate Profile'
        verbose_name_plural = 'Candidate Profiles'


class JobPost(models.Model):
    job_title = models.CharField(max_length=200)
    job_description = models.TextField()
    required_skills = models.TextField(help_text="Comma-separated list of required skills")
    experience_required = models.CharField(max_length=100, blank=True, default='0-1 years')
    education_required = models.CharField(max_length=200, blank=True, default='Bachelor\'s Degree')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='job_posts')
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.job_title

    def get_required_skills_list(self):
        return [s.strip().lower() for s in self.required_skills.split(',') if s.strip()]

    class Meta:
        verbose_name = 'Job Post'
        verbose_name_plural = 'Job Posts'
        ordering = ['-created_date']


class Application(models.Model):
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
    ]

    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='applications')
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    applied_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.candidate.full_name} → {self.job.job_title}"

    class Meta:
        unique_together = ['candidate', 'job']
        ordering = ['-applied_date']


class ResumeAnalysis(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='analyses')
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='analyses')
    extracted_text = models.TextField(blank=True)
    extracted_skills = models.TextField(blank=True, help_text="JSON list of extracted skills")
    matched_skills = models.TextField(blank=True, help_text="JSON list of matched skills")
    missing_skills = models.TextField(blank=True, help_text="JSON list of missing skills")
    score = models.FloatField(default=0.0)
    name_extracted = models.CharField(max_length=200, blank=True)
    email_extracted = models.EmailField(blank=True)
    phone_extracted = models.CharField(max_length=20, blank=True)
    education_extracted = models.TextField(blank=True)
    experience_extracted = models.TextField(blank=True)
    analyzed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis: {self.candidate.full_name} for {self.job.job_title}"

    class Meta:
        unique_together = ['candidate', 'job']
        ordering = ['-analyzed_at']


class Ranking(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='rankings')
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='rankings')
    rank = models.IntegerField(default=0)
    score = models.FloatField(default=0.0)
    is_recommended = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Rank {self.rank}: {self.candidate.full_name} ({self.score:.1f}%)"

    class Meta:
        unique_together = ['candidate', 'job']
        ordering = ['rank']
