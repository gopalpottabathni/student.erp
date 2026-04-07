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

# 🔥 Run DB init on startup
init_db()


# ✅ NEW CORRECT SUBJECT EXTRACTION (FINAL FIX)
def extract_subjects(row):
    subjects = []

    for col in row.index:
        try:
            # detect subject columns like 25MAT1001
            if isinstance(col, str) and col.startswith("25"):
                subject_name = col
                marks = row[col]

                if isinstance(marks, (int, float)):
                    subjects.append((subject_name, marks))

                elif isinstance(marks, str):
                    try:
                        marks = float(marks)
                        subjects.append((subject_name, marks))
                    except:
                        continue

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

        df = pd.read_excel(file, engine="openpyxl", nrows=500)
        print("COLUMNS:", df.columns)

        df = df.fillna("")

        conn = sqlite3.connect(DB)

        for _, row in df.iterrows():
            try:
                urn = str(row.get("URN", "")).strip()
                name = str(row.get("Name", "")).strip()
                course = str(row.get("Course", "")).strip()

                if not urn:
                    continue

                conn.execute(
                    "INSERT OR IGNORE INTO students VALUES (?,?,?)",
                    (urn, name, course)
                )

                # ✅ USE NEW FUNCTION HERE
                subjects = extract_subjects(row)
                print("Subjects found:", subjects)

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
