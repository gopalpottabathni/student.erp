
from flask import Flask, render_template, request, redirect
import pandas as pd
import sqlite3

app = Flask(__name__)
DB = "erp.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS students (
        urn TEXT PRIMARY KEY,
        name TEXT,
        course TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS performance (
        urn TEXT,
        subject TEXT,
        marks REAL
    )''')

    conn.commit()
    conn.close()

def smart_parse(row):
    subjects = []
    for i in range(len(row)):
        val = row[i]
        if isinstance(val, str) and any(char.isdigit() for char in val):
            try:
                subject = row[i+1]
                marks = row[i+5]
                if isinstance(marks, (int, float)):
                    subjects.append((subject, marks))
            except:
                continue
    return subjects

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]
    df = pd.read_excel(file)

    conn = sqlite3.connect(DB)

    for _, row in df.iterrows():
        try:
            urn = str(row[2])
            name = row[1]
            course = row[3]

            conn.execute("INSERT OR IGNORE INTO students VALUES (?,?,?)",
                         (urn, name, course))

            subjects = smart_parse(row)

            for sub, marks in subjects:
                conn.execute("INSERT INTO performance VALUES (?,?,?)",
                             (urn, sub, marks))
        except:
            pass

    conn.commit()
    conn.close()
    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM performance", conn)

    summary = df.groupby("urn")["marks"].mean().reset_index()

    data = []
    for _, row in summary.iterrows():
        marks = row["marks"]
        if marks < 40:
            insight = "🔴 Critical"
        elif marks < 60:
            insight = "🟡 Average"
        else:
            insight = "🟢 Good"

        data.append({
            "urn": row["urn"],
            "marks": round(marks,2),
            "insight": insight
        })

    return render_template("dashboard.html", data=data)

if __name__ == "__main__":
    init_db()
    if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
