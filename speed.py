"""
Fill the TASKY database with demo data.
⚠️ Deletes ALL existing users and tasks first!

Run from the project folder:  python3 seed.py
"""
import random
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from app import app, db, Users, Tasks

PASSWORD = "password123"   # same password for every demo account

USERS = [
    ("Maya Chen", "maya.chen@tasky.demo"),
    ("Lucas Romano", "lucas.romano@tasky.demo"),
    ("Sara Novak", "sara.novak@tasky.demo"),
    ("Daniel Weber", "daniel.weber@tasky.demo"),
    ("Elena Costa", "elena.costa@tasky.demo"),
]

TITLES = [
    "Prepare Q4 budget", "Update client contracts", "Fix login page bug",
    "Write onboarding guide", "Review supplier invoices", "Plan team offsite",
    "Clean up CRM data", "Design new landing page", "Monthly sales report",
    "Renew software licenses", "Prepare board presentation", "Test payment flow",
    "Organise training session", "Migrate files to cloud", "Update price list",
    "Call new leads", "Reconcile bank statements", "Draft newsletter",
    "Set up new laptops", "Review marketing budget", "Write API documentation",
    "Audit user permissions", "Prepare tax documents", "Update company website",
    "Collect customer feedback", "Plan product launch", "Check inventory levels",
    "Create social media posts", "Review job applications", "Backup database",
    "Optimise report queries", "Translate user manual", "Book conference room",
    "Follow up overdue payments", "Update team calendar", "Prepare KPI dashboard",
    "Negotiate supplier discount", "Fix mobile layout", "Write case study",
    "Archive old projects", "Schedule client demo", "Update security policy",
    "Analyse churn data", "Prepare quarterly review", "Refactor export feature",
    "Send meeting minutes", "Update FAQ page", "Order office supplies",
    "Review expense claims", "Plan next sprint",
]

DESCRIPTIONS = [
    "Coordinate with the team and share a first draft.",
    "Check the details and update the shared folder.",
    "Needs approval from the manager before Friday.",
    "Keep it short, one page is enough.",
    "Follow the checklist from last month.",
    "",
]

with app.app_context():
    # 1. wipe everything (tasks first, they point to users)
    db.session.execute(db.delete(Tasks))
    db.session.execute(db.delete(Users))
    db.session.commit()

    hashed = generate_password_hash(PASSWORD, method="pbkdf2:sha256", salt_length=8)

    # 2. one manager + 5 team members
    manager = Users(name="Alex Morgan", email="manager@tasky.demo",
                    password=hashed, is_manager=True)
    db.session.add(manager)

    team = []
    for name, email in USERS:
        user = Users(name=name, email=email, password=hashed)
        db.session.add(user)
        team.append(user)
    db.session.commit()

    # 3. 50 tasks with random owner, priority, status and due date
    today = date.today()
    for title in TITLES:
        status = random.choices(["todo", "inprogress", "done"], weights=[4, 3, 3])[0]

        if random.random() < 0.1:
            due = None                                            # ~10% without a date
        else:
            due = today + timedelta(days=random.randint(-10, 30))  # some are overdue

        db.session.add(Tasks(
            title=title,
            description=random.choice(DESCRIPTIONS),
            priority=random.choice(["low", "medium", "high"]),
            status=status,
            due_date=due,
            user_id=random.choice(team).id,
        ))
    db.session.commit()

    print(f"✅ Created 1 manager, {len(team)} users and {len(TITLES)} tasks")
    print(f"🔑 Log in with any email above, password: {PASSWORD}")
    print("👔 Manager: manager@tasky.demo")