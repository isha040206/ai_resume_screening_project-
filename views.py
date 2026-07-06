import json
import os
import io
import logging
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Avg, Q
from django.conf import settings

from .models import CandidateProfile, JobPost, Application, ResumeAnalysis, Ranking
from .forms import (
    CandidateRegistrationForm, LoginForm, CandidateProfileForm,
    ResumeUploadForm, JobPostForm
)
from .ai_parser import parse_resume, calculate_match_score, rank_candidates

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def is_hr(user):
    return user.is_staff or user.is_superuser


def hr_required(view_func):
    """Decorator: only staff/superusers (HR) may access."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not is_hr(request.user):
            messages.error(request, "Access denied. HR credentials required.")
            return redirect('candidate_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def candidate_required(view_func):
    """Decorator: only non-staff users (candidates) may access."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if is_hr(request.user):
            return redirect('hr_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────
# AUTH VIEWS
# ─────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('hr_dashboard' if is_hr(request.user) else 'candidate_dashboard')
    form = CandidateRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome, {user.candidate_profile.full_name}! Your account is ready.")
        return redirect('candidate_dashboard')
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('hr_dashboard' if is_hr(request.user) else 'candidate_dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user:
            login(request, user)
            return redirect('hr_dashboard' if is_hr(user) else 'candidate_dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'auth/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')


# ─────────────────────────────────────────────
# CANDIDATE VIEWS
# ─────────────────────────────────────────────

@candidate_required
def candidate_dashboard(request):
    profile = get_object_or_404(CandidateProfile, user=request.user)
    applications = Application.objects.filter(candidate=profile).select_related('job')
    analyses = ResumeAnalysis.objects.filter(candidate=profile).select_related('job')
    rankings = Ranking.objects.filter(candidate=profile).select_related('job')
    ctx = {
        'profile': profile,
        'applications': applications,
        'analyses': analyses,
        'rankings': rankings,
        'total_applied': applications.count(),
        'selected': applications.filter(status='selected').count(),
        'rejected': applications.filter(status='rejected').count(),
    }
    return render(request, 'candidate/dashboard.html', ctx)


@candidate_required
def candidate_profile(request):
    profile = get_object_or_404(CandidateProfile, user=request.user)
    profile_form = CandidateProfileForm(request.POST or None, instance=profile)
    resume_form = ResumeUploadForm(request.POST or None, request.FILES or None, instance=profile)

    if request.method == 'POST':
        if 'save_profile' in request.POST and profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('candidate_profile')

        if 'upload_resume' in request.POST and resume_form.is_valid():
            resume_form.save()
            messages.success(request, "Resume uploaded successfully. Apply for jobs to run AI analysis.")
            return redirect('candidate_profile')

    return render(request, 'candidate/profile.html', {
        'profile': profile,
        'profile_form': profile_form,
        'resume_form': resume_form,
    })


@candidate_required
def job_list_candidate(request):
    jobs = JobPost.objects.filter(is_active=True).order_by('-created_date')
    profile = get_object_or_404(CandidateProfile, user=request.user)
    applied_job_ids = Application.objects.filter(candidate=profile).values_list('job_id', flat=True)
    return render(request, 'candidate/job_list.html', {
        'jobs': jobs,
        'applied_job_ids': list(applied_job_ids),
        'profile': profile,
    })


@candidate_required
def apply_job(request, job_id):
    job = get_object_or_404(JobPost, id=job_id, is_active=True)
    profile = get_object_or_404(CandidateProfile, user=request.user)

    if not profile.resume_file:
        messages.warning(request, "Please upload your resume before applying.")
        return redirect('candidate_profile')

    if Application.objects.filter(candidate=profile, job=job).exists():
        messages.info(request, "You have already applied for this job.")
        return redirect('candidate_applications')

    # Create application
    Application.objects.create(candidate=profile, job=job, status='applied')

    # Run AI analysis
    try:
        resume_path = os.path.join(settings.MEDIA_ROOT, str(profile.resume_file))
        parsed = parse_resume(resume_path)
        required_skills = job.get_required_skills_list()
        score, matched, missing = calculate_match_score(parsed['skills'], required_skills)

        # Save analysis
        analysis, _ = ResumeAnalysis.objects.update_or_create(
            candidate=profile, job=job,
            defaults={
                'extracted_text': parsed['raw_text'][:2000],
                'extracted_skills': json.dumps(parsed['skills']),
                'matched_skills': json.dumps(matched),
                'missing_skills': json.dumps(missing),
                'score': score,
                'name_extracted': parsed['name'],
                'email_extracted': parsed['email'],
                'phone_extracted': parsed['phone'],
                'education_extracted': parsed['education'],
                'experience_extracted': parsed['experience'],
            }
        )

        # Update candidate best score
        if score > profile.score:
            profile.score = score
            profile.save()

        # Recompute rankings for this job
        _recompute_rankings(job)
        messages.success(request, f"Applied! Your match score: {score:.1f}%")

    except Exception as e:
        logger.error(f"Analysis error: {e}")
        messages.warning(request, "Applied successfully. Analysis will be available shortly.")

    return redirect('candidate_applications')


@candidate_required
def candidate_applications(request):
    profile = get_object_or_404(CandidateProfile, user=request.user)
    applications = Application.objects.filter(candidate=profile).select_related('job').order_by('-applied_date')
    analyses = {a.job_id: a for a in ResumeAnalysis.objects.filter(candidate=profile)}
    app_data = []
    for app in applications:
        analysis = analyses.get(app.job_id)
        app_data.append({
            'application': app,
            'analysis': analysis,
            'matched_skills': json.loads(analysis.matched_skills) if analysis else [],
            'missing_skills': json.loads(analysis.missing_skills) if analysis else [],
            'score': analysis.score if analysis else 0,
        })
    return render(request, 'candidate/applications.html', {'app_data': app_data, 'profile': profile})


# ─────────────────────────────────────────────
# HR / ADMIN VIEWS
# ─────────────────────────────────────────────

@hr_required
def hr_dashboard(request):
    total_candidates = CandidateProfile.objects.count()
    total_jobs = JobPost.objects.filter(is_active=True).count()
    total_applications = Application.objects.count()
    selected = Application.objects.filter(status='selected').count()
    rejected = Application.objects.filter(status='rejected').count()
    shortlisted = Application.objects.filter(status='shortlisted').count()

    top_ranking = Ranking.objects.select_related('candidate', 'job').order_by('rank').first()
    recent_applications = Application.objects.select_related('candidate', 'job').order_by('-applied_date')[:5]

    # Chart data: applications per job (top 6)
    job_app_data = (
        Application.objects.values('job__job_title')
        .annotate(count=Count('id'))
        .order_by('-count')[:6]
    )
    chart_labels = [d['job__job_title'] for d in job_app_data]
    chart_values = [d['count'] for d in job_app_data]

    # Scores distribution (top 10 by score)
    top_scores = (
        ResumeAnalysis.objects.select_related('candidate')
        .order_by('-score')[:10]
    )
    score_labels = [a.candidate.full_name for a in top_scores]
    score_values = [a.score for a in top_scores]

    ctx = {
        'total_candidates': total_candidates,
        'total_jobs': total_jobs,
        'total_applications': total_applications,
        'selected': selected,
        'rejected': rejected,
        'shortlisted': shortlisted,
        'top_ranking': top_ranking,
        'recent_applications': recent_applications,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
        'score_labels': json.dumps(score_labels),
        'score_values': json.dumps(score_values),
        'pie_data': json.dumps([total_applications - selected - rejected, selected, rejected]),
    }
    return render(request, 'hr/dashboard.html', ctx)


@hr_required
def job_list_hr(request):
    jobs = JobPost.objects.annotate(app_count=Count('applications')).order_by('-created_date')
    return render(request, 'hr/job_list.html', {'jobs': jobs})


@hr_required
def job_create(request):
    form = JobPostForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        job = form.save(commit=False)
        job.created_by = request.user
        job.save()
        messages.success(request, f"Job '{job.job_title}' created successfully.")
        return redirect('hr_job_list')
    return render(request, 'hr/job_form.html', {'form': form, 'title': 'Create Job Post'})


@hr_required
def job_edit(request, job_id):
    job = get_object_or_404(JobPost, id=job_id)
    form = JobPostForm(request.POST or None, instance=job)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Job post updated.")
        return redirect('hr_job_list')
    return render(request, 'hr/job_form.html', {'form': form, 'title': 'Edit Job Post', 'job': job})


@hr_required
def job_delete(request, job_id):
    job = get_object_or_404(JobPost, id=job_id)
    if request.method == 'POST':
        job.delete()
        messages.success(request, "Job post deleted.")
        return redirect('hr_job_list')
    return render(request, 'hr/job_confirm_delete.html', {'job': job})


@hr_required
def candidate_list(request):
    query = request.GET.get('q', '')
    skill_filter = request.GET.get('skill', '')
    status_filter = request.GET.get('status', '')

    candidates = CandidateProfile.objects.select_related('user').order_by('-score')

    if query:
        candidates = candidates.filter(
            Q(full_name__icontains=query) | Q(email__icontains=query)
        )
    if status_filter:
        candidates = candidates.filter(status=status_filter)

    # Skill filter: look in analyses extracted_skills
    if skill_filter:
        skill_lower = skill_filter.lower()
        matching_ids = [
            a.candidate_id for a in
            ResumeAnalysis.objects.all()
            if skill_lower in a.extracted_skills.lower()
        ]
        candidates = candidates.filter(id__in=matching_ids)

    return render(request, 'hr/candidate_list.html', {
        'candidates': candidates,
        'query': query,
        'skill_filter': skill_filter,
        'status_filter': status_filter,
    })


@hr_required
def candidate_detail(request, candidate_id):
    profile = get_object_or_404(CandidateProfile, id=candidate_id)
    analyses = ResumeAnalysis.objects.filter(candidate=profile).select_related('job')
    applications = Application.objects.filter(candidate=profile).select_related('job')
    rankings = Ranking.objects.filter(candidate=profile).select_related('job')

    analysis_data = []
    for a in analyses:
        analysis_data.append({
            'analysis': a,
            'matched': json.loads(a.matched_skills) if a.matched_skills else [],
            'missing': json.loads(a.missing_skills) if a.missing_skills else [],
            'extracted': json.loads(a.extracted_skills) if a.extracted_skills else [],
        })

    return render(request, 'hr/candidate_detail.html', {
        'profile': profile,
        'analysis_data': analysis_data,
        'applications': applications,
        'rankings': rankings,
    })


@hr_required
def update_application_status(request, app_id, new_status):

    app = get_object_or_404(Application, id=app_id)

    if request.method != "POST":
        return redirect("hr_candidate_detail", candidate_id=app.candidate.id)

    valid_status = [
        "applied",
        "under_review",
        "shortlisted",
        "selected",
        "rejected",
    ]

    if new_status not in valid_status:
        messages.error(request, "Invalid Status")
        return redirect("hr_candidate_detail", candidate_id=app.candidate.id)

    # Update Application Status
    app.status = new_status
    app.save()

    # Update Candidate Profile Status
    if new_status == "selected":
        app.candidate.status = "selected"

    elif new_status == "shortlisted":
        app.candidate.status = "shortlisted"

    elif new_status == "rejected":
        app.candidate.status = "rejected"

    else:
        app.candidate.status = "pending"

    app.candidate.save()

    messages.success(request, f"Candidate marked as {new_status.title()}.")

    return redirect("hr_candidate_detail", candidate_id=app.candidate.id)

@hr_required
def rankings_view(request):
    job_id = request.GET.get('job')
    jobs = JobPost.objects.filter(is_active=True)
    selected_job = None
    rankings = []

    if job_id:
        selected_job = get_object_or_404(JobPost, id=job_id)
        rankings = Ranking.objects.filter(job=selected_job).select_related('candidate').order_by('rank')

    return render(request, 'hr/rankings.html', {
        'jobs': jobs,
        'selected_job': selected_job,
        'rankings': rankings,
    })


@hr_required
def recompute_rankings_view(request, job_id):
    job = get_object_or_404(JobPost, id=job_id)
    _recompute_rankings(job)
    messages.success(request, f"Rankings recomputed for '{job.job_title}'.")
    return redirect(f'/hr/rankings/?job={job_id}')


def _recompute_rankings(job):
    """Internal helper: recompute and store rankings for a job."""
    analyses = ResumeAnalysis.objects.filter(job=job)
    data = [{'candidate_id': a.candidate_id, 'score': a.score} for a in analyses]
    ranked = rank_candidates(data)
    for item in ranked:
        Ranking.objects.update_or_create(
            candidate_id=item['candidate_id'], job=job,
            defaults={
                'rank': item['rank'],
                'score': item['score'],
                'is_recommended': item['is_recommended'],
            }
        )


# ─────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────

@hr_required
def report_page(request):
    jobs = JobPost.objects.all()
    return render(request, 'hr/reports.html', {'jobs': jobs})


@hr_required
def export_candidates_excel(request):
    import pandas as pd
    candidates = CandidateProfile.objects.all().values(
        'full_name', 'email', 'phone', 'education', 'experience', 'score', 'status'
    )
    df = pd.DataFrame(list(candidates))
    df.columns = ['Full Name', 'Email', 'Phone', 'Education', 'Experience', 'Score (%)', 'Status']

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="candidates_report.xlsx"'
    df.to_excel(response, index=False)
    return response


@hr_required
def export_pdf_report(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.units import cm

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                 fontSize=18, textColor=colors.HexColor('#1a237e'),
                                 spaceAfter=12, alignment=1)
    elements.append(Paragraph("AI Resume Screening System — Candidate Report", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))

    # Table
    candidates = CandidateProfile.objects.all().order_by('-score')
    table_data = [['#', 'Name', 'Email', 'Score (%)', 'Status']]
    for i, c in enumerate(candidates, 1):
        table_data.append([str(i), c.full_name, c.email, f"{c.score:.1f}%", c.get_status_display()])

    t = Table(table_data, colWidths=[1*cm, 5*cm, 6*cm, 2.5*cm, 2.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="candidate_report.pdf"'
    return response


@hr_required
def export_rankings_pdf(request, job_id):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.units import cm

    job = get_object_or_404(JobPost, id=job_id)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                 fontSize=16, textColor=colors.HexColor('#1a237e'),
                                 spaceAfter=8, alignment=1)
    elements.append(Paragraph(f"Candidate Ranking Report", title_style))
    elements.append(Paragraph(f"Job: {job.job_title}", styles['Heading2']))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))

    rankings = Ranking.objects.filter(job=job).select_related('candidate').order_by('rank')
    table_data = [['Rank', 'Candidate Name', 'Email', 'Score (%)', 'Recommended']]
    for r in rankings:
        rec = '★ Yes' if r.is_recommended else 'No'
        table_data.append([str(r.rank), r.candidate.full_name, r.candidate.email, f"{r.score:.1f}%", rec])

    t = Table(table_data, colWidths=[1.5*cm, 5*cm, 5.5*cm, 2.5*cm, 2.5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#e8eaf6')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#c5cae9')),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ranking_{job_id}.pdf"'
    return response
