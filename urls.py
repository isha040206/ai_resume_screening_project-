from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.login_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Candidate
    path('dashboard/', views.candidate_dashboard, name='candidate_dashboard'),
    path('profile/', views.candidate_profile, name='candidate_profile'),
    path('jobs/', views.job_list_candidate, name='candidate_job_list'),
    path('jobs/<int:job_id>/apply/', views.apply_job, name='apply_job'),
    path('applications/', views.candidate_applications, name='candidate_applications'),

    # HR
    path('hr/dashboard/', views.hr_dashboard, name='hr_dashboard'),
    path('hr/jobs/', views.job_list_hr, name='hr_job_list'),
    path('hr/jobs/create/', views.job_create, name='hr_job_create'),
    path('hr/jobs/<int:job_id>/edit/', views.job_edit, name='hr_job_edit'),
    path('hr/jobs/<int:job_id>/delete/', views.job_delete, name='hr_job_delete'),
    path('hr/candidates/', views.candidate_list, name='hr_candidate_list'),
    path('hr/candidates/<int:candidate_id>/', views.candidate_detail, name='hr_candidate_detail'),
    path('hr/applications/<int:app_id>/status/<str:new_status>/', views.update_application_status, name='update_status'),
    path('hr/rankings/', views.rankings_view, name='hr_rankings'),
    path('hr/rankings/<int:job_id>/recompute/', views.recompute_rankings_view, name='recompute_rankings'),

    # Reports
    path('hr/reports/', views.report_page, name='hr_reports'),
    path('hr/reports/export/excel/', views.export_candidates_excel, name='export_excel'),
    path('hr/reports/export/pdf/', views.export_pdf_report, name='export_pdf'),
    path('hr/reports/rankings/<int:job_id>/pdf/', views.export_rankings_pdf, name='export_rankings_pdf'),
]
