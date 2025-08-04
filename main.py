from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

# display the homepage
@app.route('/')
def home():
    return render_template('homepage.html')

# display the event list
@app.route('/Eventlist.html')
def Eventlist():
    return render_template('Eventlist.html')

def get_events():
    conn = sqlite3.connect('rgsq.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM event")
    events = cursor.fetchall()
    conn.close()
    return events
