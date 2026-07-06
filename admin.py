from django.contrib import admin
from .models import CandidateProfile, JobPost, Application, ResumeAnalysis, Ranking


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'phone', 'score', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['full_name', 'email']
    ordering = ['-score']


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ['job_title', 'experience_required', 'is_active', 'created_date']
    list_filter = ['is_active']
    search_fields = ['job_title']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'job', 'status', 'applied_date']
    list_filter = ['status']


@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'job', 'score', 'analyzed_at']
    ordering = ['-score']


@admin.register(Ranking)
class RankingAdmin(admin.ModelAdmin):
    list_display = ['rank', 'candidate', 'job', 'score', 'is_recommended']
    ordering = ['rank']
