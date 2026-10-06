"""Create demo driver and admin accounts (students sign up in the app).

    python seed.py
Change these passwords before showing anyone a deployed version.
"""
from app import db
from app.security import hash_password

DEMO = [
    ("driver@nsu.edu", "Demo Driver", "D0001", "driverpass123", "driver"),
    ("admin@nsu.edu", "Demo Admin", "A0001", "adminpass123", "admin"),
]

db.init()
with db.connect() as c:
    for email, name, sid, pw, role in DEMO:
        if not c.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            c.execute(
                "INSERT INTO users (email, name, student_id, password_hash, role, created_at) VALUES (?,?,?,?,?,?)",
                (email, name, sid, hash_password(pw), role, db.now_iso()),
            )
            print(f"created {role}: {email} / {pw}")
        else:
            print(f"exists: {email}")
