"""
AI Resume Parser Module
Extracts text, skills, contact info, education and experience from PDF resumes.
Uses pypdf for text extraction and regex-based pattern matching for all
field extraction and skill/matching logic below.
"""

import os
import re
import json
import logging

logger = logging.getLogger(__name__)

# ---------- SKILLS DATABASE ----------
SKILLS_DATABASE = [
    # Programming Languages
    'python', 'java', 'javascript', 'typescript', 'c', 'c++', 'c#', 'php', 'ruby',
    'swift', 'kotlin', 'go', 'rust', 'scala', 'r', 'matlab', 'perl', 'bash', 'shell',

    # Web Technologies
    'html', 'css', 'html5', 'css3', 'bootstrap', 'tailwind', 'sass', 'less',
    'react', 'reactjs', 'angular', 'angularjs', 'vue', 'vuejs', 'jquery',
    'nodejs', 'node.js', 'expressjs', 'express', 'nextjs', 'nuxtjs',

    # Backend Frameworks
    'django', 'flask', 'fastapi', 'spring', 'spring boot', 'laravel', 'rails',
    'asp.net', 'dotnet', '.net',

    # Databases
    'sql', 'mysql', 'postgresql', 'sqlite', 'mongodb', 'redis', 'elasticsearch',
    'oracle', 'mssql', 'cassandra', 'firebase', 'dynamodb',

    # AI/ML
    'machine learning', 'deep learning', 'data science', 'artificial intelligence',
    'natural language processing', 'nlp', 'computer vision', 'tensorflow', 'pytorch',
    'keras', 'scikit-learn', 'sklearn', 'pandas', 'numpy', 'matplotlib', 'seaborn',
    'opencv', 'nltk', 'spacy', 'huggingface', 'transformers',

    # Cloud & DevOps
    'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'jenkins',
    'ci/cd', 'ansible', 'terraform', 'linux', 'unix', 'nginx', 'apache',

    # Version Control & Tools
    'git', 'github', 'gitlab', 'bitbucket', 'jira', 'confluence', 'agile', 'scrum',

    # Mobile
    'android', 'ios', 'react native', 'flutter', 'xamarin',

    # Data & Analytics
    'tableau', 'power bi', 'excel', 'data analysis', 'data visualization',
    'big data', 'hadoop', 'spark', 'kafka',

    # Security
    'cybersecurity', 'network security', 'ethical hacking', 'penetration testing',
    'owasp',

    # Other
    'api', 'rest api', 'graphql', 'microservices', 'oop', 'mvc', 'design patterns',
    'unit testing', 'selenium', 'postman', 'xml', 'json', 'regex',
]

EDUCATION_KEYWORDS = [
    'b.e', 'b.tech', 'be', 'btech', 'bachelor', 'b.sc', 'bsc', 'b.com', 'bcom',
    'm.tech', 'mtech', 'm.e', 'me', 'master', 'm.sc', 'msc', 'mba',
    'phd', 'ph.d', 'doctorate', '10th', '12th', 'ssc', 'hsc', 'diploma',
    'university', 'college', 'institute', 'school', 'engineering', 'science',
    'computer science', 'information technology', 'it', 'electronics',
]

EXPERIENCE_KEYWORDS = [
    'experience', 'work', 'worked', 'internship', 'intern', 'project',
    'developer', 'engineer', 'analyst', 'manager', 'lead', 'senior', 'junior',
    'trainee', 'assistant', 'associate', 'consultant',
]

# ---------- SKILL ALIASES ----------
# Maps common variants/abbreviations to the canonical name used in
# SKILLS_DATABASE, so "ReactJS" on a resume matches "react" required by a
# job post, "Node" matches "node.js", etc. This is the main fix for the
# match score staying stuck at 0% even when the candidate clearly has the
# required skills, just spelled slightly differently.
SKILL_ALIASES = {
    'reactjs': 'react', 'react.js': 'react', 'react js': 'react',
    'nodejs': 'node.js', 'node': 'node.js', 'node js': 'node.js',
    'vuejs': 'vue', 'vue.js': 'vue',
    'angularjs': 'angular', 'angular.js': 'angular',
    'expressjs': 'express', 'express.js': 'express',
    'nextjs': 'next.js', 'nuxtjs': 'nuxt.js',
    'py': 'python',
    'js': 'javascript', 'ecmascript': 'javascript',
    'ts': 'typescript',
    'ml': 'machine learning', 'machinelearning': 'machine learning',
    'dl': 'deep learning', 'deeplearning': 'deep learning',
    'ai': 'artificial intelligence',
    'nlp': 'natural language processing',
    'cv': 'computer vision',
    'k8s': 'kubernetes',
    'postgres': 'postgresql', 'psql': 'postgresql',
    'mongo': 'mongodb',
    'html5': 'html', 'css3': 'css',
    'dotnet': '.net', 'asp.net': '.net', 'aspnet': '.net',
    'sklearn': 'scikit-learn',
    'restapi': 'rest api', 'rest': 'rest api', 'restful': 'rest api', 'restful api': 'rest api',
    'cicd': 'ci/cd',
    'reactnative': 'react native',
    'oops': 'oop',
    'gcloud': 'gcp', 'google cloud platform': 'gcp',
    'csharp': 'c#', 'c sharp': 'c#',
    'cpp': 'c++', 'c plus plus': 'c++',
}


def normalize_skill(skill):
    """Normalize a raw skill string to its canonical form for matching."""
    if not skill:
        return ''
    s = re.sub(r'\s+', ' ', skill.strip().lower())
    s = s.rstrip('.')
    return SKILL_ALIASES.get(s, s)


def extract_text_from_pdf(pdf_path):
    """Extract raw text from a PDF file using pypdf (the actively
    maintained successor to PyPDF2). Handles password-protected PDFs
    (empty password) and logs clearly when a PDF has no extractable text
    (e.g. a scanned image with no OCR layer) instead of silently failing.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.error("pypdf is not installed. Run: pip install pypdf")
        return ""

    if not pdf_path or not os.path.isfile(pdf_path):
        logger.error(f"Resume file not found on disk: {pdf_path}")
        return ""

    try:
        text = ""
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            if reader.is_encrypted:
                try:
                    reader.decrypt('')
                except Exception:
                    logger.warning(f"Could not decrypt protected PDF: {pdf_path}")
            for page in reader.pages:
                try:
                    page_text = page.extract_text() or ""
                except Exception as page_err:
                    logger.warning(f"Could not extract a page from {pdf_path}: {page_err}")
                    page_text = ""
                if page_text:
                    text += page_text + "\n"
        text = text.strip()
        if not text:
            logger.warning(
                f"No extractable text in {pdf_path} — likely a scanned/image-only PDF."
            )
        return text
    except Exception as e:
        logger.error(f"PDF extraction error for {pdf_path}: {e}")
        return ""


def extract_name(text):
    """Extract candidate name from resume text."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    # The name is usually in the first few lines, is short, and all alpha
    for line in lines[:5]:
        # Skip lines with email/phone/common headers
        if re.search(r'[@\d\|/\\]', line):
            continue
        if len(line.split()) <= 4 and len(line) <= 50:
            cleaned = re.sub(r'[^a-zA-Z\s\.]', '', line).strip()
            if cleaned and len(cleaned) >= 3:
                return cleaned.title()
    return ""


def extract_email(text):
    """Extract email address from resume text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(pattern, text)
    return matches[0] if matches else ""


def extract_phone(text):
    """Extract phone number from resume text.

    Handles the common formats seen on resumes:
    - +91 98765 43210 (space-separated Indian mobile)
    - +91-9876543210 / +919876543210
    - (123) 456-7890 / 123-456-7890 (US-style)
    - 10-13 plain digits
    """
    patterns = [
        # International w/ country code, groups separated by space/dash/dot,
        # e.g. "+91 98765 43210" or "+1 415-555-0132"
        r'\+\d{1,3}[-.\s]?\d{3,5}[-.\s]?\d{3,5}(?:[-.\s]?\d{2,4})?',
        # US-style with parentheses, e.g. "(123) 456-7890"
        r'\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}',
        # Generic 3-3-4/5 grouping without country code
        r'\b\d{3,5}[-.\s]\d{3,5}[-.\s]\d{3,5}\b',
        # Plain 10-13 contiguous digits
        r'\b\d{10,13}\b',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Clean up stray whitespace and keep it human-readable
            return re.sub(r'\s+', ' ', matches[0].strip())
    return ""


def extract_skills(text):
    """Extract skills from resume text using keyword matching."""
    text_lower = text.lower()
    found_skills = []
    for skill in SKILLS_DATABASE:
        # Use word boundary matching
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill)
    return list(set(found_skills))


def extract_education(text):
    """Extract education information from resume text."""
    lines = text.split('\n')
    education_lines = []
    capture = False

    for line in lines:
        line_lower = line.lower().strip()
        # Check for education section header
        if re.search(r'\b(education|qualification|academic)\b', line_lower):
            capture = True
        elif capture and re.search(r'\b(experience|skills|project|certif|award)\b', line_lower):
            capture = False

        if capture and line.strip():
            education_lines.append(line.strip())

        # Also grab lines mentioning degrees directly
        for keyword in EDUCATION_KEYWORDS:
            if keyword in line_lower and line.strip() not in education_lines:
                education_lines.append(line.strip())
                break

    result = ' | '.join(education_lines[:6])
    return result[:500] if result else "Not found"


def extract_experience(text):
    """Extract work experience information from resume text."""
    lines = text.split('\n')
    experience_lines = []
    capture = False

    for line in lines:
        line_lower = line.lower().strip()
        if re.search(r'\b(experience|work history|employment|internship)\b', line_lower):
            capture = True
        elif capture and re.search(r'\b(education|skills|project|certif|award|language)\b', line_lower):
            capture = False

        if capture and line.strip():
            experience_lines.append(line.strip())

    result = ' | '.join(experience_lines[:8])
    return result[:500] if result else "Fresher / Not specified"


def parse_resume(pdf_path):
    """
    Main function: Parse a PDF resume and return structured data.

    Returns a dict with:
    - name, email, phone
    - education, experience
    - skills (list)
    - raw_text
    """
    raw_text = extract_text_from_pdf(pdf_path)

    if not raw_text:
        return {
            'name': '', 'email': '', 'phone': '',
            'education': '', 'experience': '',
            'skills': [], 'raw_text': '',
        }

    return {
        'name': extract_name(raw_text),
        'email': extract_email(raw_text),
        'phone': extract_phone(raw_text),
        'education': extract_education(raw_text),
        'experience': extract_experience(raw_text),
        'skills': extract_skills(raw_text),
        'raw_text': raw_text,
    }


def calculate_match_score(candidate_skills, required_skills):
    """
    Calculate matching percentage between candidate skills and job required skills.

    Formula: (Matched Skills / Required Skills) * 100

    Skills are compared using normalize_skill() so that common variants
    (ReactJS/React, Node/Node.js, ML/Machine Learning, etc.) are correctly
    recognized as the same skill — this is what keeps the score from
    incorrectly showing 0% when the candidate actually has the skill.

    Returns:
    - score (float): percentage match
    - matched (list): required skills (original casing) that matched
    - missing (list): required skills (original casing) that were not found
    """
    if not required_skills:
        return 0.0, [], []

    candidate_norm = {normalize_skill(s) for s in candidate_skills if s and s.strip()}

    matched = []
    missing = []
    seen = set()
    for raw in required_skills:
        raw_clean = raw.strip()
        if not raw_clean:
            continue
        norm = normalize_skill(raw_clean)
        if norm in seen:
            continue
        seen.add(norm)
        if norm in candidate_norm:
            matched.append(raw_clean)
        else:
            missing.append(raw_clean)

    total = len(matched) + len(missing)
    if total == 0:
        return 0.0, [], []

    score = (len(matched) / total) * 100
    return round(score, 2), matched, missing


def rank_candidates(analyses):
    """
    Rank candidates by their matching score (highest first).

    analyses: list of dicts with keys: candidate_id, score
    Returns: sorted list with rank added
    """
    sorted_analyses = sorted(analyses, key=lambda x: x['score'], reverse=True)
    for i, item in enumerate(sorted_analyses):
        item['rank'] = i + 1
        item['is_recommended'] = i < 3  # Top 3 are recommended
    return sorted_analyses
