from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('homepage.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)

def get_events():
    conn = sqlite3.connect('rgsq.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM event")
    events = cursor.fetchall()
    conn.close()
    return events