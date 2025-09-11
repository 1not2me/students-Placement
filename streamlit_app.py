
# matcher_streamlit_beauty_rtl_v5.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

st.set_page_config(page_title="מערכת שיבוץ סטודנטים – התאמה חכמה", layout="wide")

# ====== עיצוב מודרני + RTL (עם הסתרת "Press Enter to apply") ======
st.markdown("""
<style>
@font-face { font-family:'David'; src:url('https://example.com/David.ttf') format('truetype'); }
html, body, [class*="css"] { font-family:'David',sans-serif!important; }
:root{ --bg-1:#e0f7fa; --bg-2:#ede7f6; --bg-3:#fff3e0; --bg-4:#fce4ec; --bg-5:#e8f5e9; --ink:#0f172a; --primary:#9b5de5; --primary-700:#f15bb5; --ring:rgba(155,93,229,.35); }
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
  border-radius:24px; padding:2.5rem; margin-top:1rem;
}
h1,h2,h3,.stMarkdown h1,.stMarkdown h2{
  text-align:center; letter-spacing:.5px; text-shadow:0 1px 2px rgba(255,255,255,.7);
  font-weight:700; color:#222; margin-bottom:1rem;
}
.stButton > button{
  background:linear-gradient(135deg,var(--primary) 0%,var(--primary-700) 100%)!important;
  color:#fff!important; border:none!important; border-radius:18px!important;
  padding:1rem 2rem!important; font-size:1.1rem!important; font-weight:600!important;
  box-shadow:0 8px 18px var(--ring)!important; transition:all .15s ease!important;
}
.stButton > button:hover{ transform:translateY(-3px) scale(1.02); filter:brightness(1.08); }
.stButton > button:focus{ outline:none!important; box-shadow:0 0 0 4px var(--ring)!important; }
.stApp,.main,[data-testid="stSidebar"]{ direction:rtl; text-align:right; }
label,.stMarkdown,.stText,.stCaption{ text-align:right!important; }
*[title="Press Enter to apply"]{ display:none !important; }
</style>
""", unsafe_allow_html=True)

# ====== כותרת ======
st.markdown("<h1>מערכת שיבוץ סטודנטים – התאמה חכמה</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#475569;margin-top:-8px;'>שיבוץ אוטומטי לפי תחום, עיר ובקשות – ללא הגדרות מסובכות.</p>", unsafe_allow_html=True)

# ====== נתונים וניקוד ======
@dataclass
class Weights:
    w_field: float = 0.70
    w_city: float = 0.20
    w_special: float = 0.10

STU_COLS = {
    "id": ["מספר תעודת זהות","תעודת זהות","ת\"ז","ת.ז","תז","מספר זהות","מס' זהות","ID","id","student_id","ת\"ז הסטודנט","מספר תז"],
    "first": ["שם פרטי","שם הסטודנט","פרטי"],
    "last": ["שם משפחה","משפחה"],
    "address": ["כתובת","כתובת הסטודנט","רחוב","כתובת מלאה"],
    "city": ["עיר מגורים","עיר","ישוב","יישוב"],
    "phone": ["טלפון","מספר טלפון","נייד","סלולרי","מס' טלפון"],
    "email": ["דוא\"ל","דוא״ל","אימייל","מייל","דואר אלקטרוני","כתובת אימייל","כתובת מייל"],
    "preferred_field": ["תחום מועדף","תחומים מועדפים","תחום רצוי","העדפת תחום"],
    "special_req": ["בקשה מיוחדת","התחשבות","בקשות"],
    "partner": ["בן/בת זוג להכשרה","בן\\בת זוג להכשרה","בן/בת זוג","בן\\בת זוג","בן זוג להכשרה","בת זוג להכשרה"]
}

SITE_COLS = {
    "name": ["מוסד / שירות הכשרה","מוסד","שם מוסד ההתמחות","שם המוסד","מקום ההתנסות","שם מקום ההתנסות","שם מקום ההתמחות","שם השירות","ארגון","שם ארגון"],
    "field": ["תחום ההתמחות","תחום התמחות","תחום","תחומי התמחות"],
    "street": ["רחוב","כתובת","כתובת מלאה"],
    "city": ["עיר","ישוב","יישוב"],
    "capacity": ["מספר סטודנטים שניתן לקלוט השנה","מספר סטודנטים שניתן לקלוט","קיבולת","כמות סטודנטים","מס' סטודנטים"],
    "sup_first": ["שם פרטי","שם פרטי (מדריך)"],
    "sup_last": ["שם משפחה","שם משפחה (מדריך)"],
    "phone": ["טלפון","נייד","מס' טלפון"],
    "email": ["אימייל","כתובת מייל","דוא\"ל","דוא״ל","מייל","דואר אלקטרוני"]
}

def norm(s: str) -> str:
    return re.sub(r'\s+', ' ', str(s)).strip().lower().replace('\"','"')

def pick_col_exact(df: pd.DataFrame, options: List[str]) -> Optional[str]:
    for opt in options:
        if opt in df.columns:
            return opt
    return None

def pick_col_fuzzy(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    cols = list(df.columns)
    low = [norm(c) for c in cols]
    keys = [norm(k) for k in keywords]
    for i, c in enumerate(low):
        for k in keys:
            if k and k in c:
                return cols[i]
    return None

def pick_col_smart(df: pd.DataFrame, options: List[str], fallback_keywords: List[str]) -> Optional[str]:
    c = pick_col_exact(df, options)
    if c: return c
    return pick_col_fuzzy(df, fallback_keywords or options)

def read_any(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded, encoding="utf-8-sig")
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded)
    try:
        return pd.read_excel(uploaded)
    except Exception:
        return pd.read_csv(uploaded, encoding="utf-8-sig")

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

# ====== עוזרי סדרות בטוחות ======
def series_or_default(df: pd.DataFrame, col: Optional[str], default_value) -> pd.Series:
    """Return a Series: if column exists -> that series; else a Series filled with default_value."""
    if col in df.columns:
        return df[col]
    # Make a series of same length
    return pd.Series([default_value] * len(df), index=df.index)

# ====== Resolve ללא UI ======
def resolve_students(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # locate columns
    id_col = pick_col_smart(out, STU_COLS["id"], ["זהות","ת\"ז","ת.ז","id"])
    first_col = pick_col_smart(out, STU_COLS["first"], ["שם פרטי","שם"])
    last_col  = pick_col_smart(out, STU_COLS["last"], ["שם משפחה"])
    phone_col = pick_col_smart(out, STU_COLS["phone"], ["טלפון","נייד"])
    email_col = pick_col_smart(out, STU_COLS["email"], ["מייל","דוא"])
    city_col  = pick_col_smart(out, STU_COLS["city"], ["עיר","ישוב"])
    addr_col  = pick_col_smart(out, STU_COLS["address"], ["כתובת","רחוב"])
    pref_col  = pick_col_smart(out, STU_COLS["preferred_field"], ["תחום"])
    req_col   = pick_col_smart(out, STU_COLS["special_req"], ["בקשה","התחשבות"])
    partner_col = pick_col_smart(out, STU_COLS["partner"], ["בן","בת","זוג","הכשרה"])

    # build safe series (IDs fallback to 1..N)
    stu_id = series_or_default(out, id_col, default_value=None)
    if stu_id.isna().all() or (stu_id.astype(str).str.strip() == "").all():
        stu_id = pd.Series(range(1, len(out)+1), index=out.index)

    out["stu_id"]    = stu_id.astype(str).str.strip()
    out["stu_first"] = series_or_default(out, first_col, "").astype(str).str.strip()
    out["stu_last"]  = series_or_default(out, last_col,  "").astype(str).str.strip()

    # if no first/last but have full name -> split
    if (out["stu_first"] == "").all() or (out["stu_last"] == "").all():
        full_col = pick_col_fuzzy(out, ["שם מלא","שם","שם סטודנט"])
        if full_col:
            parts = out[full_col].astype(str).str.strip().str.split(r"\s+", n=1, expand=True)
            out.loc[out["stu_first"].eq(""), "stu_first"] = parts[0]
            out.loc[out["stu_last"].eq(""),  "stu_last"]  = parts[1].fillna("")

    out["stu_phone"]   = series_or_default(out, phone_col, "").astype(str).str.strip()
    out["stu_email"]   = series_or_default(out, email_col, "").astype(str).str.strip()
    out["stu_city"]    = series_or_default(out, city_col,  "").astype(str).str.strip()
    out["stu_address"] = series_or_default(out, addr_col,  "").astype(str).str.strip()
    out["stu_pref"]    = series_or_default(out, pref_col,  "").astype(str).str.strip()
    out["stu_req"]     = series_or_default(out, req_col,   "").astype(str).str.strip()
    out["stu_partner"] = series_or_default(out, partner_col,"").astype(str).str.strip()
    return out

def resolve_sites(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    name_col   = pick_col_smart(out, SITE_COLS["name"], ["מוסד","שירות","מקום","התנסות","התמחות","שם"])
    field_col  = pick_col_smart(out, SITE_COLS["field"], ["תחום","התמחות"])
    street_col = pick_col_smart(out, SITE_COLS["street"],["כתובת","רחוב"])
    city_col   = pick_col_smart(out, SITE_COLS["city"],  ["עיר","ישוב"])
    cap_col    = pick_col_smart(out, SITE_COLS["capacity"], ["קיבולת","סטודנטים","כמות"])
    supf_col   = pick_col_smart(out, SITE_COLS["sup_first"], ["שם פרטי"])
    supl_col   = pick_col_smart(out, SITE_COLS["sup_last"],  ["שם משפחה"])

    out["site_name"]   = series_or_default(out, name_col,   "מוסד ללא שם").astype(str).str.strip()
    out["site_field"]  = series_or_default(out, field_col,  "").astype(str).str.strip()
    out["site_street"] = series_or_default(out, street_col, "").astype(str).str.strip()
    out["site_city"]   = series_or_default(out, city_col,   "").astype(str).str.strip()

    # >>> Fix: ensure capacity default is a Series, not a scalar
    cap_series = series_or_default(out, cap_col, 1)
    out["site_capacity"] = pd.to_numeric(cap_series, errors="coerce").fillna(1).astype(int)
    out["capacity_left"] = out["site_capacity"].astype(int)

    # Supervisor as Series
    ff = series_or_default(out, supf_col, "")
    ll = series_or_default(out, supl_col, "")
    out["supervisor"] = (ff.astype(str) + " " + ll.astype(str)).str.strip()

    out["site_type"] = out.apply(lambda r: detect_site_type(r.get("site_name"), r.get("site_field")), axis=1)
    for c in ["site_name","site_field","site_street","site_city","site_type","supervisor"]:
        out[c] = out[c].astype(str).apply(normalize_text)
    return out

# ====== Scoring & Matching ======
def tokens(s: str) -> List[str]:
    return [t for t in str(s).replace(","," ").replace("/"," ").replace("-"," ").split() if t]

def field_match_score(stu_pref: str, site_field: str) -> float:
    if not stu_pref: return 50.0
    sp = stu_pref.strip(); sf = site_field.strip()
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
    field_s  = field_match_score(stu.get("stu_pref",""), site.get("site_field",""))
    city_s   = 100.0 if same_city else 65.0
    special_s= special_req_score(stu.get("stu_req",""), site.get("site_type",""), same_city)
    score = W.w_field*field_s + W.w_city*city_s + W.w_special*special_s
    return float(np.clip(score, 0, 100))

def find_partner_map(students_df: pd.DataFrame) -> Dict[str,str]:
    ids = set(students_df["stu_id"])
    m = {}
    for _, r in students_df.iterrows():
        sid=r["stu_id"]; pid=r.get("stu_partner","")
        if not pid: continue
        if pid in ids and pid != sid: m[sid]=pid; continue
        for _, r2 in students_df.iterrows():
            full=f"{r2.get('stu_first','')} {r2.get('stu_last','')}".strip()
            if pid and full and pid in full and r2["stu_id"] != sid:
                m[sid]=r2["stu_id"]; break
    return m

def candidate_table_for_student(stu: pd.Series, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    tmp = sites_df.copy()
    tmp["score"] = tmp.apply(lambda r: compute_score(stu, r, W), axis=1)
    return tmp.sort_values(["score"], ascending=[False])

def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    separate_couples=True; top_k=10
    def dec_cap(idx:int): sites_df.at[idx,"capacity_left"]=int(sites_df.at[idx,"capacity_left"])-1
    results=[]; processed=set(); partner_map=find_partner_map(students_df)
    # Couples
    for _, s in students_df.iterrows():
        sid=s["stu_id"]
        if sid in processed: continue
        pid=partner_map.get(sid)
        if pid and partner_map.get(pid)==sid:
            r2=students_df[students_df["stu_id"]==pid]
            if r2.empty: continue
            s2=r2.iloc[0]
            c1=candidate_table_for_student(s, sites_df[sites_df["capacity_left"]>0], W).head(top_k)
            c2=candidate_table_for_student(s2, sites_df[sites_df["capacity_left"]>0], W).head(top_k)
            best=(-1.0,None,None)
            for i1,r1 in c1.iterrows():
                for i2,r2 in c2.iterrows():
                    if i1==i2: continue
                    if r1.get("supervisor") and r1.get("supervisor")==r2.get("supervisor"): continue
                    sc=float(r1["score"])+float(r2["score"])
                    if sc>best[0]: best=(sc,i1,i2)
            if best[1] is not None:
                rsite1=sites_df.loc[best[1]]; rsite2=sites_df.loc[best[2]]
                dec_cap(best[1]); dec_cap(best[2])
                results.append((s,rsite1)); results.append((s2,rsite2))
                processed.add(sid); processed.add(pid)
    # Singles
    for _, s in students_df.iterrows():
        sid=s["stu_id"]
        if sid in processed: continue
        c=candidate_table_for_student(s, sites_df[sites_df["capacity_left"]>0], W).head(top_k)
        if not c.empty:
            idx=c.index[0]; r=sites_df.loc[idx]
            dec_cap(idx); results.append((s,r)); processed.add(sid)
    # Export
    rows=[]
    for s,r in results:
        rows.append({
            "ת\"ז הסטודנט": s.get("stu_id"),
            "שם פרטי": s.get("stu_first"),
            "שם משפחה": s.get("stu_last"),
            "כתובת": s.get("stu_address"),
            "עיר": s.get("stu_city"),
            "מספר טלפון": s.get("stu_phone"),
            "אימייל": s.get("stu_email"),
            "אחוז התאמה": round(compute_score(s,r,Weights()),1),
            "שם מקום ההתמחות": r.get("site_name"),
            "עיר המוסד": r.get("site_city"),
            "סוג מקום השיבוץ": r.get("site_type"),
            "תחום ההתמחות במוסד": r.get("site_field"),
        })
    out=pd.DataFrame(rows)
    desired=["ת\"ז הסטודנט","שם פרטי","שם משפחה","כתובת","עיר","מספר טלפון","אימייל",
             "אחוז התאמה","שם מקום ההתמחות","עיר המוסד","סוג מקום השיבוץ","תחום ההתמחות במוסד"]
    return out[[c for c in desired if c in out.columns]]

# ====== 1) הוראות שימוש ======
st.markdown("## 📘 הוראות שימוש")
st.markdown("""
1. הכינו **קובץ סטודנטים** (CSV/XLSX) ושמרו שמות עמודות נפוצים (ת\"ז, שם פרטי, שם משפחה, עיר, כתובת, טלפון, אימייל...).  
2. הכינו **קובץ אתרים/מדריכים** (CSV/XLSX) עם: שם מוסד/שירות, תחום התמחות, כתובת/רחוב, עיר, קיבולת.  
3. לחצו **בצע שיבוץ** והורידו את קובץ התוצאות.  
**הערה:** המערכת מזהה אוטומטית שם-עמודות (כולל וריאציות), ואם חסר — ממשיכה עם ברירת מחדל ולא נופלת.
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
        try:
            df_students_raw = read_any(students_file)
            drop_cols = [c for c in df_students_raw.columns if str(c).startswith("Unnamed")]
            df_students_raw.drop(columns=drop_cols, inplace=True, errors="ignore")
            st.caption("הצצה ל-5 הרשומות הראשונות:")
            st.dataframe(df_students_raw.head(5), use_container_width=True)
        except Exception as e:
            st.error("לא ניתן לקרוא את הקובץ.")
            df_students_raw = None
    else:
        df_students_raw = None

with colB:
    sites_file = st.file_uploader("קובץ אתרי התמחות/מדריכים", type=["csv","xlsx","xls"], key="sites_file")
    if sites_file is not None:
        try:
            df_sites_raw = read_any(sites_file)
            drop_cols = [c for c in df_sites_raw.columns if str(c).startswith("Unnamed")]
            df_sites_raw.drop(columns=drop_cols, inplace=True, errors="ignore")
            st.caption("הצצה ל-5 הרשומות הראשונות:")
            st.dataframe(df_sites_raw.head(5), use_container_width=True)
        except Exception as e:
            st.error("לא ניתן לקרוא את הקובץ.")
            df_sites_raw = None
    else:
        df_sites_raw = None

# ====== 4) שיבוץ ======
st.markdown("## ⚙️ ביצוע השיבוץ")
run_btn = st.button("🚀 בצע שיבוץ", use_container_width=True)

result_df = None
if run_btn:
    if df_students_raw is None or df_sites_raw is None:
        st.error("נא להעלות את שני הקבצים לפני הפעלת השיבוץ.")
    else:
        students = resolve_students(df_students_raw)
        sites = resolve_sites(df_sites_raw)
        result_df = greedy_match(students, sites, Weights())
        st.success("השיבוץ הושלם ✓")

# ====== 5) תוצאות ======
st.markdown("## 📊 תוצאות השיבוץ")
if 'result_df' in locals() and result_df is not None and not result_df.empty:
    st.dataframe(result_df, use_container_width=True)
    csv = result_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("⬇️ הורדת קובץ התוצאות (CSV)", data=csv, file_name="student_site_matching.csv", mime="text/csv")
else:
    st.caption("טרם הופעל שיבוץ או שאין תוצאות להצגה.")
