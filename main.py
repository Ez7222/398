
from flask import Flask, render_template,request,redirect,url_for,flash,abort,session
from flask_sqlalchemy import SQLAlchemy
import sqlite3
import os
import smtplib
from email.message import EmailMessage
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from datetime import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.secret_key = 'change_me'
UPLOAD_FOLDER = os.path.join('static','uploads')
os.makedirs(UPLOAD_FOLDER,exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif','webp'}

def allowed_file(filename:str)->bool:
    return "." in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS




class Event(db.Model):
    __tablename__ = "event"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    event_time = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)

class User(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(120),unique = True, nullable = False)
    full_name = db.Column(db.String(120))
    password_hash = db.Column(db.String(200),nullable = False)
    membership = db.Column(db.String(50))

    def set_password(self,raw_pwd:str):
        self.password_hash = generate_password_hash(raw_pwd, method="pbkdf2:sha256")
    
    def check_password(self,password):
        return check_password_hash(self.password_hash,password)

def migrate_event_table():
    with db.engine.begin() as conn:
        cols = conn.exec_driver_sql("PRAGMA table_info(event);").fetchall()
        col_names = [c[1] for c in cols]
        if 'event_time' not in col_names:
            conn.exec_driver_sql("ALTER TABLE event ADD COLUMN event_time TEXT;")
            if 'date' in col_names:
                conn.exec_driver_sql("UPDATE event SET event_time = date;")

with app.app_context():
    db.create_all()
    migrate_event_table()



@app.context_processor
def inject_current_user_name():
    """ Injects the variable current_user_name into all templates"""
    name = None
    try:
        uid = session.get('user_id')
        if uid:
            u = User.query.get(uid)
            if u:
                name = (u.full_name or '').strip()or (u.email.split('@')[0] if u.email else None)
    except Exception:
        name = None
    return {'current_user_name':name}


    



# display the homepage
@app.route('/')
def Home():
    from datetime import datetime
    now_iso = datetime.now().isoformat(timespec='minutes')
    upcoming = Event.query.filter(Event.event_time >= now_iso).order_by(Event.event_time.asc()).limit(4).all()
    return render_template('homepage.html',upcoming_events=upcoming)

# display the event list
@app.route('/Eventlist.html')
def Eventlist():
    per_page = 6
    page = request.args.get('page',1,type=int)
    q = Event.query.order_by(Event.event_time.asc())
    total = q.count()
    events_paginated = q.offset((page-1) * per_page).limit(per_page).all()
    total_pages = (total + per_page -1)//per_page
    return render_template('Eventlist.html',events=events_paginated, page=page, total_pages=total_pages)
    
# display the create event page.
@app.route('/Create.html', methods = ['GET', 'POST'])
def Create():
    if request.method == 'POST':
        title = (request.form.get('title')or '').strip()
        event_time = (request.form.get('event_time')or request.form.get('date') or '').strip()
        location = (request.form.get('location')or '').strip()
        price_raw = (request.form.get('price')or '').strip()
        description = (request.form.get('description')or '').strip()

        if not title or not event_time or not location or not price_raw:
            flash("Title, Date, Location and Price are required.","danger")
            return redirect(url_for('Create'))
        try:
            price_val = float(price_raw)
        except ValueError:
            flash("Price must be a number.","danger")
            return redirect(url_for('Create'))
        
        image_rel = None
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            ext = file.filename.rsplit('.',1)[1].lower()
            from datetime import datetime
            safe_name = f"{int(datetime.now().timestamp())}_{title.replace(' ','_')}.{ext}" 
            save_path = os.path.join(app.config['UPLOAD_FOLDER'],safe_name) 
            file.save(save_path)
            image_rel = f"uploads/{safe_name}"
            

        evt = Event(
            title = title,
            event_time = event_time,
            location = location,
            price = price_val,
            image = image_rel,
            description = description or None
        )
        
        db.session.add(evt)
        db.session.commit()
        flash("Event created successfully.","success")
        return redirect(url_for('Eventlist'))
    return render_template('Create.html')
            
                        
            

# handle the creation of a new event.
def get_events():
    conn = sqlite3.connect('rgsq.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM event")
    events = cursor.fetchall()
    conn.close()
    return events

# showing the member benefits page.
@app.route('/Memberbenefits.html')
def Memberbenefits():
    return render_template('Memberbenefits.html')

# shwoing the join RGSQ page.
@app.route('/JoinRGSQ.html')
def join_rgsq():
    return render_template('JoinRGSQ.html')

# choosing the level of membership page.
@app.route("/join", methods = ["GET"])
def join_page():
    return render_template('JoinRGSQ.html')

LEVELS = {
    "household": {"key": "household", "name": "Household Bundle", "price": "$90.00 (AUD)",
                  "desc": "Bundle (up to 5 members) · Subscription: 1 year · No automatically recurring payments."},
    "ordinary":  {"key": "ordinary",  "name": "Ordinary Member", "price": "$70.00 (AUD)",
                  "desc": "Subscription: 1 year · No automatically recurring payments."},
    "school":    {"key": "school",    "name": "School/Educational Institution", "price": "$85.00 (AUD)",
                  "desc": "Subscription: 1 year · No automatically recurring payments."},
    "student":   {"key": "student",   "name": "Student", "price": "N/A",
                  "desc": "Subscription: 1 year · No automatically recurring payments."},
    "under35":   {"key": "under35",   "name": "Under 35s", "price": "$35.00 (AUD)",
                  "desc": "Subscription: 1 year · No automatically recurring payments."},
    "youth":     {"key": "youth",     "name": "Youth", "price": "N/A",
                  "desc": "Subscription: 1 year · No automatically recurring payments."},
}

SMTP_HOST = os.environ.get("SMTP_HOST","smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT","587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
FROM_EMAIL = os.environ.get("FROM_EMAIL",SMTP_USER or "no-reply@RGSQ.org")

def send_welcome_email(to_email: str, level:dict):
    """Send a welcome email to the new member."""
    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and FROM_EMAIL):
        print("SMTP settings are not configured. Skipping email sending.")
        return
    meg = EmailMessage()
    meg ["Subject"] = "Welcome to RGSQ"
    meg ["From"] = FROM_EMAIL
    meg ["To"] = to_email

    body = f""" Hi there,
Welcome to the Royal Geographical Society of Queensland (RGSQ)! Thanks for creating an account.

Selected level: {level['name']} 

Selected price:({level['price']})

Details: {level['desc']}

We are excited to have you as a member of our community. 
If you have any questions or need assistance, feel free to reach out to us.
    
Best regards,
RGSQ Team
"""
    meg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER,SMTP_PASS)
            server.send_message(meg)
            print(f"[OK] Welcome email sent to {to_email}")
    except Exception as e:
        print(f"[ERR] Failed to send email to {to_email}: {e}")


def send_event_confirmation_email(to_email:str,event:dict):
    """
    Send a confirmation email after user successfully registers for an event
    """
    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and FROM_EMAIL):
        print("SMTP settings are not configured. Skipping email sending")
        return
    
    meg = EmailMessage()
    meg ["Subject"] = f"Confirmation: {event['title']}"
    meg ["From"]=FROM_EMAIL
    meg ["To"] = to_email

    body = f""" Dear Participant,

Thanks you for registering for the event: {event['title']}.

Event Details:
Title: {event['title']}
Date: {event['date']}
Location: {event ['location']}
Price: {event ['price']}

We look forward to seeing you there !

Best regards.
RGSQ Team
"""
    meg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER,SMTP_PASS)
            server.send_message(meg)
            print(f"[Ok] Event registration email sent to {to_email}")
    except Exception as e:
        print(f"[ERR] Failed to send event registration email to {to_email}:{e}")

   


@app.route("/register", methods = ["GET","POST"])
def register_account():
    """ 
    Get: Receive membership =? from the previous page, render the registration page, and pre-fill the level field.
    Post: Submit the regidtration form."""

    level_key = request.values.get("membership","ordinary")
    level = LEVELS.get(level_key,LEVELS["ordinary"])
    if request.method == "POST":
        email = (request.form.get("email")or "").strip().lower()
        full_name = (request.form.get("fullname")or "").strip()
        password = (request.form.get("password")or "").strip()

        user = User(email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        send_welcome_email(email,level)
        flash("Account created. Please login.","success")
        return redirect(url_for("Home"))
    return render_template("register.html",level=level, level_key = level_key)




# shwoing the society page.
@app.route('/Aboutsociety.html')
def Aboutsociety():
    return render_template('Aboutsociety.html')

# showing the login in page.
@app.route('/Login.html', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email')or '').strip().lower()
        password = (request.form.get('password')or '').strip()

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id']= user.id
            session['user_email']=user.email
            flash ("Login successful","success")
            return redirect(url_for('Home'))
        else:
            flash("Invaild email or password.", "danger")
    return render_template('Login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Your have been logged out.","info")
    return redirect(url_for('login'))




# showing the contact us page.
@app.route('/Contact.html')
def contact():
    return render_template('Contact.html')

#showing the forgot passsword page.
@app.route('/Forgotpassword.html')
def forgot_password():
    return render_template('Forgotpassword.html')

#showing the library page.
@app.route('/Library.html')
def library():
    return render_template('Library.html')

#showing the venuehire page.
@app.route('/Venuehire.html')
def venue_hire():
    return render_template('Venuehire.html')

#showing the Bulletin page.
@app.route('/Bulletin.html')
def bulletin():
    return render_template('Bulletin.html')

#showing the Geography website  page.
@app.route('/Geographywebsite.html')
def geography_website():
    return render_template('Geographywebsite.html')


@app.route('/Museums and other attractions.html')
def Museums_and_other_attractions():
    return render_template('Museums and other attractions.html')

@app.route('/MapResources.html')
def MapResources():
    return render_template('MapResources.html')

@app.route('/PhilateliesCover.html')
def PhilateliesCover():
    return render_template('PhilateliesCover.html')

@app.route('/Disclaimer.html')
def Disclaimer():
    return render_template('Disclaimer.html')

@app.route('/Committees.html')
def committees_html():
    return render_template('Committees.html')

@app.route('/Governance.html')
def governance_html():
    return render_template('Governance.html')

@app.route('/Honoursboard.html')
def honours_board():
    return render_template('Honoursboard.html')

@app.route('/Donate.html')
def donate():
    return render_template('Donate.html')
 

@app.route('/AustraliaGeographyCompetitions.html')
def australia_geography_competitions():
    return render_template('AustraliaGeographyCompetitions.html')

@app.route('/Lambertcenter.html')
def lambert_center():
    return render_template('Lambertcenter.html')

@app.route('/Queenslandbydegrees.html')
def queensland_by_degrees():
    return render_template('Queenslandbydegrees.html')


#  Society / News
@app.route('/SocietyNews.html')
def SocietyNews():
    """News list under Society (demo)."""
    return render_template('SocietyNews.html')

@app.route('/SocietyNews_2025_writing_comp.html')
def SocietyNews_2025_writing_comp():
    """Detail page: 2025 Geography Writing Competition - Long-Listed Stories."""
    return render_template('SocietyNews_2025_writing_comp.html')

@app.route('/SocietyNews_2025_tsunami_boulder.html')
def SocietyNews_2025_tsunami_boulder():
    """Detail page: Discovery of a 1200-ton tsunami boulder in Tonga."""
    return render_template('SocietyNews_2025_tsunami_boulder.html')

@app.route('/SocietyNews_2024_gbwo.html')
def SocietyNews_2024_gbwo():
    """Detail page: 2024 Geography’s Big Week Out."""
    return render_template('SocietyNews_2024_gbwo.html')

@app.route('/SocietyNews_2024_souvenir_exhibition.html')
def SocietyNews_2024_souvenir_exhibition():
    """Detail page: Souvenir Cover Exhibition."""
    return render_template('SocietyNews_2024_souvenir_exhibition.html')


def get_event(event_id : int):
    try:
        evt = Event.query.get(event_id)
        if evt:
            return {
                "id": evt.id,
                "title": evt.title,
                "date": evt.event_time,
                "location": evt.location,
                "price": f"${evt.price:.2f}" if evt.price is not None else "Free",
            }
    except Exception:
        pass
    return {
        "id": event_id,
        "title": f"Event #{event_id}",
        "date": "Date to be announced",
        "location": "Venue to be confirmed",
        "price": "",
    }




@app.route('/events/<int:event_id>/register', methods=["GET","POST"])
def register_event(event_id):
    ev = Event.query.get_or_404(event_id)

    event={
        "id": ev.id,
        "title": ev.title,
        "date": ev.event_time,
        "location": ev.location,
        "price": f"${ev.price:.2f}" if ev.price is not None else "Free",
    }

    if request.method == "POST":
        email = (request.form.get("email") or ""). strip()
        if email:
            send_event_confirmation_email(email,event)
            session['last_event_email']= email
            flash("You have successfully registered for this event.","event")
            return redirect(url_for("register_event_confirm",event_id=event_id))
        else:
            flash("Email is required")
            
    return render_template("event_register.html",event=event)

@app.route('/events/<int:event_id>/register/confirm')
def register_event_confirm(event_id):
    event = get_event(event_id)
    email = session.pop('last_event_email', None)
    return render_template("event_register_confirm.html",event=event,email=email)

@app.route('/events/<int:event_id>/delete', methods=["POST"])
def delete_event(event_id):
    ev = Event.query.get_or_404(event_id)
    if ev.image:
        try:
            from os.path import basename, join
            img_file = basename(ev.image)
            abs_path = join(app.config['UPLOAD_FOLDER'],img_file)
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except Exception:
            pass
    db.session.delete(ev)
    db.session.commit()
    flash("Event deleted.","success")
    return redirect(url_for("Eventlist"))

# showing the Awards & Prizes page.
@app.route('/AwardsPrizes.html')
def AwardsPrizes():
    return render_template('AwardsPrizes.html')

# showing the Student Research Grants page.
@app.route('/StudentResearchGrants.html')
def StudentResearchGrants():
    return render_template('StudentResearchGrants.html')



# ===============================================================
# Admin Center routes (additive only)
# - /admin/signup  : create admin via invite code TEAM305
# - /admin/login   : admin-only login
# ===============================================================
from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

ADMIN_INVITE_CODE = "TEAM305"

def _hash_password(raw: str) -> str:
    """Prefer project's helper if present; else use werkzeug; fallback to sha256."""
    try:
        return hash_password(raw)  # if your project already defines it
    except Exception:
        try:
            return generate_password_hash(raw, method="pbkdf2:sha256")
        except Exception:
            import hashlib
            return hashlib.sha256((raw or "").encode("utf-8")).hexdigest()

def _check_password(user, raw: str) -> bool:
    """Prefer model's method; else use werkzeug; else sha256 compare."""
    try:
        if hasattr(user, "check_password"):
            return user.check_password(raw)
        if getattr(user, "password_hash", None):
            return check_password_hash(user.password_hash, raw)
    except Exception:
        pass
    import hashlib
    return (user.password_hash or "") == hashlib.sha256((raw or "").encode("utf-8")).hexdigest()

@app.route("/admin/signup", methods=["GET", "POST"])
def admin_signup():
    """Admin self-registration with fixed invite code."""
    if request.method == "POST":
        code = (request.form.get("code") or "").strip()
        email = (request.form.get("email") or "").strip()
        full_name = (request.form.get("full_name") or "").strip()
        password = (request.form.get("password") or "").strip()
        password2 = (request.form.get("password2") or "").strip()

        if code != ADMIN_INVITE_CODE:
            flash("Invalid invite code.", "danger")
            return render_template("admin_signup.html", email=email, full_name=full_name)

        if not email or "@" not in email:
            flash("Please enter a valid email.", "warning")
            return render_template("admin_signup.html", email=email, full_name=full_name)
        if not password or len(password) < 8:
            flash("Password must be at least 8 characters.", "warning")
            return render_template("admin_signup.html", email=email, full_name=full_name)
        if password != password2:
            flash("Passwords do not match.", "warning")
            return render_template("admin_signup.html", email=email, full_name=full_name)
        if User.query.filter_by(email=email).first():
            flash("This email is already registered.", "warning")
            return render_template("admin_signup.html", email=email, full_name=full_name)

        try:
            u = User(email=email, full_name=(full_name or None), password_hash=_hash_password(password))
            # Role / is_active only if columns exist
            if hasattr(u, "role"):
                u.role = "admin"
            if hasattr(u, "is_active"):
                u.is_active = 1

            db.session.add(u)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Failed to create admin account. Please try again.", "danger")
            return render_template("admin_signup.html", email=email, full_name=full_name)

        session["user_id"] = u.id
        session["user_email"] = u.email
        session["current_user_name"] = u.full_name
        flash("Admin account created. Welcome!", "success")
        try:
            return redirect(url_for("admin.dashboard"))
        except Exception:
            return redirect(url_for("Home"))

    # GET -> show page; default active tab is Sign Up
    return render_template("admin_signup.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin-only login; members should use /login."""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = (request.form.get("password") or "")
        u = User.query.filter_by(email=email).first()

        if not u or not _check_password(u, password):
            flash("Invalid email or password.", "danger")
            # show admin tab on this page
            return render_template("admin_signup.html", active_tab="login")

        role = (getattr(u, "role", None) or "member").lower()
        if role not in ("admin", "staff"):
            flash("You don't have admin access.", "danger")
            return render_template("admin_signup.html", active_tab="login")

        if hasattr(u, "is_active") and not u.is_active:
            flash("This account is disabled.", "warning")
            return render_template("admin_signup.html", active_tab="login")

        session["user_id"] = u.id
        session["user_email"] = u.email
        session["current_user_name"] = u.full_name
        flash("Welcome back.", "success")
        try:
            return redirect(url_for("admin.dashboard"))
        except Exception:
            return redirect(url_for("Home"))

    # GET -> show page with login tab open
    return render_template("admin_signup.html", active_tab="login")



from admin import admin_bp
app.register_blueprint(admin_bp)


