# matcher_streamlit_beauty_rtl_v3.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

st.set_page_config(page_title="מערכת שיבוץ סטודנטים – התאמה חכמה", layout="wide")

# ====== עיצוב מודרני + RTL + הסתרת "Press Enter to apply" ======
st.markdown("""
<style>
@font-face {
  font-family:'David';
  src:url('https://example.com/David.ttf') format('truetype');
}
html, body, [class*="css"] {
  font-family:'David',sans-serif!important;
}

/* ====== עיצוב מודרני + RTL ====== */
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

/* כותרות */
h1,h2,h3,.stMarkdown h1,.stMarkdown h2{
  text-align:center;
  letter-spacing:.5px;
  text-shadow:0 1px 2px rgba(255,255,255,.7);
  font-weight:700;
  color:#222;
  margin-bottom:1rem;
}

/* כפתור */
.stButton > button{
  background:linear-gradient(135deg,var(--primary) 0%,var(--primary-700) 100%)!important;
  color:#fff!important;
  border:none!important;
  border-radius:18px!important;
  padding:1rem 2rem!important;
  font-size:1.1rem!important;
  font-weight:600!important;
  box-shadow:0 8px 18px var(--ring)!important;
  transition:all .15s ease!important;
}
.stButton > button:hover{ transform:translateY(-3px) scale(1.02); filter:brightness(1.08); }
.stButton > button:focus{ outline:none!important; box-shadow:0 0 0 4px var(--ring)!important; }

/* קלטים */
div.stSelectbox > div,
div.stMultiSelect > div,
.stTextInput > div > div > input{
  border-radius:14px!important;
  border:1px solid rgba(15,23,42,.12)!important;
  box-shadow:0 3px 10px rgba(15,23,42,.04)!important;
  padding:.6rem .8rem!important;
  color:var(--ink)!important;
  font-size:1rem!important;
}

/* טאבים – רוחב קטן יותר */
.stTabs [data-baseweb="tab"]{
  border-radius:14px!important;
  background:rgba(255,255,255,.65);
  margin-inline-start:.3rem;
  padding:.4rem .8rem;
  font-weight:600;
  min-width: 110px !important;
  text-align:center;
  font-size:0.9rem !important;
}
.stTabs [data-baseweb="tab"]:hover{ background:rgba(255,255,255,.9); }

/* RTL */
.stApp,.main,[data-testid="stSidebar"]{ direction:rtl; text-align:right; }
label,.stMarkdown,.stText,.stCaption{ text-align:right!important; }

/* הסתרת טיפ "Press Enter to apply" */
*[title="Press Enter to apply"]{ display:none !important; }

/* ====== כפתורי הורדה – סגנון "פיל" ====== */
div.stDownloadButton{ direction:rtl; text-align:right; }
div.stDownloadButton > button{
  border:1px solid rgba(15,23,42,.12)!important;
  border-radius:999px!important;
  padding:.85rem 1.2rem!important;
  font-size:1.05rem!important;
  font-weight:600!important;
  background:#fff!important;
  color:#111!important;
  box-shadow:0 8px 18px rgba(15,23,42,.06)!important;
  display:inline-flex!important;
  align-items:center!important;
  gap:.5rem!important;
}
div.stDownloadButton > button:hover{
  transform:translateY(-1px);
  box-shadow:0 10px 22px rgba(15,23,42,.08)!important;
}
</style>
""", unsafe_allow_html=True)

# ====== 0) כותרת (Hero) ======
st.markdown("<h1>מערכת שיבוץ סטודנטים – התאמה חכמה</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#475569;margin-top:-8px;'>כאן משבצים סטודנטים למקומות התמחות בקלות, בהתבסס על תחום, עיר ובקשות.</p>", unsafe_allow_html=True)

# ====== מודל ניקוד ======
@dataclass
class Weights:
    w_field: float = 0.70
    w_city: float = 0.20
    w_special: float = 0.10

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
SITE_COLS = {
    "name": ["מוסד / שירות הכשרה", "מוסד", "שם מוסד ההתמחות"],
    "field": ["תחום ההתמחות", "תחום התמחות"],
    "street": ["רחוב"],
    "city": ["עיר"],
    "capacity": ["מספר סטודנטים שניתן לקלוט השנה", "מספר סטודנטים שניתן לקלוט", "קיבולת"],
    "sup_first": ["שם פרטי"],
    "sup_last": ["שם משפחה"],
    "phone": ["טלפון"],
    "email": ["אימייל", "כתובת מייל", "דוא\"ל", "דוא״ל"]
}

def pick_col(df: pd.DataFrame, options: List[str]) -> Optional[str]:
    for opt in options:
        if opt in df.columns:
            return opt
    return None

def read_any(uploaded) -> Optional[pd.DataFrame]:
    try:
        name = uploaded.name.lower()
        if name.endswith(".csv"):
            return pd.read_csv(uploaded, encoding="utf-8-sig")
        if name.endswith(".xlsx") or name.endswith(".xls"):
            return pd.read_excel(uploaded)
        # ניסיון נוסף כ־Excel, אחרת CSV
        try:
            return pd.read_excel(uploaded)
        except Exception:
            return pd.read_csv(uploaded, encoding="utf-8-sig")
    except Exception:
        return None

def normalize_text(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()

# עוזרים בטוחים לעמודות חסרות
def series_or_default(df: pd.DataFrame, options: List[str], default: str = "") -> pd.Series:
    """
    מחזיר Series מתוך df אם נמצאה עמודה מתאימה; אחרת מחזיר Series של ברירת מחדל באורך df.
    לעולם לא זורק KeyError.
    """
    col = pick_col(df, options)
    if col is None:
        return pd.Series([default] * len(df), index=df.index)
    return df[col].fillna(default).astype(str)

def numeric_series_or_default(df: pd.DataFrame, options: List[str], default: int = 1) -> pd.Series:
    col = pick_col(df, options)
    if col is None:
        return pd.Series([default] * len(df), index=df.index, dtype=int)
    return pd.to_numeric(df[col], errors="coerce").fillna(default).astype(int)

def detect_site_type(name: str, field: str) -> str:
    text = f"{name or ''} {field or ''}".replace("־"," ").replace("-"," ").lower()
    pairs = [("כלא","כלא"),("בית סוהר","כלא"),
             ("בית חולים","בית חולים"),("מרכז רפואי","בית חולים"),
             ("מרפאה","בריאות"),
             ("בי\"ס","בית ספר"),("בית ספר","בית ספר"),("תיכון","בית ספר"),
             ("גן","גן ילדים"),
             ("מרכז קהילתי","קהילה"),("רווחה","רווחה"),
             ("חוסן","בריאות הנפש"),("בריאות הנפש","בריאות הנפש")]
    for k,v in pairs:
        if k in text:
            return v
    if "חינוך" in (field or ""):
        return "חינוך"
    return "אחר"

def resolve_students(df: pd.DataFrame) -> pd.DataFrame:
    """עמיד לעמודות חסרות; לא נופל על None/חוסר עמודה."""
    if df is None or not isinstance(df, pd.DataFrame):
        return pd.DataFrame(columns=[
            "stu_id","stu_first","stu_last","stu_phone","stu_email",
            "stu_city","stu_address","stu_pref","stu_req","stu_partner"
        ])
    out = df.copy()

    out["stu_id"]      = series_or_default(out, STU_COLS["id"])
    out["stu_first"]   = series_or_default(out, STU_COLS["first"])
    out["stu_last"]    = series_or_default(out, STU_COLS["last"])
    out["stu_phone"]   = series_or_default(out, STU_COLS["phone"])
    out["stu_email"]   = series_or_default(out, STU_COLS["email"])
    out["stu_city"]    = series_or_default(out, STU_COLS["city"])
    out["stu_address"] = series_or_default(out, STU_COLS["address"])
    out["stu_pref"]    = series_or_default(out, STU_COLS["preferred_field"])
    out["stu_req"]     = series_or_default(out, STU_COLS["special_req"])
    out["stu_partner"] = series_or_default(out, STU_COLS["partner"])

    for c in ["stu_id","stu_first","stu_last","stu_phone","stu_email","stu_city","stu_address","stu_pref","stu_req","stu_partner"]:
        out[c] = out[c].apply(normalize_text)
    return out

def resolve_sites(df: pd.DataFrame) -> pd.DataFrame:
    """עמיד לעמודות חסרות; קיבולת ברירת מחדל 1."""
    if df is None or not isinstance(df, pd.DataFrame):
        return pd.DataFrame(columns=[
            "site_name","site_field","site_street","site_city",
            "site_capacity","capacity_left","site_type","supervisor"
        ])
    out = df.copy()

    out["site_name"]    = series_or_default(out, SITE_COLS["name"])
    out["site_field"]   = series_or_default(out, SITE_COLS["field"])
    out["site_street"]  = series_or_default(out, SITE_COLS["street"])
    out["site_city"]    = series_or_default(out, SITE_COLS["city"])
    out["site_capacity"]= numeric_series_or_default(out, SITE_COLS["capacity"], default=1).clip(lower=0).astype(int)
    out["capacity_left"]= out["site_capacity"].astype(int)

    # טיפוס מקום
    out["site_type"] = (out["site_name"].astype(str) + " || " + out["site_field"].astype(str)).apply(
        lambda s: detect_site_type(*s.split(" || ", 1))
    )

    # שם מדריך
    sup_first = pick_col(out, SITE_COLS["sup_first"])
    sup_last  = pick_col(out, SITE_COLS["sup_last"])
    if sup_first or sup_last:
        ff = out[sup_first].astype(str) if sup_first else ""
        ll = out[sup_last].astype(str)  if sup_last  else ""
        out["supervisor"] = (ff + " " + ll).str.strip()
    else:
        out["supervisor"] = ""

    for c in ["site_name","site_field","site_street","site_city","site_type","supervisor"]:
        out[c] = out[c].apply(normalize_text)
    return out

def tokens(s: str) -> List[str]:
    return [t for t in str(s).replace(","," ").replace("/"," ").replace("-"," ").split() if t]

def field_match_score(stu_pref: str, site_field: str) -> float:
    if not stu_pref:
        return 50.0
    sp = stu_pref.strip()
    sf = site_field.strip() if site_field else ""
    if not sf:
        return 40.0
    if sp and sp in sf:
        return 90.0
    tp = set([w for w in tokens(sp) if len(w) > 1])
    tf = set([w for w in tokens(sf) if len(w) > 1])
    if tp.intersection(tf):
        return 75.0
    return 45.0

def special_req_score(req: str, site_type: str, same_city: bool) -> float:
    if not req:
        return 70.0
    if "לא בבית חולים" in req and site_type == "בית חולים":
        return 0.0
    if "קרוב" in req:
        return 90.0 if same_city else 55.0
    return 75.0

def compute_score(stu: pd.Series, site: pd.Series, W: Weights) -> float:
    same_city = bool(stu.get("stu_city")) and bool(site.get("site_city")) and (stu.get("stu_city") == site.get("site_city"))
    field_s   = field_match_score(stu.get("stu_pref",""), site.get("site_field",""))
    city_s    = 100.0 if same_city else 65.0
    special_s = special_req_score(stu.get("stu_req",""), site.get("site_type",""), same_city)
    score = W.w_field*field_s + W.w_city*city_s + W.w_special*special_s
    return float(np.clip(score, 0, 100))

def find_partner_map(students_df: pd.DataFrame) -> Dict[str,str]:
    if students_df.empty:
        return {}
    ids = set(students_df["stu_id"])
    m: Dict[str,str] = {}
    for _, r in students_df.iterrows():
        sid = r.get("stu_id","")
        pid = r.get("stu_partner","")
        if not sid or not pid:
            continue
        if pid in ids and pid != sid:
            m[sid] = pid
            continue
        for _, r2 in students_df.iterrows():
            full = f"{r2.get('stu_first','')} {r2.get('stu_last','')}".strip()
            if pid and full and pid in full and r2.get("stu_id","") != sid:
                m[sid] = r2.get("stu_id","")
                break
    return m

def candidate_table_for_student(stu: pd.Series, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    if sites_df.empty:
        return pd.DataFrame(columns=list(sites_df.columns) + ["score"])
    tmp = sites_df.copy()
    tmp["score"] = tmp.apply(lambda r: compute_score(stu, r, W), axis=1)
    return tmp.sort_values(["score"], ascending=[False])

def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    """
    מחזיר DataFrame של כל הסטודנטים. אם אין מקום/התאמה – הסטודנט יופיע כ'לא שובץ'.
    לא מוחק/מסנן שום רשומה מהקבצים המקוריים.
    """
    if students_df is None or sites_df is None or students_df.empty:
        return pd.DataFrame(columns=[
            "ת\"ז הסטודנט","שם פרטי","שם משפחה","כתובת","עיר",
            "מספר טלפון","אימייל","אחוז התאמה","שם מקום ההתמחות",
            "עיר המוסד","סוג מקום השיבוץ","תחום ההתמחות במוסד"
        ])

    # ודא שקיים capacity_left חוקי
    if "capacity_left" not in sites_df.columns:
        sites_df = sites_df.copy()
        if "site_capacity" in sites_df.columns:
            sites_df["capacity_left"] = sites_df["site_capacity"].astype(int)
        else:
            sites_df["capacity_left"] = 1

    separate_couples = True
    top_k = 10

    def dec_cap(idx: int):
        sites_df.at[idx, "capacity_left"] = max(0, int(sites_df.at[idx, "capacity_left"]) - 1)

    results: List[Tuple[pd.Series, Optional[pd.Series]]] = []
    processed = set()
    partner_map = find_partner_map(students_df)

    # בני/בנות זוג תחילה
    for _, s in students_df.iterrows():
        sid = s.get("stu_id","")
        if not sid or sid in processed:
            continue
        pid = partner_map.get(sid)
        if pid and partner_map.get(pid) == sid:
            partner_row = students_df[students_df["stu_id"] == pid]
            if partner_row.empty:
                continue
            s2 = partner_row.iloc[0]
            avail = sites_df[sites_df["capacity_left"] > 0]
            cand1 = candidate_table_for_student(s, avail, W).head(top_k)
            cand2 = candidate_table_for_student(s2, avail, W).head(top_k)
            best = (-1.0, None, None)
            for i1, r1 in cand1.iterrows():
                for i2, r2 in cand2.iterrows():
                    if i1 == i2:
                        continue
                    if separate_couples and r1.get("supervisor") and r1.get("supervisor") == r2.get("supervisor"):
                        continue
                    sc = float(r1["score"]) + float(r2["score"])
                    if sc > best[0]:
                        best = (sc, i1, i2)
            if best[1] is not None and best[2] is not None:
                rsite1 = sites_df.loc[best[1]]
                rsite2 = sites_df.loc[best[2]]
                dec_cap(best[1]); dec_cap(best[2])
                results.append((s, rsite1))
                results.append((s2, rsite2))
                processed.add(sid); processed.add(pid)

    # שיבוץ בודדים/מי שלא שובץ
    for _, s in students_df.iterrows():
        sid = s.get("stu_id","")
        if not sid or sid in processed:
            continue
        avail = sites_df[sites_df["capacity_left"] > 0]
        cand = candidate_table_for_student(s, avail, W).head(top_k)
        if not cand.empty:
            chosen_idx = cand.index[0]
            rsite = sites_df.loc[chosen_idx]
            dec_cap(chosen_idx)
            results.append((s, rsite))
            processed.add(sid)
        else:
            results.append((s, None))
            processed.add(sid)

    # פלט
    rows = []
    for s, r in results:
        if r is None:
            rows.append({
                "ת\"ז הסטודנט": s.get("stu_id",""),
                "שם פרטי": s.get("stu_first",""),
                "שם משפחה": s.get("stu_last",""),
                "כתובת": s.get("stu_address",""),
                "עיר": s.get("stu_city",""),
                "מספר טלפון": s.get("stu_phone",""),
                "אימייל": s.get("stu_email",""),
                "אחוז התאמה": 0.0,
                "שם מקום ההתמחות": "לא שובץ",
                "עיר המוסד": "",
                "סוג מקום השיבוץ": "",
                "תחום ההתמחות במוסד": "",
            })
        else:
            score = compute_score(s, r, W)
            rows.append({
                "ת\"ז הסטודנט": s.get("stu_id",""),
                "שם פרטי": s.get("stu_first",""),
                "שם משפחה": s.get("stu_last",""),
                "כתובת": s.get("stu_address",""),
                "עיר": s.get("stu_city",""),
                "מספר טלפון": s.get("stu_phone",""),
                "אימייל": s.get("stu_email",""),
                "אחוז התאמה": round(score, 1),
                "שם מקום ההתמחות": r.get("site_name",""),
                "עיר המוסד": r.get("site_city",""),
                "סוג מקום השיבוץ": r.get("site_type",""),
                "תחום ההתמחות במוסד": r.get("site_field",""),
            })
    out = pd.DataFrame(rows)
    desired = ["ת\"ז הסטודנט","שם פרטי","שם משפחה","כתובת","עיר","מספר טלפון","אימייל",
               "אחוז התאמה","שם מקום ההתמחות","עיר המוסד","סוג מקום השיבוץ","תחום ההתמחות במוסד"]
    remaining = [c for c in out.columns if c not in desired]
    return out[[c for c in desired if c in out.columns] + remaining]

W = Weights()

# ====== 1) הוראות שימוש ======
st.markdown("## 📘 הוראות שימוש")
st.markdown("""
1. **קובץ סטודנטים (CSV/XLSX):** שם פרטי, שם משפחה, תעודת זהות, כתובת/עיר, טלפון, אימייל.  
   אופציונלי: תחום מועדף, בקשה מיוחדת, בן/בת זוג להכשרה.
2. **קובץ אתרים/מדריכים (CSV/XLSX):** מוסד/שירות, תחום התמחות, רחוב, עיר, מספר סטודנטים שניתן לקלוט השנה.  
   אופציונלי: שם פרטי+שם משפחה של המדריך, טלפון, אימייל.
3. לחיצה על **בצע שיבוץ** תחשב *אחוז התאמה* לפי תחום (70%), עיר (20%), בקשות (10%), כולל הפרדת בני/בנות זוג ואכיפת קיבולת.
4. בסוף ניתן להוריד את קובץ התוצאות (CSV/XLSX).
""")

# ====== 2) דוגמה לשימוש ======
st.markdown("## 🧪 דוגמה לשימוש")
example_students = pd.DataFrame([
    {"שם פרטי":"רות", "שם משפחה":"כהן", "תעודת זהות":"123456789", "כתובת":"הרצל 12", "עיר מגורים":"תל אביב", "טלפון":"0501111111", "דוא\"ל":"ruth@example.com", "תחום מועדף":"בריאות הנפש"},
    {"שם פרטי":"יואב", "שם משפחה":"לוי", "תעודת זהות":"987654321", "כתובת":"דיזנגוף 80", "עיר מגורים":"תל אביב", "טלפון":"0502222222", "דוא\"ל":"yoav@example.com", "תחום מועדף":"רווחה"}
])
example_sites = pd.DataFrame([
    {"מוסד / שירות הכשרה":"מרכז חוסן תל אביב", "תחום ההתמחות":"בריאות הנפש", "רחוב":"אבן גבירול 1", "עיר":"תל אביב", "מספר סטודנטים שניתן לקלוט השנה":2},
    {"מוסד / שירות הכשרה":"מחלקת רווחה רמת גן", "תחום ההתמחות":"רווחה", "רחוב":"ביאליק 10", "עיר":"רמת גן", "מספר סטודנטים שניתן לקלוט השנה":1},
])
colX, colY = st.columns(2, gap="large")
with colX:
    st.write("**דוגמה – סטודנטים**")
    st.dataframe(example_students, use_container_width=True)
    st.download_button("⬇️ הורדת דוגמת סטודנטים (CSV)",
                       data=example_students.to_csv(index=False, encoding="utf-8-sig"),
                       file_name="students_example.csv", mime="text/csv")
with colY:
    st.write("**דוגמה – אתרי התמחות/מדריכים**")
    st.dataframe(example_sites, use_container_width=True)
    st.download_button("⬇️ הורדת דוגמת אתרים (CSV)",
                       data=example_sites.to_csv(index=False, encoding="utf-8-sig"),
                       file_name="sites_example.csv", mime="text/csv")

# ====== 3) העלאת קבצים ======
st.markdown("## 📤 העלאת קבצים")
colA, colB = st.columns(2, gap="large")
with colA:
    students_file = st.file_uploader("קובץ סטודנטים", type=["csv","xlsx","xls"], key="students_file")
    if students_file is not None:
        st.caption("הצצה ל-5 הרשומות הראשונות (לא מוחקים שום עמודה):")
        df_students_raw = read_any(students_file)
        if isinstance(df_students_raw, pd.DataFrame):
            st.dataframe(df_students_raw.head(5), use_container_width=True)
        else:
            st.error("לא ניתן לקרוא את קובץ הסטודנטים. ודא/י פורמט ונתונים תקינים.")
            df_students_raw = None
    else:
        df_students_raw = None

with colB:
    sites_file = st.file_uploader("קובץ אתרי התמחות/מדריכים", type=["csv","xlsx","xls"], key="sites_file")
    if sites_file is not None:
        st.caption("הצצה ל-5 הרשומות הראשונות (לא מוחקים שום עמודה):")
        df_sites_raw = read_any(sites_file)
        if isinstance(df_sites_raw, pd.DataFrame):
            st.dataframe(df_sites_raw.head(5), use_container_width=True)
        else:
            st.error("לא ניתן לקרוא את קובץ האתרים/מדריכים. ודא/י פורמט ונתונים תקינים.")
            df_sites_raw = None
    else:
        df_sites_raw = None

# ====== 4) שיבוץ ======
st.markdown("## ⚙️ ביצוע השיבוץ")
run_btn = st.button("🚀 בצע שיבוץ", use_container_width=True)

result_df = None
unmatched_students = None
unused_sites = None

if run_btn:
    # ולידציה חזקה: גם קבצים הועלו וגם נקראו בהצלחה
    if students_file is None or sites_file is None:
        st.error("נא להעלות את שני הקבצים לפני הפעלת השיבוץ.")
    elif df_students_raw is None or df_sites_raw is None:
        st.error("קריאת אחד הקבצים נכשלה. תקנ/י את הקובץ ונסו שוב.")
    else:
        try:
            students = resolve_students(df_students_raw)
            sites = resolve_sites(df_sites_raw)
            result_df = greedy_match(students, sites, W)

            # סטודנטים שלא שובצו
            unmatched_students = result_df[result_df["שם מקום ההתמחות"] == "לא שובץ"]

            # מוסדות שלא שובץ אליהם אף אחד
            used_sites = set(result_df["שם מקום ההתמחות"].unique())
            unused_sites = sites[~sites["site_name"].isin(used_sites)]

            st.success("השיבוץ הושלם ✓")
        except Exception as e:
            st.exception(e)

# ====== 5) תוצאות ======
st.markdown("## 📊 תוצאות השיבוץ")
if result_df is not None and not result_df.empty:
    st.dataframe(result_df, use_container_width=True)

    # כפתור Excel בלבד
    xlsx_io = BytesIO()
    with pd.ExcelWriter(xlsx_io, engine="xlsxwriter") as writer:
        result_df.to_excel(writer, index=False, sheet_name="שיבוץ")
    xlsx_io.seek(0)
    st.download_button(
        label="הורדת Excel (XLSX)",
        data=xlsx_io.getvalue(),
        file_name="student_site_matching.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_xlsx"
    )

    # טבלה: סטודנטים שלא שובצו
    if unmatched_students is not None and not unmatched_students.empty:
        st.markdown("### 👩‍🎓 סטודנטים שלא שובצו")
        st.dataframe(unmatched_students, use_container_width=True)

    # טבלה: מוסדות ללא סטודנטים
    if unused_sites is not None and not unused_sites.empty:
        st.markdown("### 🏫 מוסדות שלא שובץ אליהם אף סטודנט")
        st.dataframe(unused_sites[["site_name","site_city","site_field","site_capacity"]],
                     use_container_width=True)
else:
    st.caption("טרם הופעל שיבוץ או שאין תוצאות להצגה.")
