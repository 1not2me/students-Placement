# streamlit_app.py
import streamlit as st
import pandas as pd
from pathlib import Path
from io import BytesIO
from datetime import datetime

# streamlit_app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

# =========================
# הגדרות כלליות
# =========================
st.set_page_config(page_title="מנגנון שיבוץ סטודנטים", layout="centered")

ADMIN_PASSWORD = "rawan_0304"


st.markdown("""
<style>
/* RTL + מראה נקי */
:root{ --ink:#0f172a; --ring:rgba(155,93,229,.25); --card:rgba(255,255,255,.78); }
html, body, [class*="css"] { font-family: system-ui, "Segoe UI", Arial; }
.stApp, .main, [data-testid="stSidebar"]{ direction:rtl; text-align:right; }
[data-testid="stAppViewContainer"]{ 
  background:
    radial-gradient(1200px 600px at 15% 10%, #ede7f6 0%, transparent 70%),
    radial-gradient(1000px 700px at 85% 20%, #fff3e0 0%, transparent 70%),
    radial-gradient(900px 500px at 50% 80%, #fce4ec 0%, transparent 70%),
    linear-gradient(135deg, #e0f7fa 0%, #ffffff 100%) !important;
  color: var(--ink);
}
.main .block-container{
  background: var(--card);
  backdrop-filter: blur(10px);
  border:1px solid rgba(15,23,42,.08);
  box-shadow:0 15px 35px rgba(15,23,42,.08);
  border-radius:24px; padding:1.25rem 1.25rem 1.75rem; margin-top: .8rem;
}
.stButton > button{
  background:linear-gradient(135deg,#9b5de5 0%,#f15bb5 100%)!important;color:#fff!important;border:none!important;
  border-radius:14px!important;padding:.6rem 1.1rem!important;font-weight:600!important;
  box-shadow:0 8px 18px var(--ring)!important; transition: all .12s ease!important;
}
.stButton > button:hover{ transform: translateY(-2px) scale(1.01); filter:brightness(1.06); }
div[data-baseweb="select"] > div, .stTextInput > div > div > input { border-radius:12px!important; }
</style>
""", unsafe_allow_html=True)
# =========================
# פונקציות עזר
# =========================

def greedy_match(students, sites):
    """
    מימוש פשוט של Greedy Matcher:
    עבור כל סטודנט נבדוק את רשימת ההעדפות שלו לפי סדר,
    ונשבץ לאתר אם יש מקום פנוי.
    """
    assignments = []
    site_capacity = {s["name"]: s["capacity"] for s in sites}

    for student in students:
        placed = None
        for pref in student["preferences"]:
            if site_capacity.get(pref, 0) > 0:
                assignments.append({
                    "student_id": student["id"],
                    "student_name": student["name"],
                    "assigned_site": pref
                })
                site_capacity[pref] -= 1
                placed = pref
                break
        if not placed:
            assignments.append({
                "student_id": student["id"],
                "student_name": student["name"],
                "assigned_site": "לא שובץ"
            })

    return pd.DataFrame(assignments)


def df_to_excel_bytes(df: pd.DataFrame, sheet: str = "שיבוץ") -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=sheet, index=False)
        worksheet = writer.sheets[sheet]
        for i, col in enumerate(df.columns):
            col_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, min(col_width, 50))
    buf.seek(0)
    return buf.read()


# =========================
# כניסת מנהל
# =========================
st.title("🔑 מערכת שיבוץ סטודנטים – מנהלים בלבד")

pwd = st.text_input("הכנס סיסמת מנהל:", type="password")

if pwd != ADMIN_PASSWORD:
    st.warning("יש להזין סיסמת מנהל תקינה כדי להמשיך.")
    st.stop()

st.success("מחובר בהצלחה ✅")

# =========================
# העלאת קבצים
# =========================
st.header("📂 העלאת נתונים")

students_file = st.file_uploader("העלה קובץ סטודנטים (CSV)", type=["csv"])
sites_file = st.file_uploader("העלה קובץ אתרים (CSV)", type=["csv"])

if students_file and sites_file:
    students_df = pd.read_csv(students_file)
    sites_df = pd.read_csv(sites_file)

    st.subheader("📊 טבלת סטודנטים")
    st.dataframe(students_df, use_container_width=True)

    st.subheader("🏫 טבלת אתרים")
    st.dataframe(sites_df, use_container_width=True)

    # הפעלת מנגנון השיבוץ
    if st.button("🚀 הפעל שיבוץ"):
        # הכנה לפורמט
        students = []
        for _, row in students_df.iterrows():
            prefs = [p.strip() for p in str(row.get("preferences", "")).split(";") if p.strip()]
            students.append({"id": row["id"], "name": row["name"], "preferences": prefs})

        sites = []
        for _, row in sites_df.iterrows():
            sites.append({"name": row["name"], "capacity": int(row["capacity"])})

        result_df = greedy_match(students, sites)

        st.success("✅ השיבוץ בוצע בהצלחה!")
        st.subheader("📋 תוצאות השיבוץ")
        st.dataframe(result_df, use_container_width=True)

        st.download_button(
            "📥 הורדת תוצאות כ־Excel",
            data=df_to_excel_bytes(result_df),
            file_name=f"assignments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.download_button(
            "📥 הורדת תוצאות כ־CSV",
            data=result_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name=f"assignments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

else:
    st.info("אנא העלה גם קובץ סטודנטים וגם קובץ אתרים כדי להמשיך.")
