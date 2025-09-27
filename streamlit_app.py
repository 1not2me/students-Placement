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


st.markdown("""
<style>
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
    "name": ["מוסד / שירות הכשרה", "מוסד", "שם מוסד ההתמחות", "שם המוסד", "מוסד ההכשרה"],
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
    out["שם המדריך"] = ""
    if sup_first or sup_last:
        ff = out[sup_first] if sup_first else ""
        ll = out[sup_last]  if sup_last else ""
        out["שם המדריך"] = (ff.astype(str) + " " + ll.astype(str)).str.strip()
    for c in ["site_name","site_field","site_city","שם המדריך"]:
        out[c] = out[c].apply(normalize_text)
    return out
 def compute_score(stu: pd.Series, site: pd.Series, W: Weights) -> float:
    # ===== תחום התמחות =====
    stu_field = str(stu.get("stu_pref", "")).strip().lower()
    site_field = str(site.get("site_field", "")).strip().lower()
    field_score = 0
    if stu_field and site_field:
        if stu_field == site_field:
            field_score = 100
        else:
            # נבדוק חפיפה בין מילים
            stu_words = set(stu_field.split())
            site_words = set(site_field.split())
            overlap = len(stu_words & site_words)
            total = max(len(stu_words), 1)
            field_score = (overlap / total) * 100  # אחוז חפיפה

    # ===== בקשות מיוחדות =====
    stu_req = str(stu.get("stu_req", "")).lower()
    site_req = str(site.get("בקשות מיוחדות", "")).lower()
    special_score = 50  # ברירת מחדל ניטרלית
    if stu_req and stu_req != "אין":
        if "קרוב" in stu_req and stu.get("stu_city") == site.get("site_city"):
            special_score = 100
        elif "נגיש" in stu_req and "נגיש" in site_req:
            special_score = 100
        else:
            special_score = 0

    # ===== עיר =====
    stu_city = str(stu.get("stu_city", "")).strip()
    site_city = str(site.get("site_city", "")).strip()
    city_score = 100 if stu_city and site_city and stu_city == site_city else 0

    # ===== ניקוד סופי =====
    score = (
        W.w_field * field_score +
        W.w_special * special_score +
        W.w_city * city_score
    )

    return round(float(score), 1)


# ====== שיבוץ ======
def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    results = []
    supervisor_count = {}

    for _, s in students_df.iterrows():
        cand = sites_df[sites_df["capacity_left"] > 0].copy()
        if cand.empty:
            results.append({
                "ת\"ז הסטודנט": s["stu_id"],
                "שם פרטי": s["stu_first"],
                "שם משפחה": s["stu_last"],
                "שם מקום ההתמחות": "לא שובץ",
                "עיר המוסד": "",
                "תחום ההתמחות במוסד": "",
                "שם המדריך": "",
                "אחוז התאמה": 0
            })
            continue

        # ✅ חישוב ציון התאמה עם compute_match במקום compute_score
        cand["score"] = cand.apply(lambda r: compute_match(s, r, W.w_field, W.w_special, W.w_city), axis=1)

        def allowed_supervisor(r):
            sup = r.get("שם המדריך", "")
            return supervisor_count.get(sup, 0) < 2

        cand = cand[cand.apply(allowed_supervisor, axis=1)]

        if cand.empty:
            all_sites = sites_df[sites_df["capacity_left"] > 0].copy()
            if all_sites.empty:
                results.append({
                    "ת\"ז הסטודנט": s["stu_id"],
                    "שם פרטי": s["stu_first"],
                    "שם משפחה": s["stu_last"],
                    "שם מקום ההתמחות": "לא שובץ",
                    "עיר המוסד": "",
                    "תחום ההתמחות במוסד": "",
                    "שם המדריך": "",
                    "אחוז התאמה": 0
                })
                continue

            all_sites["score"] = all_sites.apply(lambda r: compute_match(s, r, W.w_field, W.w_special, W.w_city), axis=1)
            cand = all_sites.sort_values("score", ascending=False).head(1)
        else:
            cand = cand.sort_values("score", ascending=False)

        chosen = cand.iloc[0]
        idx = chosen.name
        sites_df.at[idx, "capacity_left"] -= 1

        sup_name = chosen.get("שם המדריך", "")
        supervisor_count[sup_name] = supervisor_count.get(sup_name, 0) + 1

        results.append({
            "ת\"ז הסטודנט": s["stu_id"],
            "שם פרטי": s["stu_first"],
            "שם משפחה": s["stu_last"],
            "שם מקום ההתמחות": chosen["site_name"],
            "עיר המוסד": chosen.get("site_city", ""),
            "תחום ההתמחות במוסד": chosen["site_field"],
            "שם המדריך": sup_name,
            "אחוז התאמה": round(chosen["score"], 1)
        })

    return pd.DataFrame(results)

# ---- יצירת XLSX ----
def df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "שיבוץ") -> bytes:
    xlsx_io = BytesIO()
    import xlsxwriter
    with pd.ExcelWriter(xlsx_io, engine="xlsxwriter") as writer:
        cols = list(df.columns)
        has_match_col = "אחוז התאמה" in cols
        if has_match_col:
            cols = [c for c in cols if c != "אחוז התאמה"] + ["אחוז התאמה"]

        df[cols].to_excel(writer, index=False, sheet_name=sheet_name)

        if has_match_col:
            workbook  = writer.book
            worksheet = writer.sheets[sheet_name]
            red_fmt = workbook.add_format({"font_color": "red"})
            col_idx = len(cols) - 1
            worksheet.set_column(col_idx, col_idx, 12, red_fmt)
    xlsx_io.seek(0)
    return xlsx_io.getvalue()

# =========================
# שיבוץ והצגת תוצאות
# =========================
if "result_df" not in st.session_state:
    st.session_state["result_df"] = None

st.markdown("## ⚙️ ביצוע השיבוץ")
if st.button("🚀 בצע שיבוץ", use_container_width=True):
    try:
        students = resolve_students(st.session_state["df_students_raw"])
        sites    = resolve_sites(st.session_state["df_sites_raw"])
        result_df = greedy_match(students, sites, Weights())
        st.session_state["result_df"] = result_df
        st.success("השיבוץ הושלם ✓")
    except Exception as e:
        st.exception(e)

if isinstance(st.session_state["result_df"], pd.DataFrame) and not st.session_state["result_df"].empty:
    st.markdown("## 📊 תוצאות השיבוץ")

    df_show = st.session_state["result_df"].copy()

    # העברת תחום ההתמחות אחרי שם מקום ההתמחות
    cols = list(df_show.columns)
    if "תחום ההתמחות במוסד" in cols and "שם מקום ההתמחות" in cols:
        cols.insert(cols.index("שם מקום ההתמחות")+1, cols.pop(cols.index("תחום ההתמחות במוסד")))
        df_show = df_show[cols]

    st.dataframe(df_show, use_container_width=True)

    # הורדת קובץ תוצאות
    xlsx_results = df_to_xlsx_bytes(df_show, sheet_name="תוצאות")
    st.download_button("⬇️ הורדת XLSX – תוצאות השיבוץ", data=xlsx_results,
        file_name="student_site_matching.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- טבלת סיכום ---
    summary_df = (
        st.session_state["result_df"]
        .groupby(["שם מקום ההתמחות","תחום ההתמחות במוסד","שם המדריך"])
        .agg({
            "ת\"ז הסטודנט":"count",
            "שם פרטי": list,
            "שם משפחה": list
        }).reset_index()
    )
    summary_df.rename(columns={"ת\"ז הסטודנט":"כמה סטודנטים"}, inplace=True)

    # המלצת שיבוץ – שם מלא
    summary_df["המלצת שיבוץ"] = summary_df.apply(
        lambda row: " + ".join([f"{f} {l}" for f, l in zip(row["שם פרטי"], row["שם משפחה"])]),
        axis=1
    )

    summary_df = summary_df[[
        "שם מקום ההתמחות",
        "תחום ההתמחות במוסד",
        "שם המדריך",
        "כמה סטודנטים",
        "המלצת שיבוץ"
    ]]

    st.markdown("### 📝 טבלת סיכום לפי מקום הכשרה")
    st.dataframe(summary_df, use_container_width=True)

    xlsx_summary = df_to_xlsx_bytes(summary_df, sheet_name="סיכום")
    st.download_button("⬇️ הורדת XLSX – טבלת סיכום", data=xlsx_summary,
        file_name="student_site_summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
