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
# ---------- עזר: קריאה מכל סוג קובץ ----------
def read_any(file):
    if file is None:
        return pd.DataFrame()
    name = (file.name or "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(file, encoding="utf-8-sig")
    if name.endswith(".xlsx"):
        # openpyxl נדרש בצד השרת (Streamlit Cloud: להוסיף ל-requirements.txt)
        return pd.read_excel(file, engine="openpyxl")
    # לא תומכים בפורמט אחר
    return pd.DataFrame()

# ---------- עזר: איתור עמודות לסטודנטים ----------
def normalize_students(df: pd.DataFrame):
    """
    מחזיר:
      students: רשימת סטודנטים עם id, name, preferences(list[str])
      notes: טקסט תמציתי על מיפויים/השערות שבוצעו
    """
    notes = []
    if df.empty:
        return [], "לא נטענו נתוני סטודנטים."

    # מזהה
    sid_col = None
    for c in df.columns:
        if str(c).strip() in ["id", "תעודת_זהות", "מספר_זהות", "תז", "ת״ז"]:
            sid_col = c
            break
    if sid_col is None:
        # אין ת"ז/ID — נייצר מזהה רץ
        df = df.copy()
        df["_gen_id"] = range(1, len(df) + 1)
        sid_col = "_gen_id"
        notes.append("לא נמצאה עמודת מזהה; נוצר מזהה רץ.")

    # שם
    name_col = None
    for c in df.columns:
        if str(c).strip().lower() == "name":
            name_col = c
            break
    if name_col is None:
        # ננסה לחבר שם פרטי + משפחה
        fn = None
        ln = None
        for c in df.columns:
            sc = str(c).strip()
            if sc in ["שם_פרטי", "שם פרטי"]:
                fn = c
            if sc in ["שם_משפחה", "שם משפחה"]:
                ln = c
        if fn is not None or ln is not None:
            df = df.copy()
            df["_gen_name"] = (
                df[fn].astype(str).str.strip().fillna("") if fn in df else ""
            ).astype(str) + " " + (
                df[ln].astype(str).str.strip().fillna("") if ln in df else ""
            ).astype(str)
            name_col = "_gen_name"
            notes.append("נוצר שם מ-'שם_פרטי' + 'שם_משפחה'.")
        else:
            # אם אין כלום – ניצור שם גנרי
            df = df.copy()
            df["_gen_name"] = "סטודנט/ית"
            name_col = "_gen_name"
            notes.append("לא נמצאה עמודת שם; שויכו שמות כלליים.")

    # העדפות
    prefs_series = None
    # 1) preferences
    for c in df.columns:
        if str(c).strip().lower() == "preferences":
            prefs_series = df[c].astype(str)
            notes.append("העדפות נלקחו מעמודת 'preferences'.")
            break
    # 2) תחומים_מועדפים (מופרד ; )
    if prefs_series is None:
        for c in df.columns:
            if str(c).strip() in ["תחומים_מועדפים", "תחומים מועדפים"]:
                prefs_series = df[c].astype(str)
                notes.append("העדפות נלקחו מעמודת 'תחומים_מועדפים'.")
                break
    # 3) דירוגים: עמודות שמתחילות ב'דירוג_' עם מספר 1..10 כתוכן
    ranked = None
    if prefs_series is None:
        rank_cols = [c for c in df.columns if str(c).startswith("דירוג_")]
        if rank_cols:
            # נבנה סדר עדיפויות לפי הערך המספרי (1 מועדף)
            ranked = []
            for _, row in df.iterrows():
                pairs = []
                for c in rank_cols:
                    v = str(row[c]).strip()
                    if v.isdigit():
                        pairs.append((int(v), c.replace("דירוג_", "")))
                prefs = [name for _, name in sorted(pairs, key=lambda x: x[0])]
                ranked.append(";".join(prefs))
            prefs_series = pd.Series(ranked)
            notes.append("העדפות חושבו מעמודות דירוג (דירוג_*).")

    # יצירת הרשימה הסופית
    students = []
    for _, row in df.iterrows():
        sid = str(row[sid_col]).strip()
        nm = str(row[name_col]).strip()
        if prefs_series is not None:
            prefs = [p.strip() for p in str(prefs_series.iloc[_]).split(";") if p.strip()]
        else:
            prefs = []  # אם אין – ננסה עדיין לשבץ בהמשך (לא ישובץ בפועל)
        students.append({"id": sid, "name": nm, "preferences": prefs})

    if prefs_series is None:
        notes.append("לא נמצאו העדפות בקובץ; סטודנטים ללא העדפות לא ישובצו.")

    return students, " | ".join(notes)

# ---------- עזר: איתור עמודות לאתרים ----------
def normalize_sites(df: pd.DataFrame):
    """
    מחזיר:
      sites: רשימת אתרים עם name, capacity(int)
      notes: טקסט תמציתי על מיפויים/השערות שבוצעו
    """
    notes = []
    if df.empty:
        return [], "לא נטענו נתוני אתרים."

    # שם אתר
    name_col = None
    for c in df.columns:
        sc = str(c).strip().lower()
        if sc in ["name", "site_name"]:
            name_col = c
            break
    if name_col is None:
        for c in df.columns:
            sc = str(c).strip()
            if sc in ["שם", "שם_אתר", "שם אתר"]:
                name_col = c
                break
    if name_col is None:
        # אין שם – נפסול הכל
        return [], "לא נמצאה עמודת שם אתר (name/שם/שם_אתר)."

    # קיבולת
    cap_col = None
    for c in df.columns:
        sc = str(c).strip().lower()
        if sc in ["capacity", "cap"]:
            cap_col = c
            break
    if cap_col is None:
        for c in df.columns:
            sc = str(c).strip()
            if sc in ["קיבולת", "מספר_מקומות", "מקומות"]:
                cap_col = c
                break
    if cap_col is None:
        notes.append("לא נמצאה קיבולת; נקבע 1 כברירת מחדל לכל אתר.")
        df = df.copy()
        df["_gen_capacity"] = 1
        cap_col = "_gen_capacity"

    sites = []
    for _, row in df.iterrows():
        nm = str(row[name_col]).strip()
        try:
            cap = int(row[cap_col])
        except Exception:
            cap = 1
        if nm:
            sites.append({"name": nm, "capacity": max(cap, 0)})
    return sites, " | ".join(notes)

# ---------- שיבוץ Greedy ----------
def greedy_match(students, sites):
    assignments = []
    site_capacity = {s["name"]: int(s["capacity"]) for s in sites}

    for s in students:
        placed = None
        for pref in s.get("preferences", []):
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

# ---------- Excel להורדה ----------
def df_to_excel_bytes(df: pd.DataFrame, sheet: str = "שיבוץ") -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=sheet, index=False)
        ws = writer.sheets[sheet]
        for i, col in enumerate(df.columns):
            w = min(50, max(len(col), int(df[col].astype(str).map(len).max() or 12)) + 2)
            ws.set_column(i, i, w)
    buf.seek(0)
    return buf.read()

# ========================= ממשק =========================
st.title("🔑 מערכת שיבוץ סטודנטים – מנהלים בלבד")
pwd = st.text_input("סיסמת מנהל:", type="password", help="הזינו את סיסמת המנהל כדי להמשיך.")

if pwd != ADMIN_PASSWORD:
    st.info("הכניסו סיסמה כדי להמשיך.")
    st.stop()

st.success("מחובר/ת כמנהל/ת ✅")

st.header("📂 העלאת נתונים")
col_a, col_b = st.columns(2)
with col_a:
    st.caption("קובץ סטודנטים (CSV/XLSX)")
    students_file = st.file_uploader("העלה קובץ סטודנטים", type=["csv", "xlsx"], key="students")
with col_b:
    st.caption("קובץ אתרים (CSV/XLSX)")
    sites_file = st.file_uploader("העלה קובץ אתרים", type=["csv", "xlsx"], key="sites")

students_df = read_any(students_file)
sites_df = read_any(sites_file)

if not students_df.empty:
    st.subheader("📊 תצוגה מקדימה – סטודנטים")
    st.dataframe(students_df.head(50), use_container_width=True)
if not sites_df.empty:
    st.subheader("🏫 תצוגה מקדימה – אתרים")
    st.dataframe(sites_df.head(50), use_container_width=True)

if st.button("🚀 הפעל שיבוץ", use_container_width=True):
    students, s_notes = normalize_students(students_df)
    sites, t_notes = normalize_sites(sites_df)

    if s_notes:
        st.caption(f"ℹ️ סטודנטים: {s_notes}")
    if t_notes:
        st.caption(f"ℹ️ אתרים: {t_notes}")

    if not students:
        st.warning("לא נמצאו סטודנטים תקפים לשיבוץ.")
    elif not sites:
        st.warning("לא נמצאו אתרים תקפים לשיבוץ.")
    else:
        result_df = greedy_match(students, sites)
        st.success("השיבוץ הושלם ✅")
        st.subheader("📋 תוצאות השיבוץ")
        st.dataframe(result_df, use_container_width=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "📥 הורדת תוצאות כ־Excel",
            data=df_to_excel_bytes(result_df),
            file_name=f"assignments_{ts}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        st.download_button(
            "📥 הורדת תוצאות כ־CSV",
            data=result_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name=f"assignments_{ts}.csv",
            mime="text/csv",
            use_container_width=True
        )
else:
    st.info("בחרו שני קבצים (סטודנטים + אתרים) ואז לחצו על «הפעל שיבוץ».")
