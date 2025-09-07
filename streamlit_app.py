# streamlit_app.py
import streamlit as st
import pandas as pd
from pathlib import Path
from io import BytesIO
from datetime import datetime

# =========================
# קבועים (לפי בקשתך)
# =========================
ADMIN_PASSWORD = "rawan_0304"
CSV_FILE = Path("Placement_data.csv")

# =========================
# הגדרות עמוד + עיצוב
# =========================
st.set_page_config(page_title="מערכת שיבוץ – ממשק מנהלים", layout="wide")

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
def read_any(upload):
    """
    קורא קובץ שהועלה (CSV/XLSX). אם XLSX ו-openpyxl לא מותקן – מציג שגיאה ידידותית.
    מחזיר DataFrame.
    """
    if upload is None:
        return None
    name = upload.name.lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(upload, encoding="utf-8-sig")
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            try:
                return pd.read_excel(upload, engine="openpyxl")
            except ImportError:
                st.error("לא מותקן openpyxl לקריאת אקסל. הוסיפו ל-requirements.txt: openpyxl, או העלו CSV.")
                return None
        else:
            st.error("סוג קובץ לא נתמך. העלו CSV או XLSX.")
            return None
    except Exception as e:
        st.error(f"שגיאה בקריאת הקובץ: {e}")
        return None

def normalize_students(df: pd.DataFrame) -> pd.DataFrame:
    """
    מנסה לזהות עמודות מזהה/שם והעדפות.
    תומך בשתי סקימות:
    1) עמודה אחת 'preferences' עם רשימה מופרדת בפסיק/נקודה-פסיק.
    2) עמודות pref1, pref2, ... או דירוג_1, דירוג_2 ...
    מחזיר DataFrame עם ['student_id','student_name','preferences'].
    """
    if df is None or df.empty:
        return pd.DataFrame()

    # נסיון למזהה ושם
    id_col = None
    for c in df.columns:
        c_low = str(c).strip().lower()
        if c_low in ("id","student_id","תעודת_זהות","תז","מזהה"):
            id_col = c
            break
    name_col = None
    for c in df.columns:
        c_low = str(c).strip().lower()
        if c_low in ("שם","שם מלא","student_name","name","שם_סטודנט","full_name"):
            name_col = c
            break

    if id_col is None:
        # אם אין מזהה – נבנה אחד זמני
        df["_tmp_id"] = range(1, len(df)+1)
        id_col = "_tmp_id"
    if name_col is None:
        # ננסה לחבר שם פרטי/משפחה אם קיימים
        fn = None; ln = None
        for c in df.columns:
            lc = str(c).strip().lower()
            if lc in ("שם פרטי","שם_פרטי","first_name","שם פרטי*"):
                fn = c
            if lc in ("שם משפחה","שם_משפחה","last_name","שם משפחה*"):
                ln = c
        if fn is not None or ln is not None:
            df["_tmp_name"] = (df.get(fn,"").astype(str).fillna("") + " " + df.get(ln,"").astype(str).fillna("")).str.strip()
            name_col = "_tmp_name"
        else:
            df["_tmp_name"] = df[id_col].astype(str)
            name_col = "_tmp_name"

    # איתור העדפות
    pref_cols = [c for c in df.columns if str(c).strip().lower().startswith(("pref","rank","דירוג","העדפה"))]
    has_single_prefs_col = any(str(c).strip().lower() in ("preferences","prefs","העדפות","תחומים_מועדפים","מקומות_מועדפים") for c in df.columns)

    prefs_series = None
    if has_single_prefs_col:
        col = next(c for c in df.columns if str(c).strip().lower() in ("preferences","prefs","העדפות","תחומים_מועדפים","מקומות_מועדפים"))
        prefs_series = (
            df[col].fillna("")
            .astype(str)
            .apply(lambda s: [x.strip() for x in s.replace(";", ",").split(",") if x.strip()])
        )
    elif pref_cols:
        # סדר לפי שם עמודה (pref1, pref2 ... / דירוג_1 ...)
        def extract_order(c):
            import re
            m = re.search(r"(\d+)", str(c))
            return int(m.group(1)) if m else 9999
        pref_cols_sorted = sorted(pref_cols, key=extract_order)
        prefs_series = df[pref_cols_sorted].fillna("").astype(str).apply(
            lambda row: [x.strip() for x in row.tolist() if str(x).strip() and str(x).strip() != "דלג"],
            axis=1
        )
    else:
        # אין מידע – נייצר ריק
        prefs_series = pd.Series([[] for _ in range(len(df))])

    out = pd.DataFrame({
        "student_id": df[id_col],
        "student_name": df[name_col].astype(str),
        "preferences": prefs_series
    })
    return out

def normalize_sites(df: pd.DataFrame) -> pd.DataFrame:
    """
    מצפה לעמודות: site / location / מקום ; capacity / קיבולת ; mentor / מדריך (לא חובה).
    מחזיר ['site','capacity','mentor'].
    """
    if df is None or df.empty:
        return pd.DataFrame()

    # מיפוי שמות עמודות גמיש
    site_col = None
    for c in df.columns:
        lc = str(c).strip().lower()
        if lc in ("site","location","מקום","שם מקום","שם_מקום","אתר","מוסד"):
            site_col = c; break
    cap_col = None
    for c in df.columns:
        lc = str(c).strip().lower()
        if lc in ("capacity","קיבולת","מכסה","מספר מקומות","קפסיטי"):
            cap_col = c; break
    mentor_col = None
    for c in df.columns:
        lc = str(c).strip().lower()
        if lc in ("mentor","מדריך","שם מדריך","שם_מדריך","מנחה"):
            mentor_col = c; break

    if site_col is None:
        # אם אין שם מקום – נוותר
        return pd.DataFrame()

    if cap_col is None:
        df["_tmp_capacity"] = 1
        cap_col = "_tmp_capacity"

    out = pd.DataFrame({
        "site": df[site_col].astype(str).str.strip(),
        "capacity": pd.to_numeric(df[cap_col], errors="coerce").fillna(0).astype(int)
    })
    if mentor_col is not None:
        out["mentor"] = df[mentor_col].astype(str)
    else:
        out["mentor"] = ""

    # רק אתרים עם קיבולת חיובית
    out = out[out["capacity"] > 0].reset_index(drop=True)
    return out

def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame) -> pd.DataFrame:
    """
    שיבוץ גרידי: עובר לפי סדר הסטודנטים, לכל סטודנט בודק העדפות לפי הסדר,
    ומצמיד לאתר הראשון שיש בו קיבולת. אם לא נמצא – מציין 'ללא שיבוץ'.
    מחזיר טבלה עם השיבוץ והדירוג שנבחר (rank).
    """
    if students_df.empty or sites_df.empty:
        return pd.DataFrame()

    capacity = {row.site: int(row.capacity) for _, row in sites_df.iterrows()}

    rows = []
    for _, s in students_df.iterrows():
        assigned_site = None
        assigned_rank = None

        prefs = s["preferences"] if isinstance(s["preferences"], list) else []
        for i, site in enumerate(prefs, start=1):
            if site in capacity and capacity[site] > 0:
                assigned_site = site
                assigned_rank = i
                capacity[site] -= 1
                break

        # אם לא שובץ לפי העדפות – ננסה למצוא מקום כלשהו פנוי (אופציונלי)
        if assigned_site is None:
            for site, cap in capacity.items():
                if cap > 0:
                    assigned_site = site
                    assigned_rank = None  # לא מתוך העדפות
                    capacity[site] -= 1
                    break

        rows.append({
            "student_id": s["student_id"],
            "student_name": s["student_name"],
            "assigned_site": assigned_site if assigned_site else "ללא שיבוץ",
            "assigned_rank": assigned_rank
        })

    return pd.DataFrame(rows)

def to_excel_bytes(df: pd.DataFrame, sheet_name="שיבוצים"):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name=sheet_name)
        ws = w.sheets[sheet_name]
        for i, col in enumerate(df.columns):
            width = min(60, max(12, int(df[col].astype(str).map(len).max() if not df.empty else 12) + 4))
            ws.set_column(i, i, width)
    buf.seek(0)
    return buf.getvalue()

# =========================
# אימות מנהל
# =========================
st.title("🧭 מערכת שיבוץ – ממשק מנהלים")
with st.expander("🔐 כניסת מנהל", expanded=True):
    pwd = st.text_input("סיסמה", type="password", value="")
    if pwd != ADMIN_PASSWORD:
        st.info("הכניסו את סיסמת המנהל כדי להמשיך.")
        st.stop()

# =========================
# טעינת קבצים
# =========================
st.markdown("#### 📥 טעינת קבצים")
c1, c2 = st.columns([1,1])

with c1:
    st.caption("קובץ סטודנטים (CSV/XLSX)")
    st.write("הקובץ צריך להכיל מזהה/שם והעדפות.\nאפשר: עמודה אחת `preferences` מופרדת בפסיקים/נקודה-פסיק, או עמודות `pref1,pref2,...`")
    students_file = st.file_uploader("בחר/י קובץ סטודנטים", type=["csv","xlsx","xls"], key="students")

with c2:
    st.caption("קובץ אתרים/מקומות (CSV/XLSX)")
    st.write("הקובץ צריך להכיל לפחות: `site`/`מקום` ו-`capacity`/`קיבולת`. עמודת `mentor`/`מדריך` רשות.")
    sites_file = st.file_uploader("בחר/י קובץ אתרים/מקומות", type=["csv","xlsx","xls"], key="sites")

students_raw = read_any(students_file) if students_file else None
sites_raw    = read_any(sites_file)    if sites_file    else None

if students_raw is not None:
    st.success(f"סטודנטים: נטען {len(students_raw):,} שורות")
    with st.expander("הצגת הקובץ הגולמי – סטודנטים"):
        st.dataframe(students_raw, use_container_width=True)

if sites_raw is not None:
    st.success(f"אתרים/מקומות: נטען {len(sites_raw):,} שורות")
    with st.expander("הצגת הקובץ הגולמי – אתרים/מקומות"):
        st.dataframe(sites_raw, use_container_width=True)

# =========================
# נרמול + שיבוץ
# =========================
if students_raw is not None and sites_raw is not None:
    students_df = normalize_students(students_raw)
    sites_df    = normalize_sites(sites_raw)

    if students_df.empty:
        st.error("לא זוהו סטודנטים/העדפות. ודאו את שמות העמודות בהתאם להנחיות.")
        st.stop()
    if sites_df.empty:
        st.error("לא זוהו אתרים/קיבולות. ודאו את שמות העמודות בהתאם להנחיות.")
        st.stop()

    st.markdown("### ⚙️ הגדרות שיבוץ")
    with st.expander("אפשרויות (אופציונלי)", expanded=False):
        fallback_any_site = st.checkbox("אם אין התאמה בהעדפות – לנסות לשבץ לכל אתר פנוי", value=True)

    # השיבוץ (האלגוריתם משתמש תמיד בניסיון למלא אתר פנוי אם אין העדפות—כבר מובנה בפונקציה)
    results = greedy_match(students_df, sites_df)

    # סטטיסטיקות קצרות
    total = len(results)
    matched = (results["assigned_site"] != "ללא שיבוץ").sum()
    st.success(f"בוצע שיבוץ ל־{matched:,} מתוך {total:,} סטודנטים ({matched/total:.0%}).")

    # הצגות
    st.markdown("### 📊 טבלת שיבוצים")
    st.dataframe(results, use_container_width=True, hide_index=True)

    st.markdown("### 🧑‍🏫 קיבולות לפי אתרים (לאחר שיבוץ)")
    # חישוב שימוש בקיבולת
    used = results[results["assigned_site"] != "ללא שיבוץ"].groupby("assigned_site").size().rename("used").reset_index()
    cap  = sites_df[["site","capacity"]]
    usage = cap.merge(used, left_on="site", right_on="assigned_site", how="left").drop(columns=["assigned_site"])
    usage["used"] = usage["used"].fillna(0).astype(int)
    usage["free"] = usage["capacity"] - usage["used"]
    st.dataframe(usage, use_container_width=True, hide_index=True)

    # שמירה אוטומטית לקובץ
    try:
        results_out = results.copy()
        results_out["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        results_out.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
        st.success(f"✅ נשמר לקובץ: {CSV_FILE.resolve()}")
    except Exception as e:
        st.warning(f"⚠️ לא הצלחתי לשמור ל־{CSV_FILE}: {e}")

    # הורדות
    st.markdown("### ⬇️ הורדות")
    cdl1, cdl2 = st.columns([1,1])
    with cdl1:
        st.download_button(
            "📥 הורדת שיבוצים (CSV)",
            data=results.to_csv(index=False, encoding="utf-8-sig"),
            file_name="placements.csv",
            mime="text/csv"
        )
    with cdl2:
        st.download_button(
            "📥 הורדת שיבוצים (Excel)",
            data=to_excel_bytes(results, sheet_name="שיבוצים"),
            file_name="placements.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("העלו שני קבצים (סטודנטים ואתרים) כדי לבצע שיבוץ.")
