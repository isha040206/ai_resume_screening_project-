#!/usr/bin/env python
"""
One-time setup: creates superuser and sample data.
Run: python setup.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_resume_screening.settings')
django.setup()

from django.contrib.auth.models import User
from screening.models import JobPost

# Create HR superuser
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@resumeai.com', 'admin123')
    print("✓ HR Admin created  →  username: admin  |  password: admin123")
else:
    print("✓ Admin already exists")

# Sample Job Posts
sample_jobs = [
    {
        'job_title': 'Python Backend Developer',
        'job_description': 'We are looking for an experienced Python developer to build and maintain scalable web applications using Django and REST APIs.',
        'required_skills': 'Python, Django, SQL, REST API, Git, Docker',
        'experience_required': '1-3 years',
        'education_required': 'B.E. / B.Tech Computer Science',
    },
    {
        'job_title': 'Full Stack Web Developer',
        'job_description': 'Join our team to develop modern web applications using React on the frontend and Node.js or Django on the backend.',
        'required_skills': 'JavaScript, React, HTML, CSS, NodeJS, SQL, Git',
        'experience_required': '1-2 years',
        'education_required': 'B.E. / B.Tech IT or CS',
    },
    {
        'job_title': 'Data Science Engineer',
        'job_description': 'Analyze large datasets, build ML models, and derive actionable insights for business decision-making.',
        'required_skills': 'Python, Machine Learning, Deep Learning, Pandas, Numpy, SQL, Scikit-learn',
        'experience_required': '0-2 years',
        'education_required': 'B.Tech / M.Tech Computer Science or Data Science',
    },
    {
        'job_title': 'DevOps Engineer',
        'job_description': 'Manage CI/CD pipelines, containerization, and cloud infrastructure on AWS.',
        'required_skills': 'Docker, Kubernetes, AWS, Linux, Git, Jenkins, Bash',
        'experience_required': '1-3 years',
        'education_required': 'B.E. / B.Tech any branch',
    },
]

admin_user = User.objects.get(username='admin')
created = 0
for job_data in sample_jobs:
    if not JobPost.objects.filter(job_title=job_data['job_title']).exists():
        JobPost.objects.create(created_by=admin_user, **job_data)
        created += 1

print(f"✓ {created} sample job posts created")
print("\n=== Setup Complete ===")
print("HR Login  →  /login/  →  admin / admin123")
print("Candidate → /register/ to create a new account")
