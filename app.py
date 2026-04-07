from flask import Flask, render_template, request, redirect
import pandas as pd
import sqlite3
import os

app = Flask(__name__, template_folder=os.path.join(os.getcwd(), "templates"))
DB = "erp.db"

# ✅ Initialize DB
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

# 🔥 IMPORTANT: Run on startup (for Render)
init_db()


# ✅ Safe subject parser
def smart_parse(row):
    subjects = []
    row = list(row)

    for i in range(len(row)):
        try:
            val = row[i]

            if isinstance(val, str) and any(char.isdigit() for char in val):

                subject = row[i+1] if i+1 < len(row) else None
                marks = row[i+5] if i+5 < len(row) else None

                if isinstance(marks, (int, float)):
                    subjects.append((subject, marks))

        except:
            continue

    return subjects


@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception as e:
        return f"ERROR LOADING INDEX: {str(e)}"


@app.route("/upload", methods=["POST"])
def upload():
    try:
        file = request.files["file"]

        # ✅ Memory-safe Excel read
        df = pd.read_excel(file, engine="openpyxl", nrows=500)
        df = df.fillna("")

        conn = sqlite3.connect(DB)

        for _, row in df.iterrows():
            try:
                urn = str(row[2])
                name = row[1]
                course = row[3]

                conn.execute(
                    "INSERT OR IGNORE INTO students VALUES (?,?,?)",
                    (urn, name, course)
                )

                subjects = smart_parse(row)

                for sub, marks in subjects:
                    conn.execute(
                        "INSERT INTO performance VALUES (?,?,?)",
                        (urn, sub, marks)
                    )

            except Exception as e:
                print("ROW ERROR:", e)

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    except Exception as e:
        return f"UPLOAD ERROR: {str(e)}"


@app.route("/dashboard")
def dashboard():
    conn = sqlite3.connect(DB)

    try:
        df = pd.read_sql_query("SELECT * FROM performance", conn)
    except Exception as e:
        return f"DB ERROR: {str(e)}"

    if df.empty:
        return "No data found. Please upload Excel first."

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
            "marks": round(marks, 2),
            "insight": insight
        })

    return render_template("dashboard.html", data=data)


# ✅ Correct run block (local only)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
