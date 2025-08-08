from flask import Flask, render_template,request
from flask_sqlalchemy import SQLAlchemy
import sqlite3

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

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

@app.route('/Create.html')
def Create():
    return render_template('Create.html')

def get_events():
    conn = sqlite3.connect('rgsq.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM event")
    events = cursor.fetchall()
    conn.close()
    return events

@app.route('/Memberbenefits.html')
def Memberbenefits():
    return render_template('Memberbenefits.html')

@app.route('/JoinRGSQ.html')
def join_rgsq():
    return render_template('JoinRGSQ.html')

@app.route('/Aboutsociety.html')
def about_society():
    return render_template('Aboutsociety/html')




