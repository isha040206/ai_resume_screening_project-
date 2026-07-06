# AI Resume Screening System
### Final Year IT Engineering Project — Django + AI/NLP

---

## Project Overview
An AI-powered system that automatically screens resumes, extracts skills using NLP, matches candidates to job descriptions, ranks them by score, and generates professional reports.

---

## Technology Stack
| Layer       | Technology                            |
|-------------|---------------------------------------|
| Backend     | Python 3.11 – 3.14, Django 5.2 (LTS)  |
| Database    | SQLite                                |
| Frontend    | Bootstrap 5, Chart.js, Font Awesome  |
| Resume Parsing | pypdf + regex-based extraction (name, email, phone, skills, education, experience) |
| Reports     | ReportLab, Pandas, openpyxl          |

---

## Setup Instructions

### Step 1 — Clone / Download the Project
```
cd Desktop
# (place project folder here)
```

### Step 2 — Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate        # Mac/Linux
```

### Step 3 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Run Migrations
Migrations are already included in `screening/migrations/`. If you ever change
`models.py`, regenerate them with `python manage.py makemigrations screening`.
```bash
python manage.py migrate
```

### Step 5 — Load Sample Data (HR admin login + sample job posts)
```bash
python setup.py
```

### Step 6 — Collect Static Files (optional, for production)
```bash
python manage.py collectstatic --noinput
```

### Step 7 — Start Server
```bash
python manage.py runserver
```

Open: **http://127.0.0.1:8000/**

---

## Sample Data

Two ready-to-use samples are included so you can test the whole pipeline
immediately without creating data by hand:

- **Sample Job Post** — `screening/fixtures/sample_job.json` (Django fixture).
  Load it with:
  ```bash
  python manage.py loaddata sample_job
  ```
  (`python setup.py`, described above, also creates four sample job posts
  and the HR admin account in one step.)
- **Sample Resume** — `samples/sample_resume.pdf`, a realistic PDF resume you
  can upload as a candidate to see the AI parser and match score in action.
  Regenerate it any time with `python samples/make_sample_resume.py`.

## Default Credentials

| Role      | Username | Password  | URL          |
|-----------|----------|-----------|--------------|
| HR Admin  | admin    | admin123  | /login/      |
| Candidate | register | (new)     | /register/   |

---

## Folder Structure
```
ai_resume_screening/
│
├── ai_resume_screening/       # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── screening/                 # Main app
│   ├── models.py              # Database models
│   ├── views.py               # All view logic
│   ├── forms.py               # Django forms
│   ├── urls.py                # URL routing
│   ├── admin.py               # Admin panel
│   ├── ai_parser.py           # Resume parser & AI matching engine
│   ├── migrations/            # Database migrations (already generated)
│   ├── fixtures/
│   │   └── sample_job.json    # Sample job post fixture
│   └── templatetags/
│       └── extra_filters.py   # Custom template filters
│
├── samples/
│   ├── make_sample_resume.py  # Script that generates sample_resume.pdf
│   └── sample_resume.pdf      # Ready-to-use sample resume for testing
│
├── templates/
│   ├── base.html              # Master layout with sidebar
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── candidate/
│   │   ├── dashboard.html
│   │   ├── profile.html
│   │   ├── job_list.html
│   │   └── applications.html
│   └── hr/
│       ├── dashboard.html
│       ├── job_list.html
│       ├── job_form.html
│       ├── candidate_list.html
│       ├── candidate_detail.html
│       ├── rankings.html
│       └── reports.html
│
├── static/
│   ├── css/main.css
│   └── js/main.js
│
├── media/resumes/             # Uploaded PDFs stored here
├── requirements.txt
├── manage.py
└── setup.py
```

---

## AI Features Explained

### 1. Resume Parsing (ai_parser.py)
- Extracts text from PDF using **pypdf** (handles password-protected PDFs and
  clearly logs when a PDF has no extractable text, e.g. a scanned image)
- Uses **regex** to extract Name, Email, Phone
- Section-aware extraction for Education and Experience

### 2. Skill Extraction
- Matches against a curated database of **100+ IT skills**
- Uses `\bword\b` word-boundary regex for accurate matching
- Handles multi-word skills (e.g. "machine learning", "react native")

### 3. Skill Matching & Scoring
```
Score = (Matched Skills ÷ Required Skills) × 100
```
- Skills are normalized through an alias table before comparing, so
  "ReactJS" on a resume correctly matches "React" on a job post, "Node"
  matches "Node.js", "ML" matches "Machine Learning", etc. This is what
  keeps the score from getting stuck at 0% due to spelling differences.
- Returns matched skills list and missing skills list
- Color-coded: Green ≥70%, Yellow ≥40%, Red <40%

### 4. Candidate Ranking
- Sorted by score descending
- Top 3 automatically marked as "Recommended"
- Displayed with gold/silver/bronze medals

---

## Testing Workflow

1. **HR Admin**: Login → Create a Job Post with required skills
2. **Candidate**: Register → Upload PDF resume → Apply for job
3. **AI Analysis**: Runs automatically on apply
4. **HR Admin**: View Rankings → See AI scores → Select/Reject candidates
5. **Reports**: Export PDF / Excel from Reports page
