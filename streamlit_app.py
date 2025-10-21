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

# ====== חישוב ציון ======
def compute_score(stu: pd.Series, site: pd.Series, W: Weights) -> float:
    same_city = (stu.get("stu_city") and site.get("site_city") and stu.get("stu_city") == site.get("site_city"))
    field_s   = 90.0 if stu.get("stu_pref") and stu.get("stu_pref") in site.get("site_field","") else 60.0
    city_s    = 100.0 if same_city else 65.0
    special_s = 90.0 if "קרוב" in stu.get("stu_req","") and same_city else 70.0
    score = W.w_field*field_s + W.w_city*city_s + W.w_special*special_s
    return float(np.clip(score, 0, 100))

# --- גרסה עם פירוט מרכיבים (לשבירת הציון) ---
def compute_score_with_explain(stu: pd.Series, site: pd.Series, W: Weights):
    same_city = (stu.get("stu_city") and site.get("site_city") and stu.get("stu_city") == site.get("site_city"))
    field_s   = 90.0 if stu.get("stu_pref") and stu.get("stu_pref") in site.get("site_field","") else 60.0
    city_s    = 100.0 if same_city else 65.0
    special_s = 90.0 if "קרוב" in stu.get("stu_req","") and same_city else 70.0

    parts = {
        "התאמת תחום": round(W.w_field*field_s),
        "מרחק/גיאוגרפיה": round(W.w_city*city_s),
        "בקשות מיוחדות": round(W.w_special*special_s),
        "עדיפויות הסטודנט/ית": 0  # אין קלט דירוג מפורש בקובץ זה; נשאר 0 לשקיפות
    }
    score = int(np.clip(sum(parts.values()), 0, 100))
    return score, parts

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
    supervisor_count = {}  # מונים פר-מדריך (דוגמה: עד 2 סטודנטים לכל מדריך)

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
                "אחוז התאמה": 0,
                "_expl": {"התאמת תחום":0,"מרחק/גיאוגרפיה":0,"בקשות מיוחדות":0,"עדיפויות הסטודנט/ית":0}
            })
            continue

        # חישוב ציון + פירוק רכיבים
        cand[["score","_parts"]] = cand.apply(
            lambda r: pd.Series(compute_score_with_explain(s, r, W)),
            axis=1
        )

        # סינון לפי מדריך: מותר עד 2 סטודנטים לכל מדריך (ניתן לשנות לפי צורך)
        def allowed_supervisor(r):
            sup = r.get("שם המדריך", "")
            return supervisor_count.get(sup, 0) < 2

        cand = cand[cand.apply(allowed_supervisor, axis=1)]

        if cand.empty:
            # אם אין מדריכים פנויים – נבחר את האתר עם הציון הגבוה ביותר מבין הזמינים לפני הסינון
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
                    "אחוז התאמה": 0,
                    "_expl": {"התאמת תחום":0,"מרחק/גיאוגרפיה":0,"בקשות מיוחדות":0,"עדיפויות הסטודנט/ית":0}
                })
                continue

            all_sites[["score","_parts"]] = all_sites.apply(
                lambda r: pd.Series(compute_score_with_explain(s, r, W)),
                axis=1
            )
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
            # >>> דרישת המרצים: אחוז התאמה מספר שלם
            "אחוז התאמה": int(chosen["score"]),
            "_expl": chosen["_parts"]
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
colM1, colM2 = st.columns([2,1], gap="large")
with colM1:
    run_match = st.button("🚀 בצע שיבוץ", use_container_width=True)
with colM2:
    MATCH_THRESHOLD = st.slider("סף התאמה (אחוזים) – מתחת לסף: בדיקה ידנית", min_value=0, max_value=100, value=70, step=1)

if run_match:
    try:
        students = resolve_students(st.session_state["df_students_raw"])
        sites    = resolve_sites(st.session_state["df_sites_raw"])
        result_df = greedy_match(students, sites, Weights())
        st.session_state["result_df"] = result_df
        # נשמור גם עותק של ה"sites" כדי להשתמש לקיבולות
        st.session_state["sites_after"] = sites
        st.success("השיבוץ הושלם ✓")
    except Exception as e:
        st.exception(e)

if isinstance(st.session_state["result_df"], pd.DataFrame) and not st.session_state["result_df"].empty:
    st.markdown("## 📊 תוצאות השיבוץ")

    base_df = st.session_state["result_df"].copy()

    # ---- בניית טבלת התוצאות המרכזית לפי סדר/תוויות המרצים ----
    df_show = pd.DataFrame({
        "אחוז התאמה": base_df["אחוז התאמה"].astype(int),
        "שם הסטודנט/ית": (base_df["שם פרטי"].astype(str) + " " + base_df["שם משפחה"].astype(str)).str.strip(),
        "תעודת זהות": base_df["ת\"ז הסטודנט"],
        "תחום התמחות": base_df["תחום ההתמחות במוסד"],
        "עיר המוסד": base_df["עיר המוסד"],
        "שם מקום ההתמחות": base_df["שם מקום ההתמחות"],
        "שם המדריך/ה": base_df["שם המדריך"],
    })

    # מיון מהגבוה לנמוך + סטטוס סף
    df_show = df_show.sort_values("אחוז התאמה", ascending=False)
    df_show["סטטוס"] = df_show["אחוז התאמה"].apply(lambda v: "⚠ דורש בדיקה ידנית" if v < MATCH_THRESHOLD else "תקין")

    st.markdown("### טבלת תוצאות מרכזית")
    st.dataframe(df_show, use_container_width=True)

    # הורדת קובץ תוצאות (בדיוק העמודות שנראות)
    xlsx_results = df_to_xlsx_bytes(df_show, sheet_name="תוצאות")
    st.download_button("⬇️ הורדת XLSX – תוצאות השיבוץ", data=xlsx_results,
        file_name="student_site_matching.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- הסבר ציון (שבירת התאמה) ---
    st.markdown("### 🧩 הסבר ציון – שבירת התאמה")
    idx_max = len(base_df) - 1
    ex_idx = st.number_input("בחר/י שורה להסבר (0..):", min_value=0, max_value=idx_max, value=0, step=1)
    try:
        expl = base_df.iloc[int(ex_idx)]["_expl"]
        ex_df = pd.DataFrame({
            "מרכיב": ["מרחק/גיאוגרפיה","התאמת תחום","עדיפויות הסטודנט/ית","בקשות מיוחדות"],
            "תרומה": [expl.get("מרחק/גיאוגרפיה",0), expl.get("התאמת תחום",0), expl.get("עדיפויות הסטודנט/ית",0), expl.get("בקשות מיוחדות",0)]
        })
        ex_df.loc[len(ex_df.index)] = {"מרכיב": "סה\"כ", "תרומה": int(base_df.iloc[int(ex_idx)]["אחוז התאמה"])}
        st.table(ex_df)
    except Exception:
        st.info("אין נתוני הסבר לציון עבור השורה שנבחרה.")

    # --- דוח סיכום לפי מקום הכשרה (כמות/שמות) ---
    st.markdown("### 📝 טבלת סיכום לפי מקום הכשרה")
    summary_df = (
        base_df
        .groupby(["שם מקום ההתמחות","תחום ההתמחות במוסד","שם המדריך"])
        .agg({
            "ת\"ז הסטודנט":"count",
            "שם פרטי": list,
            "שם משפחה": list
        }).reset_index()
    )
    summary_df.rename(columns={"ת\"ז הסטודנט":"כמה סטודנטים"}, inplace=True)
    summary_df["המלצת שיבוץ"] = summary_df.apply(
        lambda row: " + ".join([f"{f} {l}" for f, l in zip(row["שם פרטי"], row["שם משפחה"])]),
        axis=1
    )
    summary_df = summary_df[[
        "שם miejsce ההתמחות".replace("miejsce","מקום"),  # הגנה קטנה מפני קידוד דפדפן
        "תחום ההתמחות במוסד",
        "שם המדריך",
        "כמה סטודנטים",
        "המלצת שיבוץ"
    ]].rename(columns={"שם miejsce ההתמחות".replace("miejsce","מקום"): "שם מקום ההתמחות"})

    st.dataframe(summary_df, use_container_width=True)
    xlsx_summary = df_to_xlsx_bytes(summary_df, sheet_name="סיכום")
    st.download_button("⬇️ הורדת XLSX – טבלת סיכום", data=xlsx_summary,
        file_name="student_site_summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # --- דוח קיבולות: קיבולת/שובצו/יתרה ---
    st.markdown("### 🏷️ דוח קיבולות לפי מקום הכשרה")
    sites_after = st.session_state.get("sites_after", None)
    if isinstance(sites_after, pd.DataFrame) and not sites_after.empty:
        caps = sites_after.groupby("site_name")["site_capacity"].sum().to_dict()
        assigned = base_df.groupby("שם מקום ההתמחות")["ת\"ז הסטודנט"].count().to_dict()
        cap_rows = []
        for site, capacity in caps.items():
            used = int(assigned.get(site, 0))
            cap_rows.append({
                "שם מקום ההתמחות": site,
                "קיבולת": int(capacity),
                "שובצו בפועל": used,
                "יתרה/חוסר": int(capacity - used)
            })
        cap_df = pd.DataFrame(cap_rows).sort_values("שם מקום ההתמחות")
        st.dataframe(cap_df, use_container_width=True)

        # הדגשה טקסטואלית
        under = cap_df[cap_df["יתרה/חוסר"] > 0]
        over  = cap_df[cap_df["יתרה/חוסר"] < 0]
        if not under.empty:
            st.info("מוסדות עם מקומות פנויים:\n- " + "\n- ".join(under["שם מקום ההתמחות"].tolist()))
        if not over.empty:
            st.error("מוסדות עם חריגה (עודף שיבוץ):\n- " + "\n- ".join(over["שם מקום ההתמחות"].tolist()))
    else:
        st.info("לא נמצאו נתוני קיבולת לשיבוץ זה.")

    # --- דוח ריכוזי פר־מורה ---
    st.markdown("### 👩‍🏫 דוח פר־מורה שיטות")
    teachers_list = ["(כולם)"] + sorted([x for x in base_df["שם המדריך"].unique() if str(x).strip() != ""])
    pick_teacher = st.selectbox("סינון לפי מורה:", teachers_list, index=0)
    df_for_teacher = base_df.copy()
    if pick_teacher != "(כולם)":
        df_for_teacher = df_for_teacher[df_for_teacher["שם המדריך"] == pick_teacher]
    # רשימת הסטודנטים + ניצול קיבולת לאותם מוסדות
    st.dataframe(
        pd.DataFrame({
            "שם הסטודנט/ית": (df_for_teacher["שם פרטי"].astype(str) + " " + df_for_teacher["שם משפחה"].astype(str)).str.strip(),
            "תעודת זהות": df_for_teacher["ת\"ז הסטודנט"],
            "שם מקום ההתמחות": df_for_teacher["שם מקום ההתמחות"],
            "אחוז התאמה": df_for_teacher["אחוז התאמה"].astype(int)
        }).sort_values("אחוז התאמה", ascending=False),
        use_container_width=True
    )
