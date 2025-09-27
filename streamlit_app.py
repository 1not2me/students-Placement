# matcher_streamlit_beauty_rtl_v7_fixed.py 
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from dataclasses import dataclass
from typing import Optional, Any, List

# =========================
# קונפיגורציה כללית
# =========================
st.set_page_config(page_title="מערכת שיבוץ סטודנטים – התאמה חכמה", layout="wide")

# ====== CSS – עיצוב מודרני + RTL ======
st.markdown("""
<style>
/* טעינת פונט עברי מגוגל (אפשר לשנות ל-Assistant, Heebo, Varela Round וכו') */
@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;600&display=swap');

html, body, [class*="css"] { 
  font-family: 'Rubik', 'David', sans-serif !important; 
}

:root{
  --bg-1:#e0f7fa;
  --bg-2:#ede7f6;
  --bg-3:#fff3e0;
  --bg-4:#fce4ec;
  --bg-5:#e8f5e9;
  --ink:#0f172a;
  --primary:#9b5de5;
  --primary-700:#f15bb5;
  --ring:rgba(155,93,229,.35);
}

[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 15% 10%, var(--bg-2) 0%, transparent 70%),
    radial-gradient(1000px 700px at 85% 20%, var(--bg-3) 0%, transparent 70%),
    radial-gradient(900px 500px at 50% 80%, var(--bg-4) 0%, transparent 70%),
    radial-gradient(700px 400px at 10% 85%, var(--bg-5) 0%, transparent 70%),
    linear-gradient(135deg, var(--bg-1) 0%, #ffffff 100%) !important;
  color: var(--ink);
}

.main .block-container{
  background: rgba(255,255,255,.78);
  backdrop-filter: blur(10px);
  border:1px solid rgba(15,23,42,.08);
  box-shadow:0 15px 35px rgba(15,23,42,.08);
  border-radius:24px;
  padding:2.5rem;
  margin-top:1rem;
}

h1,h2,h3,.stMarkdown h1,.stMarkdown h2{
  text-align:center;
  letter-spacing:.5px;
  text-shadow:0 1px 2px rgba(255,255,255,.7);
  font-weight:700;
  color:#222;
  margin-bottom:1rem;
}

.stButton > button,
div[data-testid="stDownloadButton"] > button{
  background:linear-gradient(135deg,var(--primary) 0%,var(--primary-700) 100%)!important;
  color:#fff!important;
  border:none!important;
  border-radius:18px!important;
  padding:1rem 2rem!important;
  font-size:1.1rem!important;
  font-weight:600!important;
  box-shadow:0 8px 18px var(--ring)!important;
  transition:all .15s ease!important;
  width:100% !important;
}
.stButton > button:hover,
div[data-testid="stDownloadButton"] > button:hover{ 
  transform:translateY(-3px) scale(1.02); 
  filter:brightness(1.08); 
}
.stButton > button:focus,
div[data-testid="stDownloadButton"] > button:focus{ 
  outline:none!important; 
  box-shadow:0 0 0 4px var(--ring)!important; 
}

.stApp,.main,[data-testid="stSidebar"]{ direction:rtl; text-align:right; }
label,.stMarkdown,.stText,.stCaption{ text-align:right!important; }
</style>
""", unsafe_allow_html=True)
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700&family=Noto+Sans+Hebrew:wght@400;600&display=swap" rel="stylesheet">

<style>
:root { --app-font: 'Assistant', 'Noto Sans Hebrew', 'Segoe UI', -apple-system, sans-serif; }

/* בסיס האפליקציה */
html, body, .stApp, [data-testid="stAppViewContainer"], .main {
  font-family: var(--app-font) !important;
}

/* ודא שכל הצאצאים יורשים את הפונט */
.stApp * {
  font-family: var(--app-font) !important;
}

/* רכיבי קלט/בחירה של Streamlit */
div[data-baseweb], /* select/radio/checkbox */
.stTextInput input,
.stTextArea textarea,
.stSelectbox div,
.stMultiSelect div,
.stRadio,
.stCheckbox,
.stButton > button {
  font-family: var(--app-font) !important;
}

/* טבלאות DataFrame/Arrow */
div[data-testid="stDataFrame"] div {
  font-family: var(--app-font) !important;
}

/* כותרות */
h1, h2, h3, h4, h5, h6 {
  font-family: var(--app-font) !important;
}
</style>
""", unsafe_allow_html=True)

# ====== כותרת ======
st.markdown("<h1>מערכת שיבוץ סטודנטים – התאמה חכמה</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#475569;margin-top:-8px;'>כאן משבצים סטודנטים למקומות התמחות בקלות, בהתבסס על תחום, עיר ובקשות.</p>", unsafe_allow_html=True)

# ====== מודל ניקוד ======
@dataclass
class Weights:
    w_field: float = 0.50
    w_city: float = 0.05
    w_special: float = 0.45

# עמודות סטודנטים
STU_COLS = {
    "id": ["מספר תעודת זהות", "תעודת זהות", "ת\"ז", "תז", "תעודת זהות הסטודנט"],
    "first": ["שם פרטי"],
    "last": ["שם משפחה"],
    "address": ["כתובת", "כתובת הסטודנט", "רחוב"],
    "city": ["עיר מגורים", "עיר"],
    "phone": ["טלפון", "מספר טלפון"],
    "email": ["דוא\"ל", "דוא״ל", "אימייל", "כתובת אימייל", "כתובת מייל"],
    "preferred_field": ["תחום מועדף","תחומים מועדפים"],
    "special_req": ["בקשה מיוחדת"],
    "partner": ["בן/בת זוג להכשרה", "בן\\בת זוג להכשרה", "בן/בת זוג", "בן\\בת זוג"]
}

# עמודות אתרים
SITE_COLS = {
    "name": ["מוסד / שירות הכשרה", "מוסד", "שם מוסד ההתמחות"],
    "field": ["תחום ההתמחות", "תחום התמחות"],
    "street": ["רחוב"],
    "city": ["עיר"],
    "capacity": ["מספר סטודנטים שניתן לקלוט השנה", "מספר סטודנטים שניתן לקלוט", "קיבולת"],
    "sup_first": ["שם פרטי"],
    "sup_last": ["שם משפחה"],
    "phone": ["טלפון"],
    "email": ["אימייל", "כתובת מייל", "דוא\"ל", "דוא״ל"],
    "review": ["חוות דעת מדריך"]
}

def pick_col(df: pd.DataFrame, options: List[str]) -> Optional[str]:
    for opt in options:
        if opt in df.columns: return opt
    return None

# ----- קריאת קבצים -----
def read_any(uploaded) -> pd.DataFrame:
    name = (uploaded.name or "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded, encoding="utf-8-sig")
    if name.endswith((".xlsx",".xls")):
        return pd.read_excel(uploaded)
    return pd.read_csv(uploaded, encoding="utf-8-sig")

def normalize_text(x: Any) -> str:
    if x is None: return ""
    return str(x).strip()

# ----- סטודנטים -----
def resolve_students(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["stu_id"] = out[pick_col(out, STU_COLS["id"])]
    out["stu_first"] = out[pick_col(out, STU_COLS["first"])]
    out["stu_last"]  = out[pick_col(out, STU_COLS["last"])]
    out["stu_city"]  = out[pick_col(out, STU_COLS["city"])] if pick_col(out, STU_COLS["city"]) else ""
    out["stu_pref"]  = out[pick_col(out, STU_COLS["preferred_field"])] if pick_col(out, STU_COLS["preferred_field"]) else ""
    out["stu_req"]   = out[pick_col(out, STU_COLS["special_req"])] if pick_col(out, STU_COLS["special_req"]) else ""
    for c in ["stu_id","stu_first","stu_last","stu_city","stu_pref","stu_req"]:
        out[c] = out[c].apply(normalize_text)
    return out

# ----- אתרים -----
def resolve_sites(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["site_name"]  = out[pick_col(out, SITE_COLS["name"])]
    out["site_field"] = out[pick_col(out, SITE_COLS["field"])]
    out["site_city"]  = out[pick_col(out, SITE_COLS["city"])]
    cap_col = pick_col(out, SITE_COLS["capacity"])
    out["site_capacity"] = pd.to_numeric(out[cap_col], errors="coerce").fillna(1).astype(int) if cap_col else 1
    out["capacity_left"] = out["site_capacity"].astype(int)
    sup_first = pick_col(out, SITE_COLS["sup_first"])
    sup_last  = pick_col(out, SITE_COLS["sup_last"])
    out["supervisor"] = ""
    if sup_first or sup_last:
        ff = out[sup_first] if sup_first else ""
        ll = out[sup_last]  if sup_last else ""
        out["supervisor"] = (ff.astype(str) + " " + ll.astype(str)).str.strip()
    for c in ["site_name","site_field","site_city","supervisor"]:
        out[c] = out[c].apply(normalize_text)
    return out

# ====== חישוב ציון ======
def compute_score(stu: pd.Series, site: pd.Series, W: Weights) -> float:
    same_city = (stu.get("stu_city") and site.get("site_city") and stu.get("stu_city") == site.get("site_city"))
    field_s   = 90.0 if stu.get("stu_pref") and stu.get("stu_pref") in site.get("site_field","") else 60.0
    city_s    = 100.0 if same_city else 65.0
    special_s = 90.0 if "קרוב" in stu.get("stu_req","") and same_city else 70.0
    score = W.w_field*field_s + W.w_city*city_s + W.w_special*special_s
    return float(np.clip(score, 0, 100))

# =========================
# 1) הוראות שימוש
# =========================
st.markdown("## 📘 הוראות שימוש")
st.markdown("""
1. **קובץ סטודנטים (CSV/XLSX):** שם פרטי, שם משפחה, תעודת זהות, כתובת/עיר, טלפון, אימייל.  
   אופציונלי: תחום מועדף, בקשה מיוחדת, בן/בת זוג להכשרה.  
2. **קובץ אתרים/מדריכים (CSV/XLSX):** מוסד/שירות, תחום התמחות, רחוב, עיר, מספר סטודנטים שניתן לקלוט השנה, מדריך, חוות דעת מדריך.  
3. **בצע שיבוץ** מחשב *אחוז התאמה* לפי תחום (50%), בקשות מיוחדות (45%), עיר (5%). 
4. בסוף אפשר להוריד **XLSX**. 
""")

# =========================
# 2) דוגמה לשימוש
# =========================
st.markdown("## 🧪 דוגמה לשימוש")
example_students = pd.DataFrame([
    {"שם פרטי":"רות", "שם משפחה":"כהן", "תעודת זהות":"123456789", "עיר מגורים":"תל אביב", "טלפון":"0501111111", "דוא\"ל":"ruth@example.com", "תחום מועדף":"בריאות הנפש", "בקשה מיוחדת":"קרוב לבית"},
    {"שם פרטי":"יואב", "שם משפחה":"לוי", "תעודת זהות":"987654321", "עיר מגורים":"חיפה", "טלפון":"0502222222", "דוא\"ל":"yoav@example.com", "תחום מועדף":"רווחה"},
    {"שם פרטי":"סמאח", "שם משפחה":"ח'ורי", "תעודת זהות":"456789123", "עיר מגורים":"עכו", "טלפון":"0503333333", "דוא\"ל":"sama@example.com", "תחום מועדף":"חינוך מיוחד"},
])
example_sites = pd.DataFrame([
    {"מוסד / שירות הכשרה":"מרכז חוסן תל אביב", "תחום ההתמחות":"בריאות הנפש", "עיר":"תל אביב", "מספר סטודנטים שניתן לקלוט השנה":2, "שם פרטי":"דניאל", "שם משפחה":"כהן", "חוות דעת מדריך":"מדריך מצוין"},
    {"מוסד / שירות הכשרה":"מחלקת רווחה חיפה", "תחום ההתמחות":"רווחה", "עיר":"חיפה", "מספר סטודנטים שניתן לקלוט השנה":1, "שם פרטי":"מיכל", "שם משפחה":"לוי", "חוות דעת מדריך":"זקוקה לשיפור"},
    {"מוסד / שירות הכשרה":"בית ספר יד לבנים", "תחום ההתמחות":"חינוך מיוחד", "עיר":"עכו", "מספר סטודנטים שניתן לקלוט השנה":1, "שם פרטי":"שרה", "שם משפחה":"כהן"},
])
colX, colY = st.columns(2, gap="large")
with colX:
    st.write("**דוגמה – סטודנטים**")
    st.dataframe(example_students, use_container_width=True)
with colY:
    st.write("**דוגמה – אתרי התמחות/מדריכים**")
    st.dataframe(example_sites, use_container_width=True)

# =========================
# 3) העלאת קבצים
# =========================
st.markdown("## 📤 העלאת קבצים")
colA, colB = st.columns(2, gap="large")

with colA:
    students_file = st.file_uploader("קובץ סטודנטים", type=["csv","xlsx","xls"], key="students_file")
    if students_file is not None:
        try:
            st.session_state["df_students_raw"] = read_any(students_file)
            st.dataframe(st.session_state["df_students_raw"].head(5), use_container_width=True)
        except Exception as e:
            st.error(f"לא ניתן לקרוא את קובץ הסטודנטים: {e}")

with colB:
    sites_file = st.file_uploader("קובץ אתרי התמחות/מדריכים", type=["csv","xlsx","xls"], key="sites_file")
    if sites_file is not None:
        try:
            st.session_state["df_sites_raw"] = read_any(sites_file)
            st.dataframe(st.session_state["df_sites_raw"].head(5), use_container_width=True)
        except Exception as e:
            st.error(f"לא ניתן לקרוא את קובץ האתרים/מדריכים: {e}")

for k in ["df_students_raw","df_sites_raw","result_df","unmatched_students","unused_sites"]:
    st.session_state.setdefault(k, None)

# ====== שיבוץ ======
def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    results = []
    for _, s in students_df.iterrows():
        cand = sites_df[sites_df["capacity_left"]>0].copy()
        cand["score"] = cand.apply(lambda r: compute_score(s, r, W), axis=1)
        cand = cand.sort_values("score", ascending=False)
        if cand.empty:
            results.append({
                "ת\"ז הסטודנט": s["stu_id"],
                "שם פרטי": s["stu_first"],
                "שם משפחה": s["stu_last"],
                "שם מקום ההתמחות": "לא שובץ",
                "עיר המוסד": "",
                "תחום ההתמחות במוסד": "",
                "מדריך": "",
                "אחוז התאמה": 0
            })
        else:
            chosen = cand.iloc[0]
            idx = chosen.name
            sites_df.at[idx, "capacity_left"] -= 1
            results.append({
                "ת\"ז הסטודנט": s["stu_id"],
                "שם פרטי": s["stu_first"],
                "שם משפחה": s["stu_last"],
                "שם מקום ההתמחות": chosen["site_name"],
                "תחום ההתמחות במוסד": chosen["site_field"],
                "עיר המוסד": chosen.get("site_city","")
                "שם המדריך": chosen["supervisor"],
                "אחוז התאמה": round(chosen["score"],1)
            })
    return pd.DataFrame(results)
# ---- יצירת XLSX ----
def df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "שיבוץ") -> bytes:
    xlsx_io = BytesIO()
    import xlsxwriter
    with pd.ExcelWriter(xlsx_io, engine="xlsxwriter") as writer:
        cols = list(df.columns)

        # סדר העמודות: ת"ז, שם פרטי, שם משפחה -> שאר העמודות -> אחוז התאמה (בסוף)
        ordered_cols = []
        for c in ["ת\"ז הסטודנט", "שם פרטי", "שם משפחה"]:
            if c in cols:
                ordered_cols.append(c)

        middle_cols = [c for c in cols if c not in ordered_cols and c != "אחוז התאמה"]
        ordered_cols += middle_cols
        if "אחוז התאמה" in cols:
            ordered_cols.append("אחוז התאמה")

        df[ordered_cols].to_excel(writer, index=False, sheet_name=sheet_name)

        if "אחוז התאמה" in ordered_cols:
            workbook  = writer.book
            worksheet = writer.sheets[sheet_name]
            red_fmt = workbook.add_format({"font_color": "red"})
            col_idx = ordered_cols.index("אחוז התאמה")
            worksheet.set_column(col_idx, col_idx, 12, red_fmt)

    xlsx_io.seek(0)
    return xlsx_io.getvalue()
