# ApplicationTracker  
*A calm, personal way to track your job search.*

ApplicationTracker is a lightweight Streamlit app that helps you log your job applications, track follow-ups and outcomes, and actually see your progress, all without spreadsheets, scattered bookmarks, or trying to remember whether you already applied somewhere.

## Features
### Clean Application Logging
Store all key details in one place:

- Company & role
- Salary range
- Job posting link
- Short description or highlights
- Notes & red flags
- Follow-up reminders
- Status (Applied > Screens > Interviews > Offer > etc.)
- Screenshot attachments of job postings

Everything is saved locally using SQLite, nothing leaves your machine.


### Visual Insights

Built-in visualizations give you perspective at a glance:

- Total applications
- Unique companies
- Applications submitted in the last 30 days
- Cumulative applications over time
- Applications by location type (Remote/Hybrid/Onsite)

These charts help you see real patterns and momentum.

### Sankey Diagram

A Sankey diagram visualizes how your applications flow from Applied into different outcomes:

- Recruiter Screens
- Interviews
- Offers
- Rejections
- Ghosted

This gives you a big-picture view of how your search is progressing.

### Powerful Filtering

Filter your applications by:

- Status
- Location type
- Free-text search (company, role, notes)

### Local-First

All data is stored locally in the `data/` directory using SQLite.  
No accounts. No sync. No tracking.