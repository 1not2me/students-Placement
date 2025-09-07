# streamlit_app.py
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

# =========================
# הגדרות כלליות
# =========================
st.set_page_config(page_title="מנגנון שיבוץ סטודנטים (מנהלים בלבד)", layout="centered")
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
def df_to_excel_bytes(df: pd.DataFrame, sheet: str = "שיבוץ") -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=sheet, index=False)
        ws = writer.sheets[sheet]
        for i, col in enumerate(df.columns):
            # רוחב עמודה אוטומטי
            width = max(len(str(col)), int(df[col].astype(str).map(len).max() if not df.empty else 12)) + 2
            ws.set_column(i, i, min(width, 60))
    buf.seek(0)
    return buf.read()

def read_any(file) -> pd.DataFrame:
    """קורא CSV או XLSX. אם חסר openpyxl – מציג הודעה ידידותית."""
    name = (file.name or "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(file, encoding="utf-8-sig")
    if name.endswith(".xlsx"):
        try:
            return pd.read_excel(file, engine="openpyxl")
        except ImportError:
            st.error("❌ חסרה הספרייה openpyxl לקריאת XLSX. הוסף/י לקובץ requirements.txt:  \n`openpyxl`")
            return pd.DataFrame()
    st.error("פורמט לא נתמך – השתמש/י ב־CSV או XLSX.")
    return pd.DataFrame()

def validate_students_df(df: pd.DataFrame) -> list[str]:
    """בודק עמודות חובה וטיפוסים לסטודנטים."""
    errors = []
    required = {"id", "name", "preferences"}
    missing = required - set(df.columns)
    if missing:
        errors.append(f"חסרות עמודות בקובץ הסטודנטים: {', '.join(missing)}")
        return errors

    # בדיקות בסיסיות
    if df["id"].isna().any():
        errors.append("עמודת id מכילה ערכים חסרים.")
    if df["name"].isna().any():
        errors.append("עמודת name מכילה ערכים חסרים.")

    return errors

def validate_sites_df(df: pd.DataFrame) -> list[str]:
    """בודק עמודות חובה וטיפוסים לאתרים."""
    errors = []
    required = {"name", "capacity"}
    missing = required - set(df.columns)
    if missing:
        errors.append(f"חסרות עמודות בקובץ האתרים: {', '.join(missing)}")
        return errors

    # ניסיון להמיר capacity למספר שלם
    try:
        df["capacity"] = pd.to_numeric(df["capacity"], errors="raise").astype(int)
    except Exception:
        errors.append("העמודה capacity חייבת להיות מספרית (שלמה).")

    if "capacity" in df.columns and (df["capacity"] < 0).any():
        errors.append("capacity לא יכול להיות שלילי.")

    if df["name"].isna().any():
        errors.append("עמודת name (באתרים) מכילה ערכים חסרים.")

    return errors

def parse_students(df: pd.DataFrame) -> list[dict]:
    """המרת DataFrame של סטודנטים למבנה נוח לשיבוץ."""
    students = []
    for _, row in df.iterrows():
        raw_prefs = str(row.get("preferences", "")).strip()
        # העדפות מופרדות ב־; (למשל: "Ziv; Welfare K8; Day Center")
        prefs = [p.strip() for p in raw_prefs.split(";") if p.strip()]
        students.append({
            "id": row["id"],
            "name": row["name"],
            "preferences": prefs
        })
    return students

def parse_sites(df: pd.DataFrame) -> list[dict]:
    """המרת DataFrame של אתרים למבנה נוח לשיבוץ."""
    sites = []
    for _, row in df.iterrows():
        sites.append({
            "name": str(row["name"]).strip(),
            "capacity": int(row["capacity"])
        })
    return sites

def greedy_match(students: list[dict], sites: list[dict]) -> pd.DataFrame:
    """
    מימוש Greedy Matcher:
    עובר על הסטודנטים לפי הסדר, ובוחר עבור כל אחד את האתר המועדף הראשון שנותר בו מקום.
    """
    assignments = []
    site_capacity = {s["name"]: s["capacity"] for s in sites}

    for s in students:
        placed = None
        for pref in s["preferences"]:
            if site_capacity.get(pref, 0) > 0:
                assignments.append({
                    "student_id": s["id"],
                    "student_name": s["name"],
                    "assigned_site": pref
                })
                site_capacity[pref] -= 1
                placed = pref
                break

        if not placed:
            assignments.append({
                "student_id": s["id"],
                "student_name": s["name"],
                "assigned_site": "לא שובץ"
            })

    return pd.DataFrame(assignments)

# =========================
# כניסת מנהל
# =========================
st.title("🔑 מערכת שיבוץ סטודנטים – מנהלים בלבד")
pwd = st.text_input("הכנס/י סיסמת מנהל:", type="password", help="יש להקליד את הסיסמה כדי להמשיך")

if pwd != ADMIN_PASSWORD:
    st.warning("⚠️ יש להזין סיסמת מנהל תקינה כדי להמשיך.")
    st.stop()

st.success("מחובר/ת כמנהל/ת ✅")

# =========================
# העלאת קבצים
# =========================
st.header("📂 העלאת נתונים")

col_a, col_b = st.columns(2)
with col_a:
    st.caption("קובץ סטודנטים (CSV/XLSX)")
    students_file = st.file_uploader("העלה/י קובץ סטודנטים", type=["csv", "xlsx"], key="students_upl")

with col_b:
    st.caption("קובץ אתרים (CSV/XLSX)")
    sites_file = st.file_uploader("העלה/י קובץ אתרים", type=["csv", "xlsx"], key="sites_upl")

if not (students_file and sites_file):
    st.info("נא להעלות גם קובץ סטודנטים וגם קובץ אתרים.")
    st.stop()

# קריאה + ולידציה
students_df = read_any(students_file)
sites_df = read_any(sites_file)

if students_df.empty or sites_df.empty:
    st.error("לא ניתן לעבד את הקבצים. ודא/י שהקבצים לא ריקים ושהפורמט נתמך.")
    st.stop()

st.subheader("📊 תצוגה מקדימה – סטודנטים")
st.dataframe(students_df, use_container_width=True)

st.subheader("🏫 תצוגה מקדימה – אתרים")
st.dataframe(sites_df, use_container_width=True)

stud_errs = validate_students_df(students_df)
site_errs = validate_sites_df(sites_df)

if stud_errs or site_errs:
    st.error("נמצאו בעיות בקלט. נא לתקן את הקבצים ולנסות שוב.")
    if stud_errs:
        st.markdown("**שגיאות – קובץ סטודנטים:**")
        for e in stud_errs:
            st.markdown(f"- {e}")
    if site_errs:
        st.markdown("**שגיאות – קובץ אתרים:**")
        for e in site_errs:
            st.markdown(f"- {e}")
    st.stop()

# =========================
# הפעלת מנגנון השיבוץ
# =========================
st.header("⚙️ הפעלת שיבוץ")

students = parse_students(students_df)
sites = parse_sites(sites_df)

if st.button("🚀 הפעל שיבוץ גרידי"):
    result_df = greedy_match(students, sites)

    st.success("✅ השיבוץ הושלם בהצלחה!")
    st.subheader("📋 תוצאות השיבוץ")
    st.dataframe(result_df, use_container_width=True)

    file_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        "📥 הורד/י כ־Excel",
        data=df_to_excel_bytes(result_df),
        file_name=f"assignments_{file_stamp}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.download_button(
        "📥 הורד/י כ־CSV",
        data=result_df.to_csv(index=False, encoding="utf-8-sig"),
        file_name=f"assignments_{file_stamp}.csv",
        mime="text/csv"
    )

# טיפים לקבצים (אופציונלי – עוזר למרצים להכין קלט נכון)
with st.expander("📎 דוגמת כותרות נדרשות לקבצים", expanded=False):
    st.markdown("""
**סטודנטים – עמודות חובה:**
- `id` — מזהה סטודנט (טקסט/מספר)
- `name` — שם הסטודנט/ית
- `preferences` — העדפות מופרדות ב־`;`  (לדוגמה: `בית חולים זיו; שירותי רווחה קריית שמונה; מרכז יום`)

**אתרים – עמודות חובה:**
- `name` — שם אתר
- `capacity` — קיבולת שלמה (מספר הסטודנטים שניתן לשבץ באתר)
""")
