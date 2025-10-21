# tests/test_app.py
from main import db, User, Event

def test_home_ok(client):
    res = client.get("/")
    assert res.status_code == 200  # Home route exists
    # The page usually renders something like "Exploring Geography", optionally with an HTML snippet assertion

def test_register_login_logout_flow(client):
    # First access /register GET with the membership parameter (otherwise you will be directed to join_rgsq)
    res = client.get("/register?membership=ordinary")
    assert res.status_code == 200

    # POST registers a normal user (role=member)
    payload = {
        "email": "user@example.com",
        "fullName": "Test User",
        "password": "secret123",
        "membership": "ordinary",
    }
    res = client.post("/register", data=payload, follow_redirects=True)
    assert res.status_code == 200
    # After successful registration, you will be redirected to login and there will be a flash
    assert b"Account created" in res.data

    # Log in
    res = client.post("/Login.html", data={
        "email": "user@example.com",
        "password": "secret123",
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Login successful" in res.data or b"Logged in" in res.data

    # Sign out
    res = client.get("/logout", follow_redirects=True)
    assert res.status_code == 200
    assert b"Logged out" in res.data

def test_admin_pages_require_admin(client):
    # Accessing the admin page without logging in - redirected/rejected
    res = client.get("/RGSQStaff.html", follow_redirects=True)
    assert res.status_code == 200
    # The page should display "Please login first." or a permission-related prompt
    assert b"Please login first" in res.data or b"Insufficient permissions" in res.data

def test_admin_signup_and_access(client):
    # Register as an administrator using the correct invitation code
    res = client.post("/admin/signup", data={
        "code": "TEAM305",
        "email": "admin@example.com",
        "full_name": "Admin",
        "password": "adminpassword",
        "password2": "adminpassword",
    }, follow_redirects=True)
    assert res.status_code == 200
    # After success, you will enter RGSQ Staff
    assert b"Admin account created" in res.data or b"Welcome back" in res.data

    # The admin page is now accessible
    res = client.get("/RGSQStaff.html")
    assert res.status_code == 200

def test_event_crud_core_flow(client):
    # Create an administrator and log in first
    client.post("/admin/signup", data={
        "code": "TEAM305",
        "email": "admin2@example.com",
        "full_name": "Admin2",
        "password": "adminpassword",
        "password2": "adminpassword",
    }, follow_redirects=True)

    # Create an event (Admin)
    res = client.post("/Create.html", data={
        "title": "RGSQ Seminar",
        "event_time": "2025-11-01 18:30",
        "location": "Brisbane",
        "price": "10.5",
        "description": "Test event",
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Event created" in res.data

    # Get an activity ID
    with client.application.app_context():
        ev = Event.query.first()
        assert ev is not None
        ev_id = ev.id

    # Public registration page GET
    res = client.get(f"/events/{ev_id}/register")
    assert res.status_code == 200

    # Registration POST (If the SMTP environment variable is not set, your code will skip sending the email and still return a success/prompt)
    res = client.post(f"/events/{ev_id}/register", data={"email": "user@foo.com"}, follow_redirects=True)
    assert res.status_code == 200
    # Will jump to confirm
    assert b"Registration confirmed" in res.data or b"confirm" in res.data

def test_eventlist_pagination_ok(client):
    # Fill in some activity data
    with client.application.app_context():
        for i in range(8):
            db.session.add(Event(
                title=f"E{i}",
                event_time=f"2025-12-{i+1:02d}",
                location="QLD",
                price=0.0
            ))
        db.session.commit()
    # Page 1
    res = client.get("/Eventlist.html?page=1")
    assert res.status_code == 200
    # Page 2
    res = client.get("/Eventlist.html?page=2")
    assert res.status_code == 200
