"""
Email notifications via Gmail SMTP.
Uses your existing Gmail app password — no third-party service needed.
"""
import smtplib
import structlog
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import get_settings
from app.db.queries import get_dashboard_stats, get_matches

logger = structlog.get_logger()


def _send_email(to: str, subject: str, html: str):
    s = get_settings()
    if not s.gmail_address or not s.gmail_app_password:
        logger.warning("gmail_not_configured")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = s.gmail_address
        msg["To"]      = to
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(s.gmail_address, s.gmail_app_password)
            server.sendmail(s.gmail_address, to, msg.as_string())

        logger.info("email_sent", to=to, subject=subject)
    except Exception as e:
        logger.error("email_failed", subject=subject, error=str(e))


def notify_high_match(to: str, job: dict, score: float):
    _send_email(
        to,
        f"New {score:.0f}% match: {job['title']} at {job['company']}",
        f"""
        <h2>New High-Match Job Found!</h2>
        <p><b>Role:</b> {job['title']}</p>
        <p><b>Company:</b> {job['company']}</p>
        <p><b>Location:</b> {job.get('location', 'Unknown')}</p>
        <p><b>Match Score:</b> {score:.0f}%</p>
        <p><b>Visa Sponsorship:</b> {job.get('visa_sponsorship', 'UNKNOWN')}</p>
        <p><a href="{job['url']}">View Job Posting</a></p>
        """,
    )


def notify_approval_required(to: str, request: dict):
    questions_html = "".join(
        f"<li><b>Q:</b> {q['question']}<br><i>Recommended: {q.get('recommended', 'N/A')}</i></li>"
        for q in request.get("questions", [])
    )
    _send_email(
        to,
        f"Action Required: {request['role']} at {request['company']}",
        f"""
        <h2>Your Input Is Required</h2>
        <p><b>Company:</b> {request['company']}</p>
        <p><b>Role:</b> {request['role']}</p>
        <p><b>Country:</b> {request.get('country', 'Unknown')}</p>
        <p><b>Match Score:</b> {request.get('match_score', 0):.0f}%</p>
        <p><a href="{request['job_url']}">View Job Posting</a></p>
        <h3>Questions requiring your response:</h3>
        <ul>{questions_html}</ul>
        """,
    )


def notify_interview_request(to: str, details: dict):
    _send_email(
        to,
        f"Interview Request: {details.get('role')} at {details.get('company')}",
        f"""
        <h2>Interview Request Received!</h2>
        <p><b>Company:</b> {details.get('company')}</p>
        <p><b>Role:</b> {details.get('role')}</p>
        <p><b>Recruiter:</b> {details.get('recruiter_name', 'Unknown')}</p>
        <p><b>Interview Type:</b> {details.get('interview_type', 'Unknown')}</p>
        <p><b>Proposed Times:</b><br>{details.get('proposed_times', 'See original message')}</p>
        """,
    )


def send_daily_summary(to: str, user_id: str):
    from datetime import date
    stats      = get_dashboard_stats(user_id)
    top_matches = get_matches(user_id, level="HIGH_MATCH", limit=5)

    top_html = "".join(
        f"<li>{m['ja_jobs']['title']} — {m['ja_jobs'].get('company')} — {m['overall_score']:.0f}% match</li>"
        for m in top_matches if m.get("ja_jobs")
    )

    _send_email(
        to,
        f"Job Search Summary — {date.today()}",
        f"""
        <h2>Job Search Daily Summary — {date.today()}</h2>
        <table cellpadding="6">
            <tr><td>Jobs discovered:</td><td><b>{stats['total_jobs_discovered']}</b></td></tr>
            <tr><td>Jobs evaluated:</td><td><b>{stats['jobs_evaluated']}</b></td></tr>
            <tr><td>High-match jobs:</td><td><b>{stats['high_match_jobs']}</b></td></tr>
            <tr><td>Applications submitted:</td><td><b>{stats['applications_submitted']}</b></td></tr>
            <tr><td>Pending your approval:</td><td><b>{stats['pending_approval']}</b></td></tr>
            <tr><td>Recruiter responses:</td><td><b>{stats['recruiter_responses']}</b></td></tr>
            <tr><td>Interviews:</td><td><b>{stats['interviews']}</b></td></tr>
        </table>
        <h3>Top New Opportunities:</h3>
        <ul>{top_html or '<li>None today</li>'}</ul>
        """,
    )
