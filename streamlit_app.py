# matcher_streamlit_beauty_rtl_v7_fixed.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from dataclasses import dataclass
from typing import Optional, Any, List, Dict
import re

# =========================
# קונפיגורציה כללית
# =========================
# ====== קונפיגורציה כללית ======
st.set_page_config(page_title="מערכת שיבוץ סטודנטים – התאמה חכמה", layout="wide")

# ====== CSS – עיצוב + RTL + David ======
st.markdown("""
<style>
:root{
  --bg-1:#e0f7fa; --bg-2:#ede7f6; --bg-3:#fff3e0; --bg-4:#fce4ec; --bg-5:#e8f5e9;
  --ink:#0f172a; --primary:#9b5de5; --primary-700:#f15bb5; --ring:rgba(155,93,229,.35);
}

/* גופן David – גלובלי + כל רכיבי הטופס של Streamlit */
html, body, [class*="css"], .stApp, .main, [data-testid="stSidebar"],
.stMarkdown, .stText, .stCaption,
.stButton button,
.stTextInput input, .stNumberInput input,
.stTextArea textarea,
.stSelectbox [data-baseweb="select"] *, .stMultiSelect [data-baseweb="select"] *,
.stDateInput input, .stTimeInput input,
input, textarea, select {
  font-family: "David", "Noto Sans Hebrew", "Segoe UI", system-ui, sans-serif !important;
}

/* כיוון כתיבה ויישור לימין */
.stApp,.main,[data-testid="stSidebar"]{ direction:rtl; text-align:right; }
label,.stMarkdown,.stText,.stCaption{ text-align:right!important; }

/* placeholder בגופן David */
.stTextInput input::placeholder,
.stTextArea textarea::placeholder,
input::placeholder, textarea::placeholder {
  font-family: "David", "Noto Sans Hebrew", "Segoe UI", system-ui, sans-serif !important;
  opacity:.8;
}

/* רקע ו־Container */
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

/* כותרות */
h1,h2,h3,.stMarkdown h1,.stMarkdown h2{
  text-align:center; letter-spacing:.5px; text-shadow:0 1px 2px rgba(255,255,255,.7);
  font-weight:700; color:#222; margin-bottom:1rem;
}

/* כפתור ראשי */
.cta-wrap { max-width: 620px; margin: 0 auto; }
.cta-wrap > div > button{
  background:linear-gradient(90deg,var(--primary) 0%,var(--primary-700) 100%)!important;
  color:#fff!important; border:none!important; border-radius:24px!important;
  padding:1.4rem 2rem!important; font-size:1.25rem!important; font-weight:700!important;
  box-shadow:0 10px 22px var(--ring)!important; transition:all .15s ease!important; width:100%!important;
}
.cta-wrap > div > button:hover{ transform:translateY(-3px) scale(1.02); filter:brightness(1.07); }
.cta-wrap > div > button:focus{ outline:none!important; box-shadow:0 0 0 4px var(--ring)!important; }
</style>
""", unsafe_allow_html=True)

# ====== כותרת ======
st.markdown("<h1>מערכת שיבוץ סטודנטים – התאמה חכמה</h1>", unsafe_allow_html=True)

st.markdown("<p style='text-align:center;color:#475569;margin-top:-8px;'>כאן משבצים סטודנטים למקומות התמחות בקלות, בהתבסס על תחום, עיר ובקשות.</p>", unsafe_allow_html=True)

# ====== מודל ניקוד ======
@dataclass
class Weights:
    w_field: float   = 0.50   # תחום ההתמחות
    w_city: float    = 0.05   # אזור / עיר
    w_special: float = 0.45   # בקשות מיוחדות

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
    return (str(x or "")).strip()

# ----- סטודנטים -----
def resolve_students(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["stu_id"]    = out[pick_col(out, STU_COLS["id"])]
    out["stu_first"] = out[pick_col(out, STU_COLS["first"])]
    out["stu_last"]  = out[pick_col(out, STU_COLS["last"])]

    city_col = pick_col(out, STU_COLS["city"]) or pick_col(out, STU_COLS["address"])
    out["stu_city"]  = out[city_col] if city_col else ""

    pref_col = pick_col(out, ["תחומים מועדפים"]) or pick_col(out, STU_COLS["preferred_field"])
    out["stu_pref"] = out[pref_col] if pref_col else ""

    out["stu_req"]  = out[pick_col(out, STU_COLS["special_req"])] if pick_col(out, STU_COLS["special_req"]) else ""

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

# ====== עזר לניקוד ======

# מילון מילים נרדפות/נרמול מושגים (אפשר להרחיב בקלות)
SYNONYMS = {
    "בריאות הנפש": {"בריאות", "נפש", "פסיכיאטריה", "התמכרויות"},
    "חינוך מיוחד": {"חינוך", "מיוחד", "לקויות", "שילוב"},
    "רווחה": {"רווחה", "שירותי רווחה", "מחלקת רווחה"},
    "ילדים ונוער": {"ילדים", "נוער", "נוער בסיכון"},
    "בריאות": {"בריאות", "רפואה", "בית חולים", "קהילה רפואית"},
    "משפחה": {"משפחה", "הורות"},
    "נשים": {"נשים", "אלימות במשפחה"},
    "שיקום": {"שיקום", "שיקומי"},
    "קהילה": {"קהילה", "עיר", "מרכז קהילתי"},
}

def expand_with_synonyms(tokens: List[str]) -> List[str]:
    out = set(tokens)
    for canon, syns in SYNONYMS.items():
        if canon in tokens or any(s in tokens for s in syns):
            out.add(canon)
            out.update(syns)
    return list(out)

CITY_REGION: Dict[str, str] = {
    "תל אביב": "מרכז", "רמת גן": "מרכז", "גבעתיים": "מרכז",
    "פתח תקווה": "מרכז", "ראשון לציון": "מרכז", "נתניה": "שרון",
    "רעננה": "שרון", "כפר סבא": "שרון",
    "חיפה": "צפון", "קריות": "צפון", "נהריה": "צפון", "עכו": "צפון", "צפת": "צפון", "טבריה": "צפון",
    "אשדוד": "דרום", "אשקלון": "דרום", "באר שבע": "דרום",
    "רחובות": "שפלה"
}

NEIGHBOR = {
    "מרכז": {"שרון", "שפלה"},
    "שרון": {"מרכז", "צפון"},
    "צפון": {"שרון"},
    "שפלה": {"מרכז", "דרום"},
    "דרום": {"שפלה"},
}

SPLIT_RE = re.compile(r"[;,/|+]+|\s{2,}")

def _norm(s: Any) -> str:
    return (str(s or "")).strip().lower()

def _tokenize_field(s: str) -> List[str]:
    s = _norm(s)
    s = re.sub(r"[^א-תa-z0-9\s/,+-]", " ", s)
    parts = [p for p in SPLIT_RE.split(s) if p]
    parts = expand_with_synonyms(parts)
    return parts

def jaccard(a: List[str], b: List[str]) -> float:
    A, B = set(a), set(b)
    if not A or not B: return 0.0
    inter = len(A & B)
    union = len(A | B)
    return inter/union if union else 0.0

def best_pref_similarity(stu_pref_text: str, site_field_text: str) -> float:
    """
    תומך במספר תחומים מועדפים לסטודנט (מופרדים בפסיקים/נקודה פסיק/קו נטוי/רווחים מרובים).
    מחזיר את הדמיון המקסימלי לאתר.
    """
    if not stu_pref_text or not site_field_text:
        return 0.0
    # פיצול תחומי סטודנט
    raw = [x for x in re.split(r"[;,/|]+", stu_pref_text) if x.strip()]
    site_tokens = _tokenize_field(site_field_text)
    best = 0.0
    for pref in raw if raw else [stu_pref_text]:
        pref_tokens = _tokenize_field(pref)
        sim = jaccard(pref_tokens, site_tokens)
        if sim > best:
            best = sim
    return best

def domain_score(stu_pref_text: str, site_field_text: str) -> float:
    sim = best_pref_similarity(stu_pref_text, site_field_text)  # 0..1
    return 100.0 * sim

def city_score(stu_city: str, site_city: str) -> float:
    s_c = normalize_text(stu_city)
    t_c = normalize_text(site_city)
    if not s_c or not t_c: return 50.0  # ברירת מחדל לא ידוע
    if s_c == t_c: return 100.0
    s_r = CITY_REGION.get(s_c, "")
    t_r = CITY_REGION.get(t_c, "")
    if s_r and t_r:
        if s_r == t_r: return 75.0
        if t_r in NEIGHBOR.get(s_r, set()): return 55.0
        return 35.0
    return 45.0

def special_score(stu_req: str, same_city: bool) -> float:
    """
    בונוס נקודתי: 'קרוב', 'קרבה', 'בית' -> משקל גבוה יותר.
    ניתן להרחיב עם מילות מפתח נוספות.
    """
    txt = _norm(stu_req)
    if not txt: return 50.0  # נייטרלי
    if "קרוב" in txt or "קרבה" in txt or "בית" in txt:
        return 100.0 if same_city else 65.0
    return 60.0

# ====== חישוב ציון גולמי ======
def raw_score(stu: pd.Series, site: pd.Series, W: Weights) -> float:
    same_city = (_norm(stu.get("stu_city")) and _norm(site.get("site_city")) and
                 _norm(stu.get("stu_city")) == _norm(site.get("site_city")))
    f = domain_score(stu.get("stu_pref",""), site.get("site_field",""))   # 0..100 רציף
    c = city_score(stu.get("stu_city",""), site.get("site_city",""))      # 0..100
    s = special_score(stu.get("stu_req",""), same_city)                    # 0..100
    score = W.w_field*f + W.w_city*c + W.w_special*s                       # 0..100
    return float(np.clip(score, 0, 100))

# ====== שיבוץ עם נורמליזציה יחסית לכל סטודנט ======
def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    results = []
    supervisor_count = {}  # דוגמה להגבלה פר-מדריך: עד 2 סטודנטים (ניתן לשנות/לבטל)

    for _, s in students_df.iterrows():
        # כל המועמדים הפנויים
        cand = sites_df[sites_df["capacity_left"] > 0].copy()

        if cand.empty:
            results.append({
                "ת\"ז הסטודנט": s.get("stu_id",""),
                "שם פרטי": s.get("stu_first",""),
                "שם משפחה": s.get("stu_last",""),
                "שם מקום ההתמחות": "לא שובץ",
                "עיר המוסד": "",
                "תחום ההתמחות במוסד": "",
                "שם המדריך": "",
                "אחוז התאמה": 0,
                "_expl": {"התאמת תחום":0,"מרחק/גיאוגרפיה":0,"בקשות מיוחדות":0,"עדיפויות הסטודנט/ית":0}
            })
            continue

        # ניקוד גולמי לכל אתר
        cand["raw"] = cand.apply(lambda r: raw_score(s, r, W), axis=1)

        # סינון פר-מדריך (אם רוצים)
        def allowed_supervisor(r):
            sup = r.get("שם המדריך", "")
            return supervisor_count.get(sup, 0) < 2 if sup else True
        cand = cand[cand.apply(allowed_supervisor, axis=1)]

        if cand.empty:
            # אם נפלנו בגלל מגבלת מדריך – נחזור לכל הפנויים (עדיף לשבץ מאשר לא)
            cand = sites_df[sites_df["capacity_left"] > 0].copy()
            cand["raw"] = cand.apply(lambda r: raw_score(s, r, W), axis=1)
            if cand.empty:
                results.append({
                    "ת\"ז הסטודנט": s.get("stu_id",""),
                    "שם פרטי": s.get("stu_first",""),
                    "שם משפחה": s.get("stu_last",""),
                    "שם מקום ההתמחות": "לא שובץ",
                    "עיר המוסד": "",
                    "תחום ההתמחות במוסד": "",
                    "שם המדריך": "",
                    "אחוז התאמה": 0,
                    "_expl": {"התאמת תחום":0,"מרחק/גיאוגרפיה":0,"בקשות מיוחדות":0,"עדיפויות הסטודנט/ית":0}
                })
                continue

        # --- נורמליזציה יחסית לסטודנט: מבטיחה פיזור 0..100 בין האתרים של אותו סטודנט ---
        rmin, rmax = float(cand["raw"].min()), float(cand["raw"].max())
        if rmax > rmin:
            cand["score"] = (cand["raw"] - rmin) / (rmax - rmin) * 100.0
        else:
            cand["score"] = 50.0  # אין שונות – מצביע שאין הבדל בין האתרים עבור הסטודנט

        # גם נשמור פירוט מרכיבים לפי הניקוד הגולמי שנבחר
        def parts_for(r):
            # פירוק לפי raw שנבנה מ־f,c,s
            same_city = (_norm(s.get("stu_city")) and _norm(r.get("site_city")) and
                         _norm(s.get("stu_city")) == _norm(r.get("site_city")))
            f = domain_score(s.get("stu_pref",""), r.get("site_field",""))
            c = city_score(s.get("stu_city",""), r.get("site_city",""))
            sp = special_score(s.get("stu_req",""), same_city)
            return {
                "התאמת תחום": int(round(W.w_field * f)),
                "מרחק/גיאוגרפיה": int(round(W.w_city * c)),
                "בקשות מיוחדות": int(round(W.w_special * sp)),
                "עדיפויות הסטודנט/ית": 0
            }

        cand = cand.sort_values("score", ascending=False)
        chosen = cand.iloc[0]
        idx = chosen.name
        sites_df.at[idx, "capacity_left"] -= 1

        sup_name = chosen.get("שם המדריך", "")
        if sup_name:
            supervisor_count[sup_name] = supervisor_count.get(sup_name, 0) + 1

        results.append({
            "ת\"ז הסטודנט": s.get("stu_id",""),
            "שם פרטי": s.get("stu_first",""),
            "שם משפחה": s.get("stu_last",""),
            "שם מקום ההתמחות": chosen.get("site_name",""),
            "עיר המוסד": chosen.get("site_city",""),
            "תחום ההתמחות במוסד": chosen.get("site_field",""),
            "שם המדריך": sup_name,
            "אחוז התאמה": int(round(float(chosen["score"]))),   # יחסי, 0..100
            "_expl": parts_for(chosen)
        })

    return pd.DataFrame(results)

# ---- יצירת XLSX ----
def df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "שיבוץ") -> bytes:
    xlsx_io = BytesIO()
    import xlsxwriter
    with pd.ExcelWriter(xlsx_io, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    xlsx_io.seek(0)
    return xlsx_io.getvalue()

# =========================
# 1) הוראות שימוש
# =========================
st.markdown("## 📘 הוראות שימוש")
st.markdown("""
1. **קובץ סטודנטים (CSV/XLSX):** שם פרטי, שם משפחה, תעודת זהות, עיר/כתובת, טלפון, אימייל.  
   אופציונלי: תחום מועדף/ים (אפשר כמה, מופרדים בפסיק/; / /), בקשה מיוחדת.  
2. **קובץ אתרים/מדריכים (CSV/XLSX):** מוסד/שירות, תחום התמחות, עיר, קיבולת, מדריך, חוות דעת.  
3. כפתור **בצע שיבוץ** מחשב ניקוד ***יחסי לכל סטודנט*** ומדגים פיזור אמיתי של אחוזי התאמה.
""")

# =========================
# 2) דוגמה לשימוש
# =========================
st.markdown("## 🧪 דוגמה לשימוש")
example_students = pd.DataFrame([
    {"שם פרטי":"רות", "שם משפחה":"כהן", "תעודת זהות":"123456789", "עיר מגורים":"תל אביב", "טלפון":"0501111111", "דוא\"ל":"ruth@example.com", "תחומים מועדפים":"בריאות הנפש; חינוך מיוחד", "בקשה מיוחדת":"קרוב לבית"},
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

for k in ["df_students_raw","df_sites_raw","result_df","sites_after"]:
    st.session_state.setdefault(k, None)

# =========================
# שיבוץ והצגת תוצאות
# =========================
st.markdown("## ⚙️ ביצוע השיבוץ")
st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)
run_match = st.button("בצע שיבוץ 🚀", use_container_width=True, key="run_match")
st.markdown('</div>', unsafe_allow_html=True)

if run_match:
    try:
        students = resolve_students(st.session_state["df_students_raw"])
        sites    = resolve_sites(st.session_state["df_sites_raw"])
        result_df = greedy_match(students, sites, Weights())
        st.session_state["result_df"] = result_df
        st.session_state["sites_after"] = sites
        st.success("השיבוץ הושלם ✓")
    except Exception as e:
        st.exception(e)

if isinstance(st.session_state["result_df"], pd.DataFrame) and not st.session_state["result_df"].empty:
    st.markdown("## 📊 תוצאות השיבוץ")
    base_df = st.session_state["result_df"].copy()

    df_show = pd.DataFrame({
        "אחוז התאמה": base_df["אחוז התאמה"].astype(int),
        "שם הסטודנט/ית": (base_df["שם פרטי"].astype(str) + " " + base_df["שם משפחה"].astype(str)).str.strip(),
        "תעודת זהות": base_df["ת\"ז הסטודנט"],
        "תחום התמחות": base_df["תחום ההתמחות במוסד"],
        "עיר המוסד": base_df["עיר המוסד"],
        "שם מקום ההתמחות": base_df["שם מקום ההתמחות"],
        "שם המדריך/ה": base_df["שם המדריך"],
    }).sort_values("אחוז התאמה", ascending=False)

    st.markdown("### טבלת תוצאות מרכזית")
    st.dataframe(df_show, use_container_width=True)

    # הורדה
    def df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "תוצאות") -> bytes:
        xlsx_io = BytesIO()
        import xlsxwriter
        with pd.ExcelWriter(xlsx_io, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name)
        xlsx_io.seek(0)
        return xlsx_io.getvalue()

    xlsx_results = df_to_xlsx_bytes(df_show, sheet_name="תוצאות")
    st.download_button(
        "⬇️ הורדת XLSX – תוצאות השיבוץ",
        data=xlsx_results,
        file_name="student_site_matching.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # הסבר ציון (שבירת התאמה)
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

    # דוח סיכום לפי מקום הכשרה
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
        "שם מקום ההתמחות","תחום ההתמחות במוסד","שם המדריך","כמה סטודנטים","המלצת שיבוץ"
    ]]
    st.dataframe(summary_df, use_container_width=True)

    xlsx_summary = df_to_xlsx_bytes(summary_df, sheet_name="סיכום")
    st.download_button(
        "⬇️ הורדת XLSX – טבלת סיכום",
        data=xlsx_summary,
        file_name="student_site_summary.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # דוח קיבולות
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

        under = cap_df[cap_df["יתרה/חוסר"] > 0]
        over  = cap_df[cap_df["יתרה/חוסר"] < 0]
        if not under.empty:
            st.info("מוסדות עם מקומות פנויים:\n- " + "\n- ".join(under["שם מקום ההתמחות"].tolist()))
        if not over.empty:
            st.error("מוסדות עם חריגה (עודף שיבוץ):\n- " + "\n- ".join(over["שם מקום ההתמחות"].tolist()))
    else:
        st.info("לא נמצאו נתוני קיבולת לשיבוץ זה.")
