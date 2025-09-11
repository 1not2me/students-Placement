# streamlit_app.py
# --------------------------------------------
# מנגנון שיבוץ סטודנטים לעבודה סוציאלית על פי מיפוי מדריכים
# Streamlit app – RTL + עברית, כולל העלאת CSVs, שיבוץ Greedy וייצוא assignments.csv
# --------------------------------------------

import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
import re
from pathlib import Path

# =========================
# הגדרות כלליות + עיצוב
# =========================
st.set_page_config(page_title="מנגנון שיבוץ סטודנטים – עבודה סוציאלית", layout="wide")

# ---- RTL + מראה נקי ----
st.markdown("""
<style>
:root{
  --ink:#0f172a; --muted:#475569; --ring:rgba(99,102,241,.25); --card:rgba(255,255,255,.85);
}
html, body, [class*="css"] { font-family: system-ui, "Segoe UI", Arial; }
.stApp, .main, [data-testid="stSidebar"]{ direction:rtl; text-align:right; }
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 8% 8%, #e0f7fa 0%, transparent 65%),
    radial-gradient(1000px 500px at 92% 12%, #ede7f6 0%, transparent 60%),
    radial-gradient(900px 500px at 20% 90%, #fff3e0 0%, transparent 55%);
}
.block-container{ padding-top: 1.4rem; }
h1,h2,h3{ color:var(--ink); }
[data-testid="stSidebar"]{
  background: linear-gradient(180deg, #ffffffaa, #ffffff66);
  border-left: 1px solid #e2e8f0;
}
.kpi{ background:var(--card); border:1px solid #e2e8f0; padding:14px; border-radius:16px; }
hr{ border-color:#e2e8f0; }
</style>
""", unsafe_allow_html=True)

# =========================
# קבועים והעדפות
# =========================
ADMIN_PASSWORD = "rawan_0304"  # ניתן לשינוי
DEFAULT_FOLDER = Path("./")     # ב-Streamlit Cloud זו תיקיית האפליקציה

# שמות קבצים ברירת מחדל אם קיימים בפרויקט (כמו שהעלית בעבר)
DEFAULT_STUDENTS = DEFAULT_FOLDER / "students.csv"
DEFAULT_SITES    = DEFAULT_FOLDER / "sites.csv"
DEFAULT_ASSIGN   = DEFAULT_FOLDER / "assignments.csv"

# =========================
# פונקציות עזר
# =========================
def _strip(s):
    if pd.isna(s):
        return None
    return str(s).strip()

def normalize_students_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    נירמול עמודות סטודנטים: מזהה/שם/העדפות.
    תומך גם בעמודת העדפות אחת מופרדת בפסיקים וגם Pref1/Pref2/Pref3...
    """
    df = df.copy()

    # מיפוי שמות אפשריים
    candidates_id   = ["id","student_id","תז","ת.ז","מספר סטודנט"]
    candidates_name = ["name","student_name","full_name","שם","שם סטודנט"]
    # מצא עמודות זהות/שם
    id_col = next((c for c in df.columns if c.strip().lower() in candidates_id), None)
    name_col = next((c for c in df.columns if c.strip().lower() in candidates_name), None)

    if id_col is None:
        # אם אין מזהה – ניצור מזהה רץ
        df["student_id"] = [f"S{i+1:03d}" for i in range(len(df))]
        id_col = "student_id"
    else:
        df.rename(columns={id_col: "student_id"}, inplace=True)
        id_col = "student_id"

    if name_col is None:
        # אם אין שם – נשתמש במזהה כשם
        df["student_name"] = df[id_col].astype(str)
        name_col = "student_name"
    else:
        df.rename(columns={name_col: "student_name"}, inplace=True)
        name_col = "student_name"

    # מצא עמודת העדפות יחידה (מופרדת בפסיקים) אם קיימת
    single_pref_col = None
    for c in df.columns:
        lc = c.strip().lower()
        if "pref" in lc or "העדפות" in lc or "עדפות" in lc or "העדפה" in lc:
            # נעדיף עמודה שמכילה פסיקים/ריבוי ערכים
            if df[c].astype(str).str.contains(",").any():
                single_pref_col = c
                break

    prefs_cols = [c for c in df.columns if re.match(r'(?i)pref[\s_]*\d+', c) or re.match(r'(?i)עדפ[ה|ות]?[\s_]*\d+', c)]

    preferences = []
    if single_pref_col:
        for val in df[single_pref_col].fillna("").astype(str):
            prefs = [p.strip() for p in val.split(",") if p.strip()]
            preferences.append(prefs)
    elif prefs_cols:
        # מיין ע"פ המספר
        def key_func(c):
            m = re.search(r'(\d+)', c)
            return int(m.group(1)) if m else 999
        prefs_cols = sorted(prefs_cols, key=key_func)
        for _, row in df[prefs_cols].iterrows():
            prefs = [ _strip(x) for x in row.values.tolist() if _strip(x) ]
            preferences.append(prefs)
    else:
        # אין עדפות – רשימה ריקה לכל סטודנט
        preferences = [[] for _ in range(len(df))]

    out = pd.DataFrame({
        "student_id": df[id_col].astype(str).apply(_strip),
        "student_name": df[name_col].astype(str).apply(_strip),
    })
    out["preferences"] = preferences
    return out

def normalize_sites_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    נירמול עמודות אתרים/מדריכים: שם + קיבולת.
    מזהה עמודות כמו name/site/guide/mentor ו-capacity/קיבולת/מספר מקומות.
    """
    df = df.copy()
    candidates_name = ["name","site","site_name","guide","mentor","institution","שם","שם אתר","שם מדריך","מדריך","אתר"]
    candidates_cap  = ["capacity","cap","slots","places","קיבולת","מקומות","מספר מקומות","מס' מקומות"]

    name_col = next((c for c in df.columns if c.strip().lower() in candidates_name), None)
    cap_col  = next((c for c in df.columns if c.strip().lower() in candidates_cap), None)

    if name_col is None:
        # אם אין שם – נבחר עמודה ראשונה טקסטואלית
        name_col = df.columns[0]
    if cap_col is None:
        # אם אין קיבולת – נניח 1
        df["capacity"] = 1
        cap_col = "capacity"

    df.rename(columns={name_col: "site_name", cap_col: "capacity"}, inplace=True)
    out = pd.DataFrame({
        "site_name": df["site_name"].astype(str).apply(_strip),
        "capacity": pd.to_numeric(df["capacity"], errors="coerce").fillna(0).astype(int)
    })
    # השמט אתרים ללא שם/קיבולת
    out = out.dropna(subset=["site_name"])
    out = out[out["site_name"] != ""]
    out = out[out["capacity"] > 0]
    return out

def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame) -> pd.DataFrame:
    """
    Greedy: עבור כל סטודנט לפי הסדר, נלך על ההעדפות לפי הסדר,
    ונשבץ לאתר אם יש קיבולת > 0. אם לא נמצא – "ללא שיבוץ".
    """
    site_capacity = {row.site_name: int(row.capacity) for _, row in sites_df.iterrows()}
    assignments = []

    for _, s in students_df.iterrows():
        placed = None
        for pref in s.preferences:
            if pref in site_capacity and site_capacity[pref] > 0:
                placed = pref
                site_capacity[pref] -= 1
                break
        if placed is None:
            # אפשרות: לשבץ לאתר כלשהו עם מקום פנוי (Fallback) – כאן נשאיר "ללא שיבוץ"
            placed = "ללא שיבוץ"
        assignments.append({
            "student_id": s.student_id,
            "student_name": s.student_name,
            "assigned_site": placed
        })

    out = pd.DataFrame(assignments)
    # הוספת חיווי אם שובץ/לא
    out["status"] = out["assigned_site"].apply(lambda x: "שובץ" if x != "ללא שיבוץ" else "ממתין")
    return out

def load_default_df(path: Path) -> pd.DataFrame | None:
    try:
        if path.exists():
            return pd.read_csv(path)
    except Exception:
        return None
    return None

def df_to_csv_download(df: pd.DataFrame, filename: str) -> BytesIO:
    bio = BytesIO()
    df.to_csv(bio, index=False, encoding="utf-8-sig")
    bio.seek(0)
    return bio

# =========================
# סיידבר: העלאות + מצב מנהל
# =========================
with st.sidebar:
    st.header("העלאת נתונים")
    st.caption("ניתן להעלות קבצי ‎CSV‎ או להשתמש בדוגמאות אם קיימות בתיקייה.")

    up_students = st.file_uploader("סטודנטים (CSV)", type=["csv"], key="up_students")
    up_sites    = st.file_uploader("מדריכים/אתרים (CSV)", type=["csv"], key="up_sites")

    st.divider()
    st.subheader("מצב מנהל")
    admin = False
    with st.popover("כניסה למנהל"):
        pwd = st.text_input("סיסמה", type="password", help="ברירת מחדל מוגדרת בקוד", placeholder="••••••••")
        if st.button("אישור", use_container_width=True):
            admin = (pwd == ADMIN_PASSWORD)
            if admin:
                st.success("ברוכה הבאה, מנהלת ✅")
            else:
                st.error("סיסמה שגויה")

    st.divider()
    st.caption("טיפ: ודאי שלסטודנטים יש עמודת העדפות (Pref1, Pref2, ... או עמודת 'העדפות' עם פסיקים).")
    st.caption("לטבלת אתרים/מדריכים – ודאי שקיימות עמודות שם + קיבולת.")

# =========================
# טעינה/נירמול נתונים
# =========================
# סטודנטים
if up_students is not None:
    raw_students = pd.read_csv(up_students)
else:
    raw_students = load_default_df(DEFAULT_STUDENTS)

# אתרים
if up_sites is not None:
    raw_sites = pd.read_csv(up_sites)
else:
    raw_sites = load_default_df(DEFAULT_SITES)

col1, col2 = st.columns([1.1, 1])
with col1:
    st.title("🧮 מנגנון שיבוץ סטודנטים – עבודה סוציאלית")
    st.write("שיבוץ Greedy לפי סדר העדפות הסטודנט/ית ובכפוף לקיבולת המדריכים/האתרים.")

with col2:
    with st.container(border=True):
        st.markdown('<div class="kpi">', unsafe_allow_html=True)
        st.subheader("סטטוס נתונים")
        st.write(f"סטודנטים: **{0 if raw_students is None else len(raw_students)}**")
        st.write(f"מדריכים/אתרים: **{0 if raw_sites is None else len(raw_sites)}**")
        st.markdown("</div>", unsafe_allow_html=True)

st.divider()

tab_data, tab_match, tab_export = st.tabs(["📥 נתונים", "🧩 שיבוץ", "📤 ייצוא"])

# =========================
# לשונית נתונים
# =========================
with tab_data:
    st.subheader("טעינת טבלאות")
    if raw_students is None or raw_sites is None:
        st.warning("יש להעלות קובצי ‎CSV‎ לשתי הטבלאות (סטודנטים + אתרים/מדריכים), או להוסיף קבצים בסביבת הפרויקט בשם students.csv ו-sites.csv.", icon="⚠️")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**סטודנטים (Raw):**")
            st.dataframe(raw_students, use_container_width=True, height=360)
        with c2:
            st.markdown("**מדריכים/אתרים (Raw):**")
            st.dataframe(raw_sites, use_container_width=True, height=360)

        st.info("המערכת תנרמל את העמודות לשדות: student_id, student_name, preferences • site_name, capacity", icon="ℹ️")

# =========================
# לשונית שיבוץ
# =========================
with tab_match:
    st.subheader("הרצת שיבוץ Greedy")

    if raw_students is None or raw_sites is None:
        st.warning("לא נטענו שתי הטבלאות. יש להעלות סטודנטים ואתרים/מדריכים.", icon="⚠️")
    else:
        try:
            students_df = normalize_students_df(raw_students)
            sites_df    = normalize_sites_df(raw_sites)
        except Exception as e:
            st.error(f"שגיאה בנירמול הנתונים: {e}")
            st.stop()

        colA, colB = st.columns(2)
        with colA:
            st.markdown("**סטודנטים (Normalized):**")
            st.dataframe(students_df, use_container_width=True, height=320)
        with colB:
            st.markdown("**מדריכים/אתרים (Normalized):**")
            st.dataframe(sites_df, use_container_width=True, height=320)

        st.divider()
        go = st.button("🚀 בצעי שיבוץ", type="primary")
        if go:
            try:
                assignments = greedy_match(students_df, sites_df)
                st.success(f"שיבוץ הושלם – נמצאו הקצאות ל-{(assignments['status']=='שובץ').sum()} סטודנטים/ות.")
                st.dataframe(assignments, use_container_width=True, height=420)

                # KPI קטן
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("סה\"כ סטודנטים", len(assignments))
                with c2:
                    st.metric("שובצו", int((assignments["status"]=="שובץ").sum()))
                with c3:
                    st.metric("ממתינים", int((assignments["status"]=="ממתין").sum()))

                # שמירה בזיכרון סשן לייצוא
                st.session_state["assignments_df"] = assignments

            except Exception as e:
                st.error(f"שגיאה בהרצת השיבוץ: {e}")

# =========================
# לשונית ייצוא
# =========================
with tab_export:
    st.subheader("ייצוא assignments.csv")
    if "assignments_df" in st.session_state and isinstance(st.session_state["assignments_df"], pd.DataFrame):
        asg = st.session_state["assignments_df"].copy()
        # סדר עמודות נוח
        cols = ["student_id","student_name","assigned_site","status"]
        asg = asg[[c for c in cols if c in asg.columns]]

        st.dataframe(asg, use_container_width=True, height=420)

        fname = f"assignments_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        buff = df_to_csv_download(asg, fname)
        st.download_button("⬇️ הורדת הקובץ", buff, file_name=fname, mime="text/csv", use_container_width=True)

        if st.checkbox("שמור גם בשם הקבוע assignments.csv (לשילוב עם מערכות אחרות)"):
            try:
                asg.to_csv("assignments.csv", index=False, encoding="utf-8-sig")
                st.success("נשמר קובץ assignments.csv בתיקיית האפליקציה.")
            except Exception as e:
                st.error(f"נכשלה שמירה מקומית: {e}")
    else:
        # ייתכן שקיים assignments.csv בפרויקט – נציג אותו למעקב
        if DEFAULT_ASSIGN.exists():
            try:
                asg = pd.read_csv(DEFAULT_ASSIGN)
                st.info("נטען קובץ assignments.csv קיים (ברירת מחדל).")
                st.dataframe(asg, use_container_width=True, height=420)
                buff = df_to_csv_download(asg, "assignments.csv")
                st.download_button("⬇️ הורדת assignments.csv", buff, file_name="assignments.csv", mime="text/csv", use_container_width=True)
            except Exception as e:
                st.error(f"שגיאה בטעינת assignments.csv הקיים: {e}")
        else:
            st.warning("אין עדיין תוצאות שיבוץ להצגה/ייצוא. הריצי שיבוץ בלשונית ״🧩 שיבוץ״.", icon="⚠️")

# =========================
# אפשרויות מתקדמות למנהלת
# =========================
if admin:
    st.divider()
    st.subheader("כלים מתקדמים (מנהל)")

    st.markdown("""
    - בדיקות מהירות ו-Preview לקבצים שנמצאים בתיקייה (אם הועלו מראש).
    - התאמות קטנות לשמות עמודות, למשל אם ברירת המחדל לא קלטה נכון.
    """)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.write("students.csv קיים:", DEFAULT_STUDENTS.exists())
    with c2:
        st.write("sites.csv קיים:", DEFAULT_SITES.exists())
    with c3:
        st.write("assignments.csv קיים:", DEFAULT_ASSIGN.exists())

    with st.expander("תצוגת קבצים קיימים בתיקייה"):
        if DEFAULT_STUDENTS.exists():
            st.caption("students.csv")
            st.dataframe(pd.read_csv(DEFAULT_STUDENTS), use_container_width=True, height=240)
        if DEFAULT_SITES.exists():
            st.caption("sites.csv")
            st.dataframe(pd.read_csv(DEFAULT_SITES), use_container_width=True, height=240)
        if DEFAULT_ASSIGN.exists():
            st.caption("assignments.csv")
            st.dataframe(pd.read_csv(DEFAULT_ASSIGN), use_container_width=True, height=240)
