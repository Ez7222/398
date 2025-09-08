
from flask import Flask, render_template,request,redirect,url_for,flash,abort,session
from flask_sqlalchemy import SQLAlchemy
import sqlite3
import os
import smtplib
from email.message import EmailMessage


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.secret_key = 'change_me'



class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    price = db.Column(db.String(20), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)


with app.app_context():
    db.create_all()

# display the homepage
@app.route('/')
def Home():
    return render_template('homepage.html')

# display the event list
@app.route('/Eventlist.html')
def Eventlist():
    per_page = 6
    page = request.args.get('page',1,type=int)
    event_list = [{"title": f"Event {i}"} for i in range(1, 21)]
    events_paginated = event_list[(page-1)*per_page: page*per_page]
    total_pages = (len(event_list) + per_page - 1) // per_page
    return render_template('Eventlist.html',events = events_paginated, page=page, total_pages = total_pages)

# display the create event page.
@app.route('/Create.html')
def Create():
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

   


@app.route("/register", methods = ["GET","POST"])
def register_account():
    """ 
    Get: Receive membership =? from the previous page, render the registration page, and pre-fill the level field.
    Post: Submit the regidtration form."""

    level_key = request.values.get("membership","ordinary")
    level = LEVELS.get(level_key,LEVELS["ordinary"])
    if request.method == "POST":
        email = request.form.get("email").strip()
        full_name = request.form.get("fullname","").strip()
        password = request.form.get("password","").strip()
        send_welcome_email(email,level)
        return redirect(url_for("Home"))
    return render_template("register.html",level=level, level_key = level_key)




# shwoing the society page.
@app.route('/Aboutsociety.html')
def Aboutsociety():
    return render_template('Aboutsociety.html')

# showing the login in page.
@app.route('/Login.html')
def login():
    return render_template('Login.html')

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

@app.route('/SocietyNews/writing-competition-2025.html')
def SocietyNews_writing_competition_2025():
    """Detail page: 2025 Geography Writing Competition - Long-Listed Stories."""
    return render_template('SocietyNews_2025_writing_comp.html')

@app.route('/SocietyNews/tsunami-boulder-tonga-2025.html')
def SocietyNews_tsunami_boulder_2025():
    """Detail page: Discovery of a 1200-ton tsunami boulder in Tonga."""
    return render_template('SocietyNews_2025_tsunami_boulder.html')

def get_event(event_id : int):
    try:
        evt = Event.query.get(event_id)
        if evt:
            return {
                "id": evt.id,
                "title": evt.title,
                "date": evt.date,
                "location": evt.location,
                "price": getattr(evt, "price", ""),
            }
    except Exception:
        pass
    return {
        "id": event_id,
        "title": "Geography writing competition" if event_id == 1 else f"Event #{event_id}",
        "date": "Date to be announced",
        "location": "Venue to be confirmed",
        "price": "",
    }
    


@app.route('/events/<int:event_id>/register', methods=["GET","POST"])
def register_event(event_id):
    event = get_event(event_id)

    if request.method == "POST":
        email = (request.form.get("email") or ""). strip()
        if not email:
            flash("Email is required.","error")
        else:
            flash("You have successfully registered for the event.","success")
            return redirect(url_for("register_event_confirm",event_id=event_id))
    return render_template("event_register.html",event=event)

@app.route('/events/<int:event_id>/register/confirm')
def register_event_confirm(event_id):
    event = get_event(event_id)
    return render_template("event_register_confirm.html",event=event)

# showing the Awards & Prizes page.
@app.route('/AwardsPrizes.html')
def AwardsPrizes():
    return render_template('AwardsPrizes.html')

# showing the Student Research Grants page.
@app.route('/StudentResearchGrants.html')
def StudentResearchGrants():
    return render_template('StudentResearchGrants.html')





