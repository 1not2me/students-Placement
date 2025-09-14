# matcher_streamlit_beauty_rtl_v5.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import csv
from io import BytesIO
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

# =========================
# קונפיגורציה כללית
# =========================
st.set_page_config(page_title="מערכת שיבוץ סטודנטים – התאמה חכמה", layout="wide")

# ====== CSS – עיצוב מודרני + RTL + כפתורי הורדה רחבים ======
st.markdown("""
<style>
@font-face {
  font-family:'David';
  src:url('https://example.com/David.ttf') format('truetype');
}
html, body, [class*="css"] { font-family:'David',sans-serif!important; }

/* ====== צבעים ====== */
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

/* רקע */
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

/* כפתור רגיל */
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
  width:100%;
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

/* טאבים */
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

/* ====== כפתורי הורדה – רחבים + גרדיאנט כמו כפתור השיבוץ ====== */
div[data-testid="stDownloadButton"] > button,
div.stDownloadButton > button{
  width:100% !important;
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
div[data-testid="stDownloadButton"] > button:hover,
div.stDownloadButton > button:hover{
  transform:translateY(-3px) scale(1.02);
  filter:brightness(1.08);
}
div[data-testid="stDownloadButton"] > button:focus,
div.stDownloadButton > button:focus{
  outline:none!important;
  box-shadow:0 0 0 4px var(--ring)!important;
}
</style>
""", unsafe_allow_html=True)

# ====== כותרת ======
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
        if opt in df.columns: return opt
    return None

# ----- קריאת קבצים עם הודעת שגיאה מועילה -----
def read_any(uploaded) -> pd.DataFrame:
    name = (uploaded.name or "").lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(uploaded, encoding="utf-8-sig")
        if name.endswith(".xlsx") or name.endswith(".xls"):
            return pd.read_excel(uploaded)
        try:
            return pd.read_excel(uploaded)
        except Exception:
            return pd.read_csv(uploaded, encoding="utf-8-sig")
    except Exception as e:
        raise ValueError(f"שגיאה בקריאת הקובץ '{uploaded.name}': {e}")

def normalize_text(x: Any) -> str:
    if x is None: return ""
    return str(x).strip()

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
        if k in text: return v
    if "חינוך" in (field or ""): return "חינוך"
    return "אחר"

def ensure_df(df: pd.DataFrame, kind: str):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError(f"קובץ ה{kind} ריק או לא נטען כראוי. אמת/י פורמט ושמות עמודות.")

def resolve_students(df: pd.DataFrame) -> pd.DataFrame:
    ensure_df(df, "סטודנטים")
    out = df.copy()
    id_col    = pick_col(out, STU_COLS["id"])
    first_col = pick_col(out, STU_COLS["first"])
    last_col  = pick_col(out, STU_COLS["last"])
    if not id_col or not first_col or not last_col:
        raise ValueError("בקובץ הסטודנטים חסרות עמודות חובה: ת\"ז / שם פרטי / שם משפחה.")
    out["stu_id"]      = out[id_col]
    out["stu_first"]   = out[first_col]
    out["stu_last"]    = out[last_col]
    out["stu_phone"]   = out[pick_col(out, STU_COLS["phone"])] if pick_col(out, STU_COLS["phone"]) else ""
    out["stu_email"]   = out[pick_col(out, STU_COLS["email"])] if pick_col(out, STU_COLS["email"]) else ""
    out["stu_city"]    = out[pick_col(out, STU_COLS["city"])] if pick_col(out, STU_COLS["city"]) else ""
    out["stu_address"] = out[pick_col(out, STU_COLS["address"])] if pick_col(out, STU_COLS["address"]) else ""
    pref_col           = pick_col(out, STU_COLS["preferred_field"])
    out["stu_pref"]    = out[pref_col] if pref_col else ""
    out["stu_req"]     = out[pick_col(out, STU_COLS["special_req"])] if pick_col(out, STU_COLS["special_req"]) else ""
    out["stu_partner"] = out[pick_col(out, STU_COLS["partner"])] if pick_col(out, STU_COLS["partner"]) else ""
    for c in ["stu_id","stu_first","stu_last","stu_phone","stu_email","stu_city","stu_address","stu_pref","stu_req","stu_partner"]:
        out[c] = out[c].apply(normalize_text)
    return out

def resolve_sites(df: pd.DataFrame) -> pd.DataFrame:
    ensure_df(df, "אתרים/מדריכים")
    out = df.copy()
    name_col  = pick_col(out, SITE_COLS["name"])
    field_col = pick_col(out, SITE_COLS["field"])
    if not name_col or not field_col:
        raise ValueError("בקובץ האתרים חסרות עמודות חובה: שם מוסד / תחום ההתמחות.")
    out["site_name"]   = out[name_col]
    out["site_field"]  = out[field_col]
    out["site_street"] = out[pick_col(out, SITE_COLS["street"])] if pick_col(out, SITE_COLS["street"]) else ""
    out["site_city"]   = out[pick_col(out, SITE_COLS["city"])] if pick_col(out, SITE_COLS["city"]) else ""
    cap_col = pick_col(out, SITE_COLS["capacity"])
    out["site_capacity"] = pd.to_numeric(out[cap_col], errors="coerce").fillna(1).astype(int) if cap_col else 1
    out["capacity_left"] = out["site_capacity"].astype(int)
    out["site_type"] = out.apply(lambda r: detect_site_type(r.get("site_name"), r.get("site_field")), axis=1)
    sup_first = pick_col(out, SITE_COLS["sup_first"])
    sup_last  = pick_col(out, SITE_COLS["sup_last"])
    out["supervisor"] = ""
    if sup_first or sup_last:
        ff = out[sup_first] if sup_first else ""
        ll = out[sup_last]  if sup_last  else ""
        out["supervisor"] = (ff.astype(str) + " " + ll.astype(str)).str.strip()
    for c in ["site_name","site_field","site_street","site_city","site_type","supervisor"]:
        out[c] = out[c].apply(normalize_text)
    return out

def tokens(s: str) -> List[str]:
    return [t for t in str(s).replace(","," ").replace("/"," ").replace("-"," ").split() if t]

def field_match_score(stu_pref: str, site_field: str) -> float:
    if not stu_pref: return 50.0
    sp = stu_pref.strip(); sf = (site_field or "").strip()
    if not sf: return 40.0
    if sp and sp in sf: return 90.0
    tp = set([w for w in tokens(sp) if len(w) > 1])
    tf = set([w for w in tokens(sf) if len(w) > 1])
    if tp.intersection(tf): return 75.0
    return 45.0

def special_req_score(req: str, site_type: str, same_city: bool) -> float:
    if not req: return 70.0
    if "לא בבית חולים" in req and site_type == "בית חולים": return 0.0
    if "קרוב" in req: return 90.0 if same_city else 55.0
    return 75.0

def compute_score(stu: pd.Series, site: pd.Series, W: Weights) -> float:
    same_city = (stu.get("stu_city") and site.get("site_city") and stu.get("stu_city") == site.get("site_city"))
    field_s   = field_match_score(stu.get("stu_pref",""), site.get("site_field",""))
    city_s    = 100.0 if same_city else 65.0
    special_s = special_req_score(stu.get("stu_req",""), site.get("site_type",""), same_city)
    score = W.w_field*field_s + W.w_city*city_s + W.w_special*special_s
    return float(np.clip(score, 0, 100))

def find_partner_map(students_df: pd.DataFrame) -> Dict[str,str]:
    ids = set(students_df["stu_id"]); m: Dict[str,str] = {}
    for _, r in students_df.iterrows():
        sid = r["stu_id"]; pid = r.get("stu_partner","")
        if not pid: continue
        if pid in ids and pid != sid:
            m[sid] = pid; continue
        for _, r2 in students_df.iterrows():
            full = f"{r2.get('stu_first','')} {r2.get('stu_last','')}".strip()
            if pid and full and pid in full and r2["stu_id"] != sid:
                m[sid] = r2["stu_id"]; break
    return m

def candidate_table_for_student(stu: pd.Series, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    tmp = sites_df.copy()
    tmp["score"] = tmp.apply(lambda r: compute_score(stu, r, W), axis=1)
    return tmp.sort_values(["score"], ascending=[False])

def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    separate_couples = True
    top_k = 10
    def dec_cap(idx: int):
        sites_df.at[idx, "capacity_left"] = int(sites_df.at[idx, "capacity_left"]) - 1
    results: List[Tuple[pd.Series, Optional[pd.Series]]] = []
    processed = set()
    partner_map = find_partner_map(students_df)

    # זוגות
    for _, s in students_df.iterrows():
        sid = s["stu_id"]
        if sid in processed: continue
        pid = partner_map.get(sid)
        if pid and partner_map.get(pid) == sid:
            partner_row = students_df[students_df["stu_id"] == pid]
            if partner_row.empty: continue
            s2 = partner_row.iloc[0]
            cand1 = candidate_table_for_student(s,  sites_df[sites_df["capacity_left"]>0], W).head(top_k)
            cand2 = candidate_table_for_student(s2, sites_df[sites_df["capacity_left"]>0], W).head(top_k)
            best = (-1.0, None, None)
            for i1, r1 in cand1.iterrows():
                for i2, r2 in cand2.iterrows():
                    if i1 == i2: continue
                    if separate_couples and r1.get("supervisor") and r1.get("supervisor") == r2.get("supervisor"):
                        continue
                    sc = float(r1["score"]) + float(r2["score"])
                    if sc > best[0]: best = (sc, i1, i2)
            if best[1] is not None and best[2] is not None:
                rsite1 = sites_df.loc[best[1]]; rsite2 = sites_df.loc[best[2]]
                dec_cap(best[1]); dec_cap(best[2])
                results.append((s, rsite1)); results.append((s2, rsite2))
                processed.add(sid); processed.add(pid)

    # בודדים
    for _, s in students_df.iterrows():
        sid = s["stu_id"]
        if sid in processed: continue
        cand = candidate_table_for_student(s, sites_df[sites_df["capacity_left"]>0], W).head(top_k)
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
                "ת\"ז הסטודנט": s.get("stu_id"),
                "שם פרטי": s.get("stu_first"),
                "שם משפחה": s.get("stu_last"),
                "כתובת": s.get("stu_address"),
                "עיר": s.get("stu_city"),
                "מספר טלפון": s.get("stu_phone"),
                "אימייל": s.get("stu_email"),
                "אחוז התאמה": 0.0,
                "שם מקום ההתמחות": "לא שובץ",
                "עיר המוסד": "",
                "סוג מקום השיבוץ": "",
                "תחום ההתמחות במוסד": "",
            })
        else:
            score = compute_score(s, r, W)
            rows.append({
                "ת\"ז הסטודנט": s.get("stu_id"),
                "שם פרטי": s.get("stu_first"),
                "שם משפחה": s.get("stu_last"),
                "כתובת": s.get("stu_address"),
                "עיר": s.get("stu_city"),
                "מספר טלפון": s.get("stu_phone"),
                "אימייל": s.get("stu_email"),
                "אחוז התאמה": round(score, 1),
                "שם מקום ההתמחות": r.get("site_name"),
                "עיר המוסד": r.get("site_city"),
                "סוג מקום השיבוץ": r.get("site_type"),
                "תחום ההתמחות במוסד": r.get("site_field"),
            })
    out = pd.DataFrame(rows)
    desired = ["ת\"ז הסטודנט","שם פרטי","שם משפחה","כתובת","עיר","מספר טלפון","אימייל",
               "אחוז התאמה","שם מקום ההתמחות","עיר המוסד","סוג מקום השיבוץ","תחום ההתמחות במוסד"]
    remaining = [c for c in out.columns if c not in desired]
    return out[[c for c in desired if c in out.columns] + remaining]

# ---- יצירת XLSX (fallback: xlsxwriter → openpyxl) ----
def df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "שיבוץ") -> bytes:
    xlsx_io = BytesIO()
    try:
        import xlsxwriter  # noqa: F401
        engine = "xlsxwriter"
    except Exception:
        engine = "openpyxl"
    with pd.ExcelWriter(xlsx_io, engine=engine) as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    xlsx_io.seek(0)
    return xlsx_io.getvalue()

# ---- CSV ידידותי לאקסל (IL): ; + UTF-8-SIG + ציטוט מלא + שימור אפסים מובילים ----
TEXT_COLS = ["ת\"ז הסטודנט", "מספר טלפון", "אימייל"]
def df_to_excel_friendly_csv_bytes(df: pd.DataFrame) -> bytes:
    df2 = df.copy()
    for c in TEXT_COLS:
        if c in df2.columns:
            df2[c] = df2[c].astype(str).apply(lambda s: "'" + s if not s.startswith("'") else s)
    return df2.to_csv(index=False, sep=";", encoding="utf-8-sig", quoting=csv.QUOTE_ALL).encode("utf-8-sig")

# =========================
# 1) הוראות שימוש
# =========================
st.markdown("## 📘 הוראות שימוש")
st.markdown("""
1. **קובץ סטודנטים (CSV/XLSX):** שם פרטי, שם משפחה, תעודת זהות, כתובת/עיר, טלפון, אימייל.  
   אופציונלי: תחום מועדף, בקשה מיוחדת, בן/בת זוג להכשרה.  
2. **קובץ אתרים/מדריכים (CSV/XLSX):** מוסד/שירות, תחום התמחות, רחוב, עיר, מספר סטודנטים שניתן לקלוט השנה.  
3. **בצע שיבוץ** מחשב *אחוז התאמה* לפי תחום (70%), עיר (20%), בקשות (10%), כולל בני/בנות זוג וקיבולת.  
4. בסוף אפשר להוריד **XLSX** או **CSV**. הכפתורים נשארים זמינים לאחר השיבוץ.
""")

# =========================
# 2) דוגמאות (אופציונלי)
# =========================
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
        st.caption("הצצה ל-5 הרשומות הראשונות (לא מוחקים שום עמודה):")
        try:
            st.session_state["df_students_raw"] = read_any(students_file)
            st.dataframe(st.session_state["df_students_raw"].head(5), use_container_width=True)
        except Exception as e:
            st.error(f"לא ניתן לקרוא את קובץ הסטודנטים: {e}")

with colB:
    sites_file = st.file_uploader("קובץ אתרי התמחות/מדריכים", type=["csv","xlsx","xls"], key="sites_file")
    if sites_file is not None:
        st.caption("הצצה ל-5 הרשומות הראשונות (לא מוחקים שום עמודה):")
        try:
            st.session_state["df_sites_raw"] = read_any(sites_file)
            st.dataframe(st.session_state["df_sites_raw"].head(5), use_container_width=True)
        except Exception as e:
            st.error(f"לא ניתן לקרוא את קובץ האתרים/מדריכים: {e}")

# אתחול session_state למפתחות חשובים
for k in ["df_students_raw","df_sites_raw","result_df","unmatched_students","unused_sites"]:
    st.session_state.setdefault(k, None)

# =========================
# 4) שיבוץ
# =========================
st.markdown("## ⚙️ ביצוע השיבוץ")
run_btn = st.button("🚀 בצע שיבוץ", use_container_width=True)

if run_btn:
    try:
        ensure_df(st.session_state["df_students_raw"], "סטודנטים")
        ensure_df(st.session_state["df_sites_raw"], "אתרים/מדריכים")
        students = resolve_students(st.session_state["df_students_raw"])
        sites    = resolve_sites(st.session_state["df_sites_raw"])
        result_df = greedy_match(students, sites, Weights())
        st.session_state["result_df"] = result_df
        st.session_state["unmatched_students"] = result_df[result_df["שם מקום ההתמחות"] == "לא שובץ"]
        used_sites = set(result_df["שם מקום ההתמחות"].unique())
        st.session_state["unused_sites"] = sites[~sites["site_name"].isin(used_sites)]
        st.success("השיבוץ הושלם ✓")
    except Exception as e:
        st.exception(e)

# =========================
# 5) תוצאות והורדות
# =========================
st.markdown("## 📊 תוצאות השיבוץ")

st.markdown("## 📊 תוצאות השיבוץ")

if isinstance(st.session_state["result_df"], pd.DataFrame) and not st.session_state["result_df"].empty:
    st.dataframe(st.session_state["result_df"], use_container_width=True)

    # --- כפתור הורדת XLSX בלבד (רחב) ---
    try:
        xlsx_bytes = df_to_xlsx_bytes(st.session_state["result_df"])
        st.download_button(
            label="⬇️ הורדת XLSX / CSV",
            data=xlsx_bytes,
            file_name="student_site_matching.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_xlsx_btn",
            help="קובץ Excel בעברית"
        )
    except Exception as e:
        st.error(f"שגיאה ביצירת Excel: {e}.")

    # --- טבלאות נוספות ---
    if isinstance(st.session_state["unmatched_students"], pd.DataFrame) and not st.session_state["unmatched_students"].empty:
        st.markdown("### 👩‍🎓 סטודנטים שלא שובצו")
        st.dataframe(st.session_state["unmatched_students"], use_container_width=True)

    if isinstance(st.session_state["unused_sites"], pd.DataFrame) and not st.session_state["unused_sites"].empty:
        st.markdown("### 🏫 מוסדות שלא שובץ אליהם אף סטודנט")
        st.dataframe(
            st.session_state["unused_sites"][["site_name","site_city","site_field","site_capacity"]],
            use_container_width=True
        )



    # --- טבלאות נוספות ---
    if isinstance(st.session_state["unmatched_students"], pd.DataFrame) and not st.session_state["unmatched_students"].empty:
        st.markdown("### 👩‍🎓 סטודנטים שלא שובצו")
        st.dataframe(st.session_state["unmatched_students"], use_container_width=True)

    if isinstance(st.session_state["unused_sites"], pd.DataFrame) and not st.session_state["unused_sites"].empty:
        st.markdown("### 🏫 מוסדות שלא שובץ אליהם אף סטודנט")
        st.dataframe(st.session_state["unused_sites"][["site_name","site_city","site_field","site_capacity"]], use_container_width=True)
else:
    st.caption("טרם הופעל שיבוץ או שאין תוצאות להצגה.")
