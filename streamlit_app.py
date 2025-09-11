
# streamlit_app.py
import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="מנגנון שיבוץ סטודנטים ↔︎ מדריכים", layout="centered")

# =========================
# עיצוב מינימלי + RTL
# =========================
st.markdown('''
<style>
:root{ --ink:#0f172a; --muted:#475569; --card:rgba(255,255,255,.86); }
html, body, [class*="css"] { font-family: system-ui, -apple-system, Segoe UI, Arial; }
.stApp, .main, [data-testid="stSidebar"]{ direction:rtl; text-align:right; }
[data-testid="stHeader"] { background: transparent; }
.block-container{ padding-top: 1rem; }
div[data-testid="stDownloadButton"] a { text-decoration:none; }
</style>
''', unsafe_allow_html=True)

st.title("🧩 מנגנון שיבוץ סטודנטים לעבודה סוציאלית לפי מדריכים/אתרים")

with st.expander("ℹ️ איך זה עובד?"):
    st.write('''
    - טוענים שני קבצי CSV:
      1) **students.csv** עם עמודות: `id, name, score`  
      2) **sites.csv** עם עמודות: `id, name, capacity`  (אתר/מדריך + קיבולת)
    - אלגוריתם Greedy: ממיין סטודנטים לפי **ציון יורד**, ובכל צעד משבץ ל**אתר עם הקיבולת הפנויה הגדולה ביותר**.
    - הפלט: `assignments.csv` עם התאמות + רשימת לא־משובצים (אם אין קיבולת).
    ''')

# =========================
# טעינת נתונים
# =========================
colL, colR = st.columns(2)

with colL:
    st.subheader("📥 סטודנטים")
    st.caption("קובץ בפורמט: id, name, score")
    up_students = st.file_uploader("העלאת students.csv", type=["csv"], key="students_csv")
    if up_students:
        students_df = pd.read_csv(up_students)
    else:
        # דוגמה מובנית
        students_df = pd.DataFrame([
            {"id":"S001","name":"Rawan Saab","score":95.0},
            {"id":"S002","name":"Maias Gotany","score":90.5},
            {"id":"S003","name":"Wissam Bebar","score":88.0},
            {"id":"S004","name":"Bayan Abu Nasser","score":86.0},
            {"id":"S005","name":"Hala Hassan","score":84.5},
            {"id":"S006","name":"Roya Saeed","score":83.0},
            {"id":"S007","name":"Student X","score":80.0},
        ])
    st.dataframe(students_df, use_container_width=True, hide_index=True)

with colR:
    st.subheader("📥 אתרים / מדריכים")
    st.caption("קובץ בפורמט: id, name, capacity")
    up_sites = st.file_uploader("העלאת sites.csv", type=["csv"], key="sites_csv")
    if up_sites:
        sites_df = pd.read_csv(up_sites)
    else:
        # דוגמה מובנית
        sites_df = pd.DataFrame([
            {"id":"SITE-A","name":"Safed Medical Center","capacity":2},
            {"id":"SITE-B","name":"Software Lab","capacity":2},
            {"id":"SITE-C","name":"Community Clinic","capacity":1},
        ])
    st.dataframe(sites_df, use_container_width=True, hide_index=True)

# בדיקות בסיסיות
def validate_inputs(students_df: pd.DataFrame, sites_df: pd.DataFrame) -> list:
    problems = []
    need_cols_students = {"id","name","score"}
    need_cols_sites = {"id","name","capacity"}
    if not need_cols_students.issubset(set(map(str.lower, students_df.columns))):
        problems.append("לקובץ הסטודנטים חייבות להיות עמודות: id, name, score")
    if not need_cols_sites.issubset(set(map(str.lower, sites_df.columns))):
        problems.append("לקובץ האתרים/מדריכים חייבות להיות עמודות: id, name, capacity")
    # המרות טיפוס
    try:
        students_df["score"] = pd.to_numeric(students_df["score"], errors="raise")
    except Exception:
        problems.append("העמודה score חייבת להיות מספרית.")
    try:
        sites_df["capacity"] = pd.to_numeric(sites_df["capacity"], errors="raise").astype(int)
        if (sites_df["capacity"] < 0).any():
            problems.append("capacity לא יכול להיות שלילי.")
    except Exception:
        problems.append("העמודה capacity חייבת להיות שלמה (int).")
    return problems

# =========================
# אלגוריתם השיבוץ (Greedy)
# =========================
def greedy_match(students: pd.DataFrame, sites: pd.DataFrame):
    students_sorted = students.sort_values("score", ascending=False).reset_index(drop=True)
    sites_work = sites.copy()
    sites_work["remaining"] = sites_work["capacity"]
    # לשמירת השיבוצים
    rows = []
    for _, stu in students_sorted.iterrows():
        # אתר/מדריך עם קיבולת פנויה מקסימלית (ואם יש שוויון – לפי id כדי לייצב)
        avail = sites_work[sites_work["remaining"] > 0].copy()
        if avail.empty:
            continue
        avail = avail.sort_values(["remaining", "id"], ascending=[False, True])
        best = avail.iloc[0]
        # עדכון
        sites_work.loc[sites_work["id"] == best["id"], "remaining"] -= 1
        rows.append({
            "student_id": stu["id"],
            "student_name": stu["name"],
            "score": float(stu["score"]),
            "site_id": best["id"],
            "site_name": best["name"],
        })
    assigned_df = pd.DataFrame(rows, columns=["student_id","student_name","score","site_id","site_name"])
    # לא-משובצים
    assigned_ids = set(assigned_df["student_id"]) if not assigned_df.empty else set()
    unassigned_df = students_sorted[~students_sorted["id"].isin(assigned_ids)].copy()
    return assigned_df, unassigned_df, sites_work[["id","name","capacity","remaining"]]

problems = validate_inputs(students_df.copy(), sites_df.copy())

run = st.button("🚀 בצע שיבוץ (Greedy)", type="primary", disabled=bool(problems))
if problems:
    st.error("לא ניתן להריץ:\n- " + "\n- ".join(problems))

if run:
    assignments_df, unassigned_df, capacities_df = greedy_match(students_df, sites_df)
    st.success("השיבוץ הושלם בהצלחה!")

    st.subheader("🗂 תוצאות השיבוץ")
    st.dataframe(assignments_df, use_container_width=True, hide_index=True)

    # הורדת CSV
    out_csv = assignments_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ הורדת assignments.csv",
        data=out_csv,
        file_name="assignments.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.subheader("📛 לא־משובצים")
    if unassigned_df.empty:
        st.write("כל הסטודנטים שובצו ✅")
    else:
        st.dataframe(unassigned_df[["id","name","score"]], use_container_width=True, hide_index=True)

    st.subheader("📦 קיבולות לאחר שיבוץ")
    st.dataframe(capacities_df, use_container_width=True, hide_index=True)
