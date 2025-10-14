from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import uuid
import smtplib
from email.message import EmailMessage
from werkzeug.utils import secure_filename


app = Flask(__name__)

# Ensure the instance folder exists (Flask writes runtime files here)
os.makedirs(app.instance_path, exist_ok=True)

# Point SQLAlchemy to an absolute path under instance/, avoids "two DB files" confusion
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(app.instance_path, 'events.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

#image upload config
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Keep your secret key as is (change for production)
app.secret_key = "change_me"

db = SQLAlchemy(app)



# -----------------------------
# Models
# -----------------------------
class Event(db.Model):
    __tablename__ = "event"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    event_time = db.Column(db.String(50), nullable=False)  # ISO string or human-readable
    location = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=True)
    image = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    visibility = db.Column(db.String(20), nullable=False, default="public")  # public/private

class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120))
    password_hash = db.Column(db.String(200), nullable=False)
    membership = db.Column(db.String(50))
    # role fields retained for admin/member split
    role = db.Column(db.String(20), nullable=False, default="member")
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw, method="pbkdf2:sha256")

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw or "")
    

# -----------------------------
# Membership levels (for register flow)
# -----------------------------
MEMBERSHIP_LEVELS = {
    "household": {"name": "Household Bundle", "price": "$90.00 (AUD)",
                  "desc": "Bundle (up to 5 members). 1-year subscription; no automatic recurring payments."},
    "ordinary":  {"name": "Ordinary Member", "price": "$70.00 (AUD)",
                  "desc": "1-year subscription; no automatic recurring payments."},
    "school":    {"name": "School/Educational Institution", "price": "$85.00 (AUD)",
                  "desc": "1-year subscription; one voting representative."},
    "student":   {"name": "Student", "price": "",
                  "desc": "1-year subscription; full-time students in Australia."},
    "under35":   {"name": "Under 35s", "price": "$35.00 (AUD)",
                  "desc": "1-year subscription; same voting rights as ordinary members."},
    "youth":     {"name": "Youth", "price": "",
                  "desc": "1-year subscription; under 18s require parental consent."},
}


# -----------------------------
# Lightweight migrations
# -----------------------------
def migrate_event_table():
    with db.engine.begin() as conn:
        cols = conn.exec_driver_sql("PRAGMA table_info(event);").fetchall()
        names = [c[1] for c in cols]
        if "event_time" not in names:
            conn.exec_driver_sql("ALTER TABLE event ADD COLUMN event_time TEXT;")
            if "date" in names:
                conn.exec_driver_sql("UPDATE event SET event_time = date;")

def migrate_event_visibility():
    with db.engine.begin() as conn:
        cols = conn.exec_driver_sql("PRAGMA table_info(event);").fetchall()
        names = [c[1] for c in cols]
        if "visibility" not in names:
            conn.exec_driver_sql("ALTER TABLE event ADD COLUMN visibility TEXT DEFAULT 'public';")
        

def migrate_user_table():
    with db.engine.begin() as conn:
        cols = conn.exec_driver_sql("PRAGMA table_info(user);").fetchall()
        names = [c[1] for c in cols]
        if "role" not in names:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN role TEXT DEFAULT 'member';")
        if "is_active" not in names:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN is_active INTEGER DEFAULT 1;")

with app.app_context():
    db.create_all()
    migrate_event_table()
    migrate_user_table()
    migrate_event_visibility()

# -----------------------------
# Template globals
# -----------------------------
@app.context_processor
def inject_user_flags():
    name = None
    is_admin = False
    uid = session.get("user_id")
    if uid:
        u = User.query.get(uid)
        if u:
            name = (u.full_name or "").strip() or u.email.split("@")[0]
            is_admin = (u.role or "member").lower() in ("admin", "staff")
    return {"current_user_name": name, "is_admin": is_admin}

# ------------------------------
# Auth helers
# ------------------------------
def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)

def is_member_user():
    u = get_current_user()
    if not u:
        return False
    role = (u.role or "").lower()
    return role in ("member", "admin", "staff")
# -----------------------------
# Email helpers (optional)
# -----------------------------
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
FROM_EMAIL = os.environ.get("FROM_EMAIL", SMTP_USER or "no-reply@rgsq.org")

def send_welcome_email(to_email: str, level_name: str):
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        print("SMTP not configured, skipping welcome email.")
        return False
    msg = EmailMessage()
    msg["Subject"] = "Welcome to RGSQ"
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.set_content(f"Welcome to RGSQ!\n\nMembership: {level_name}\n")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        print(f"Sent welcome email to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
    return False

def send_event_registration_email(to_email: str, ev: Event):
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        print("[MAIL] SMTP not configured: missing SMTP_HOST/SMTP_USER/SMTP_PASS")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Event registration confirmed: {ev.title}"
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email

    body_lines = [
        "Thank you for registering!",
        "",
        f"Event: {ev.title}",
        f"Time:  {ev.event_time}",
        f"Place: {ev.location}",
    ]
    if ev.price is not None:
        body_lines.append(f"Price: ${ev.price:.2f}")
    if ev.description:
        body_lines += ["", "Details:", ev.description]

    msg.set_content("\n".join(body_lines))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        print(f"[MAIL] Event registration email sent to {to_email} for event #{ev.id}")
        return True
    except Exception as e:
        print(f"[MAIL][ERROR] Failed to send event registration email to {to_email}: {e}")
        return False

# -----------------------------
# Home / Events (public)
# -----------------------------
@app.route("/")
def Home():
    base_q = Event.query
    if not is_member_user():
        base_q = base_q.filter(Event.visibility == "public")
    events = base_q.order_by(Event.event_time.asc()).limit(4).all()
    return render_template("homepage.html", events=events, upcoming_events=events)

@app.route("/Eventlist.html")
def Eventlist():
    page = request.args.get("page", 1, type=int)
    per_page = 6
    base_q = Event.query
    if not is_member_user():
        base_q = base_q.filter(Event.visibility == "public")
    base_q = base_q.order_by(Event.event_time.asc())
    pagination = base_q.paginate(page=page, per_page=per_page, error_out=False)
    events = pagination.items
    return render_template("Eventlist.html", events=events, pagination=pagination)

# -----------------------------
# Auth (member)
# -----------------------------
@app.route("/Login.html", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "")
        u = User.query.filter_by(email=email).first()
        if u and u.check_password(password):
            session["user_id"] = u.id
            session["user_email"] = u.email
            flash("Login successful.", "success")
            return redirect(url_for("Home"))
        flash("Invalid email or password.", "danger")
    return render_template("Login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("Home"))


@app.route("/register", methods=["GET", "POST"])
def register_account():
    # GET: arrived from Join page with ?membership=xxx
    if request.method == "GET":
        level_key = (request.args.get("membership") or "").strip().lower()
        if level_key not in MEMBERSHIP_LEVELS:
            flash("Please select a membership level first.", "warning")
            return redirect(url_for("join_rgsq"))
        return render_template("register.html", level_key=level_key, level=MEMBERSHIP_LEVELS[level_key])

    # POST: create account
    email = (request.form.get("email") or "").strip().lower()
    # accept both "fullName" (template default) and "fullname" (fallback)
    fullname = (request.form.get("fullName") or request.form.get("fullname") or "").strip()
    password = (request.form.get("password") or "")
    membership = (request.form.get("membership") or "").strip().lower()

    # basic validation
    if not email or "@" not in email:
        flash("Please enter a valid email.", "warning")
        level = MEMBERSHIP_LEVELS.get(membership)
        return render_template("register.html", level_key=membership, level=level)

    if len(password) < 6:
        flash("Password must be at least 6 characters.", "warning")
        level = MEMBERSHIP_LEVELS.get(membership)
        return render_template("register.html", level_key=membership, level=level)

    if User.query.filter_by(email=email).first():
        flash("This email is already registered.", "warning")
        level = MEMBERSHIP_LEVELS.get(membership)
        return render_template("register.html", level_key=membership, level=level)

    # create user with selected membership
    u = User(
        email=email,
        full_name=fullname or None,
        membership=membership if membership in MEMBERSHIP_LEVELS else None
    )
    u.set_password(password)
    u.role = "member"   # ensure public signups are members
    u.is_active = True

    db.session.add(u)
    db.session.commit()

    # optional welcome email
    sent = False
    try:
        display_name = MEMBERSHIP_LEVELS.get(membership, {}).get("name", "member")
        sent = send_welcome_email(u.email, display_name)
    except Exception:
        sent = False

    if sent:
        flash("Account created. Welcome email sent.", "success")
    else:
        flash("Account created. Could not send welcome email.", "warning")

    return redirect(url_for("Home"))


# -----------------------------
# Admin Center (signup/login)
# -----------------------------
ADMIN_INVITE_CODE = "TEAM305"

@app.route("/admin/signup", methods=["GET", "POST"])
def admin_signup():
    active_tab = request.args.get("tab")
    if request.method == "POST":
        code = (request.form.get("code") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        full_name = (request.form.get("full_name") or "").strip()
        password = (request.form.get("password") or "")
        password2 = (request.form.get("password2") or "")
        if code != ADMIN_INVITE_CODE:
            flash("Invalid invite code.", "danger")
            return render_template("admin_signup.html", active_tab="signup")
        if not email or "@" not in email:
            flash("Please enter a valid email.", "warning")
            return render_template("admin_signup.html", active_tab="signup")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "warning")
            return render_template("admin_signup.html", active_tab="signup")
        if password != password2:
            flash("Passwords do not match.", "warning")
            return render_template("admin_signup.html", active_tab="signup")
        if User.query.filter_by(email=email).first():
            flash("This email is already registered.", "warning")
            return render_template("admin_signup.html", active_tab="signup")
        u = User(email=email, full_name=full_name or None)
        u.set_password(password)
        u.role = "admin"
        u.is_active = True
        db.session.add(u)
        db.session.commit()
        session["user_id"] = u.id
        session["user_email"] = u.email
        flash("Admin account created.", "success")
        return redirect(url_for("rgsq_staff_html"))
    return render_template("admin_signup.html", active_tab=active_tab or "signup")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "")
        u = User.query.filter_by(email=email).first()
        if not u or not u.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("admin_signup.html", active_tab="login")
        if (u.role or "member").lower() not in ("admin", "staff"):
            flash("You do not have admin access.", "danger")
            return render_template("admin_signup.html", active_tab="login")
        if not u.is_active:
            flash("This account is disabled.", "warning")
            return render_template("admin_signup.html", active_tab="login")
        session["user_id"] = u.id
        session["user_email"] = u.email
        flash("Welcome back.", "success")
        return redirect(url_for("rgsq_staff_html"))
    return render_template("admin_signup.html", active_tab="login")

# -----------------------------
# Admin-only pages / Event admin
# -----------------------------
from auth_helpers import admin_required

@app.route("/event_management.html")
@admin_required
def event_management():
    page = request.args.get("page", 1, type=int)
    per_page = 30

    base_q = Event.query.order_by(Event.event_time.desc())
    total_count = base_q.count()
    pagination = base_q.paginate(page=page, per_page=per_page, error_out=False)
    events = pagination.items

    return render_template(
        'event_management.html', 
        events=events, 
        pagination=pagination, 
        total_count=total_count
    )

@app.post("/events/<int:event_id>/delete")
@admin_required
def delete_event(event_id):
    ev = Event.query.get_or_404(event_id)
    db.session.delete(ev)
    db.session.commit()
    flash("Event deleted.", "success")
    return redirect(url_for("event_management"))

@app.route("/Create.html", methods=["GET", "POST"])
@admin_required
def Create():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        event_time = (request.form.get("event_time") or request.form.get("date") or "").strip()
        location = (request.form.get("location") or "").strip()
        price_raw = (request.form.get("price") or "").strip()
        description = (request.form.get("description") or "").strip()
        raw_vis = (request.form.get("visibility") or "").strip().lower()

        image_rel_path = None
        file = request.files.get("image")
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("Image upload not supported yet.", "warning")
                return redirect(request.url)
            
            original_name = secure_filename(file.filename)
            ext = os.path.splitext(original_name)[1].lower()
            unique_name = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file.save(save_path)
            image_rel_path = f"uploads/{unique_name}"
        


        if raw_vis in ("member-only", "member only", "member", "members", "private"):
            visibility = "member"
        elif raw_vis in ("public", "everyone", "all", "anyone", "public user"):
            visibility = "public"
        else:
            visibility = raw_vis if raw_vis in ("public", "member") else "public"

        if not title or not event_time or not location:
            flash("Title, Date and Location are required.", "warning")
            return render_template("Create.html")

        try:
            price = float(price_raw) if price_raw else None
        except ValueError:
            flash("Price must be a number.", "warning")
            return render_template("Create.html")
        
    

        evt = Event(title=title, 
                    event_time=event_time, 
                    location=location,
                    price=price, 
                    description=description or None,
                    visibility=visibility,
                    image=image_rel_path
                    )
        
        db.session.add(evt)
        db.session.commit()
        flash("Event created.", "success")
        return redirect(url_for("event_management"))
    return render_template("Create.html")

# -----------------------------
# Event register (explicit endpoints)
# -----------------------------
@app.route("/events/<int:event_id>/register", methods=["GET", "POST"], endpoint="register_event")
def register_event(event_id: int):
    ev = Event.query.get_or_404(event_id)
    event = {
        "id": ev.id,
        "title": ev.title,
        "date": ev.event_time,
        "location": ev.location,
        "price": f"${ev.price:.2f}" if ev.price is not None else "",
    }
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        if not email:
            flash("Email is required.", "warning")
            return render_template("event_register.html", event=event)
        session["last_event_email"] = email
        return redirect(url_for("register_event_confirm", event_id=event_id))
    return render_template("event_register.html", event=event)

@app.route("/events/<int:event_id>/register/confirm", endpoint="register_event_confirm")
def register_event_confirm(event_id: int):
    ev = Event.query.get_or_404(event_id)
    event = {
        "id": ev.id,
        "title": ev.title,
        "date": ev.event_time,
        "location": ev.location,
        "price": f"${ev.price:.2f}" if ev.price is not None else "",
    }
    email = session.pop("last_event_email", None)
    if email:
        sent = send_event_registration_email(email, ev)
        if sent:
            flash("Registration confirmed. A confirmation email has been sent.", "success")
        else:
            flash("Registration confirmed. Could not send confirmation email.", "warning")
    else:
        flash("No email provided. Registration not confirmed.", "warning")
    return render_template("event_register_confirm.html", event=event, email=email)

# Backward compatible alias (old links)
@app.route("/event_register/<int:event_id>", methods=["GET", "POST"])
def register_event_legacy(event_id: int):
    return register_event(event_id)

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    if event.visibility == "member" and not is_member_user():
        flash("This event is for members only. Please log in.", "warning")
        return redirect(url_for("login"))
    return render_template('event_detail.html', event=event, ev=event)


# -----------------------------
# Staff pages (admin only)
# -----------------------------
@app.route("/RGSQStaff.html")
@admin_required
def rgsq_staff_html():
    return render_template("RGSQStaff.html")

@app.route("/StaffMembersOverview.html")
@admin_required
def staff_members_overview():
    return render_template("StaffMembersOverview.html")

@app.route("/StaffMembersList.html")
@admin_required
def staff_members_list():
    return render_template("StaffMembersList.html")

@app.route('/StaffMembersCount.html')
def staff_members_count():
    return render_template('StaffMembersCount.html')

# -----------------------------
# Static content pages (restored for navbar links)
# -----------------------------
@app.route("/Memberbenefits.html")
def Memberbenefits():
    return render_template("Memberbenefits.html")

@app.route("/JoinRGSQ.html", endpoint="join_rgsq")
def JoinRGSQ():
    return render_template("JoinRGSQ.html")

@app.route("/join", methods=["GET"])
def join_page():
    membership = request.args.get("membership")
    return render_template("JoinRGSQ.html", membership=membership)

@app.route("/Aboutsociety.html")
def Aboutsociety():
    return render_template("Aboutsociety.html")

@app.route("/Contact.html")
def contact():
    return render_template("Contact.html")

@app.route("/Forgotpassword.html")
def forgot_password():
    return render_template("Forgotpassword.html")

@app.route("/Library.html")
def library():
    return render_template("Library.html")

@app.route("/Venuehire.html")
def venue_hire():
    return render_template("Venuehire.html")

@app.route("/Bulletin.html")
def bulletin():
    return render_template("Bulletin.html")

@app.route("/Geographywebsite.html")
def geography_website():
    return render_template("Geographywebsite.html")

# route with spaces kept to match template filename
@app.route("/Museums and other attractions.html")
def Museums_and_other_attractions():
    return render_template("Museums and other attractions.html")

@app.route("/MapResources.html")
def MapResources():
    return render_template("MapResources.html")

@app.route("/PhilateliesCover.html")
def PhilateliesCover():
    return render_template("PhilateliesCover.html")

@app.route("/Disclaimer.html")
def Disclaimer():
    return render_template("Disclaimer.html")

@app.route("/Committees.html")
def committees_html():
    return render_template("Committees.html")

@app.route("/Governance.html")
def governance_html():
    return render_template("Governance.html")

@app.route("/Honoursboard.html")
def honours_board():
    return render_template("Honoursboard.html")

@app.route("/Donate.html")
def donate():
    return render_template("Donate.html")

@app.route("/AustraliaGeographyCompetitions.html")
def australia_geography_competitions():
    return render_template("AustraliaGeographyCompetitions.html")

@app.route("/Lambertcenter.html")
def lambert_center():
    return render_template("Lambertcenter.html")

@app.route("/Queenslandbydegrees.html")
def queensland_by_degrees():
    return render_template("Queenslandbydegrees.html")

# Society / News (list + details)
@app.route("/SocietyNews.html")
def SocietyNews():
    return render_template("SocietyNews.html")

@app.route("/SocietyNews_2025_writing_comp.html")
def SocietyNews_2025_writing_comp():
    return render_template("SocietyNews_2025_writing_comp.html")

@app.route("/SocietyNews_2025_tsunami_boulder.html")
def SocietyNews_2025_tsunami_boulder():
    return render_template("SocietyNews_2025_tsunami_boulder.html")

@app.route("/SocietyNews_2024_gbwo.html")
def SocietyNews_2024_gbwo():
    return render_template("SocietyNews_2024_gbwo.html")

@app.route("/SocietyNews_2024_souvenir_exhibition.html")
def SocietyNews_2024_souvenir_exhibition():
    return render_template("SocietyNews_2024_souvenir_exhibition.html")

# Awards & Grants
@app.route("/AwardsPrizes.html")
def AwardsPrizes():
    return render_template("AwardsPrizes.html")

@app.route("/StudentResearchGrants.html")
def StudentResearchGrants():
    return render_template("StudentResearchGrants.html")

# -----------------------------
# Blueprint registration
# -----------------------------
from admin import admin_bp
app.register_blueprint(admin_bp)

if __name__ == "__main__":
    app.run(debug=True)



