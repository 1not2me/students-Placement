
# matcher_streamlit_beauty.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

# ===================== Page & Global Style =====================
st.set_page_config(page_title="מערכת שיבוץ סטודנטים – התאמה חכמה", layout="wide")

st.markdown("""
<style>
:root{
  --ink:#0f172a;
  --muted:#475569;
  --brand:#6366f1;
  --card:rgba(255,255,255,.86);
  --ring:rgba(99,102,241,.25);
  --ok:#16a34a;
  --warn:#f59e0b;
  --bad:#ef4444;
}

html, body, [class*="css"]{ font-family: system-ui, "Segoe UI", Arial; }
.stApp, .main{ direction:rtl; text-align:right; }

/* Background (soft gradients) */
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1100px 500px at 8% 8%, #e0f7fa 0%, transparent 65%),
    radial-gradient(900px 450px at 92% 12%, #ede7f6 0%, transparent 60%),
    radial-gradient(900px 480px at 20% 90%, #fff3e0 0%, transparent 55%);
}
.block-container{ padding-top:1.0rem; }

/* Hero */
.hero{
  max-width:1000px; margin:20px auto 10px auto; padding:24px 28px;
  background:linear-gradient(135deg, rgba(255,255,255,.88), rgba(255,255,255,.78));
  border:1px solid #e5e7eb; border-radius:22px;
  box-shadow:0 18px 50px rgba(2,6,23,.06);
}
.hero h1{ margin:0 0 6px 0; color:var(--ink); font-size:2.0rem; }
.hero p{ margin:0; color:var(--muted); }

/* Section cards */
.section{
  max-width:1100px; margin:20px auto; padding:22px 22px;
  background:var(--card);
  border:1px solid #e6e9f2; border-radius:18px;
  box-shadow:0 14px 36px rgba(2,6,23,.07);
}
.section h3{ margin-top:0; color:var(--ink); }
.section .muted{ color:var(--muted); }

/* Upload form */
.upload-card{ padding:10px 14px; border-radius:14px; border:1px dashed #d1d5db; background:rgba(255,255,255,.65); }
.stButton>button{
  border-radius:12px; padding:.6rem 1rem;
  box-shadow:0 10px 20px rgba(99,102,241,.20);
}

/* Tables spacing */
[data-testid="stHorizontalBlock"]{ gap:1.2rem; }

/* Pills / labels */
.pill{ display:inline-block; padding:.25rem .6rem; border-radius:999px; background:#eef2ff; color:#3730a3; font-size:.85rem; }

/* Headings */
h2.section-title{ display:flex; align-items:center; gap:.5rem; color:#111827; margin:0 0 .75rem 0; }
h2.section-title .emoji{ font-size:1.25rem; }
</style>
""", unsafe_allow_html=True)

# ===================== Hero =====================
st.markdown("""
<div class="hero">
  <h1>🏷️ מערכת שיבוץ סטודנטים – התאמה חכמה</h1>
  <p>העלו שני קבצים (סטודנטים ואתרי התמחות), בצעו שיבוץ אוטומטי – פשוט, מסודר ואלגנטי.</p>
</div>
""", unsafe_allow_html=True)

# ===================== Data & Logic =====================
@dataclass
class Weights:
    # קבועים – אין סליידרים או פרמטרים במסך
    w_field: float = 0.70    # התאמה לתחום
    w_city: float = 0.20     # התאמת עיר
    w_special: float = 0.10  # בקשות מיוחדות

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

def resolve_students(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["stu_id"]    = out[pick_col(out, STU_COLS["id"])]
    out["stu_first"] = out[pick_col(out, STU_COLS["first"])]
    out["stu_last"]  = out[pick_col(out, STU_COLS["last"])]
    out["stu_phone"] = out[pick_col(out, STU_COLS["phone"])]
    out["stu_email"] = out[pick_col(out, STU_COLS["email"])]
    out["stu_city"]  = out[pick_col(out, STU_COLS["city"])] if pick_col(out, STU_COLS["city"]) else ""
    out["stu_address"] = out[pick_col(out, STU_COLS["address"])] if pick_col(out, STU_COLS["address"]) else ""
    pref_col = pick_col(out, STU_COLS["preferred_field"])
    out["stu_pref"] = out[pref_col] if pref_col else ""
    out["stu_req"]  = out[pick_col(out, STU_COLS["special_req"])] if pick_col(out, STU_COLS["special_req"]) else ""
    out["stu_partner"] = out[pick_col(out, STU_COLS["partner"])] if pick_col(out, STU_COLS["partner"]) else ""
    for c in ["stu_id","stu_first","stu_last","stu_phone","stu_email","stu_city","stu_address","stu_pref","stu_req","stu_partner"]:
        out[c] = out[c].apply(normalize_text)
    return out

def resolve_sites(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["site_name"]  = out[pick_col(out, SITE_COLS["name"])]
    out["site_field"] = out[pick_col(out, SITE_COLS["field"])]
    out["site_street"]= out[pick_col(out, SITE_COLS["street"])] if pick_col(out, SITE_COLS["street"]) else ""
    out["site_city"]  = out[pick_col(out, SITE_COLS["city"])] if pick_col(out, SITE_COLS["city"]) else ""
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
    if not stu_pref: 
        return 50.0
    sp = stu_pref.strip()
    sf = site_field.strip()
    if not sf:
        return 40.0
    if sp and sp in sf:
        return 90.0
    tp = set([w for w in tokens(sp) if len(w) > 1])
    tf = set([w for w in tokens(sf) if len(w) > 1])
    inter = tp.intersection(tf)
    if inter:
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
        sid = r["stu_id"]
        pid = r.get("stu_partner","")
        if not pid: 
            continue
        if pid in ids and pid != sid:
            m[sid] = pid
            continue
        for _, r2 in students_df.iterrows():
            full = f"{r2.get('stu_first','')} {r2.get('stu_last','')}".strip()
            if pid and full and pid in full and r2["stu_id"] != sid:
                m[sid] = r2["stu_id"]
                break
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

    results = []
    processed = set()
    partner_map = find_partner_map(students_df)

    # Couples first
    for _, s in students_df.iterrows():
        sid = s["stu_id"]
        if sid in processed: 
            continue
        pid = partner_map.get(sid)
        if pid and partner_map.get(pid) == sid:
            partner_row = students_df[students_df["stu_id"] == pid]
            if partner_row.empty:
                continue
            s2 = partner_row.iloc[0]
            cand1 = candidate_table_for_student(s, sites_df[sites_df["capacity_left"]>0], W).head(top_k)
            cand2 = candidate_table_for_student(s2, sites_df[sites_df["capacity_left"]>0], W).head(top_k)
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

    # Singles
    for _, s in students_df.iterrows():
        sid = s["stu_id"]
        if sid in processed: 
            continue
        cand = candidate_table_for_student(s, sites_df[sites_df["capacity_left"]>0], W).head(top_k)
        if not cand.empty:
            chosen_idx = cand.index[0]
            rsite = sites_df.loc[chosen_idx]
            dec_cap(chosen_idx)
            results.append((s, rsite))
            processed.add(sid)

    rows = []
    for s, r in results:
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
    return out[[c for c in desired if c in out.columns]]

W = Weights()

# ===================== 1) הוראות שימוש =====================
st.markdown("""
<div class="section">
  <h2 class="section-title"><span class="emoji">📘</span> הוראות שימוש</h2>
  <ol>
    <li>הכינו <b>קובץ סטודנטים</b> (CSV/XLSX) עם: שם פרטי, שם משפחה, תעודת זהות, כתובת/עיר, טלפון, אימייל. אופציונלי: תחום מועדף, בקשה מיוחדת, בן/בת זוג להכשרה.</li>
    <li>הכינו <b>קובץ אתרי התמחות/מדריכים</b> (CSV/XLSX) עם: מוסד/שירות, תחום התמחות, רחוב, עיר, מספר סטודנטים שניתן לקלוט השנה. אופציונלי: שם פרטי+שם משפחה של המדריך, טלפון, אימייל.</li>
    <li>לחצו על <b>בצע שיבוץ</b>. אחוז ההתאמה מחושב לפי התאמת תחום (70%), התאמת עיר (20%) ובקשות מיוחדות (10%), כולל הפרדת בני/בנות זוג ואכיפת קיבולת.</li>
    <li>בסיום, הורידו את קובץ התוצאות בלחיצה על כפתור ההורדה.</li>
  </ol>
  <div class="muted">הערה: העמוד מזהה אוטומטית וריאציות נפוצות לשמות העמודות בעברית.</div>
</div>
""", unsafe_allow_html=True)

# ===================== 2) העלאת קבצים =====================
with st.container():
    st.markdown("""
    <div class="section">
      <h2 class="section-title"><span class="emoji">📤</span> העלאת קבצים</h2>
      <div class="upload-card">
        העלו קובץ סטודנטים וקובץ אתרי התמחות (CSV, XLSX, XLS).
      </div>
    </div>
    """, unsafe_allow_html=True)

    colA, colB = st.columns(2, gap="large")
    with colA:
        students_file = st.file_uploader("קובץ סטודנטים", type=["csv","xlsx","xls"], key="students_file")
        if students_file is not None:
            st.caption("הצצה ל-5 הרשומות הראשונות:")
            try:
                df_students_raw = read_any(students_file)
                df_students_raw_preview = df_students_raw.head(5)
                st.dataframe(df_students_raw_preview, use_container_width=True)
            except Exception as e:
                st.error("לא ניתן לקרוא את הקובץ. ודאו שהוא CSV/XLSX תקין.")
                df_students_raw = None
        else:
            df_students_raw = None

    with colB:
        sites_file = st.file_uploader("קובץ אתרי התמחות/מדריכים", type=["csv","xlsx","xls"], key="sites_file")
        if sites_file is not None:
            st.caption("הצצה ל-5 הרשומות הראשונות:")
            try:
                df_sites_raw = read_any(sites_file)
                df_sites_raw_preview = df_sites_raw.head(5)
                st.dataframe(df_sites_raw_preview, use_container_width=True)
            except Exception as e:
                st.error("לא ניתן לקרוא את הקובץ. ודאו שהוא CSV/XLSX תקין.")
                df_sites_raw = None
        else:
            df_sites_raw = None

# ===================== 3) דוגמה לשימוש =====================
# Small built-in example tables for visual guidance (not used for matching)
example_students = pd.DataFrame([
    {"שם פרטי":"רות", "שם משפחה":"כהן", "תעודת זהות":"123456789", "כתובת":"הרצל 12", "עיר מגורים":"תל אביב", "טלפון":"0501111111", "דוא\"ל":"ruth@example.com", "תחום מועדף":"בריאות הנפש"},
    {"שם פרטי":"יואב", "שם משפחה":"לוי", "תעודת זהות":"987654321", "כתובת":"דיזנגוף 80", "עיר מגורים":"תל אביב", "טלפון":"0502222222", "דוא\"ל":"yoav@example.com", "תחום מועדף":"רווחה"}
])
example_sites = pd.DataFrame([
    {"מוסד / שירות הכשרה":"מרכז חוסן תל אביב", "תחום ההתמחות":"בריאות הנפש", "רחוב":"אבן גבירול 1", "עיר":"תל אביב", "מספר סטודנטים שניתן לקלוט השנה":2},
    {"מוסד / שירות הכשרה":"מחלקת רווחה רמת גן", "תחום ההתמחות":"רווחה", "רחוב":"ביאליק 10", "עיר":"רמת גן", "מספר סטודנטים שניתן לקלוט השנה":1},
])

st.markdown("""
<div class="section">
  <h2 class="section-title"><span class="emoji">🧪</span> דוגמה לשימוש</h2>
  <div class="muted">כך נראים קבצים בסכימה מומלצת. ניתן להוריד ולמלא כבסיס.</div>
</div>
""", unsafe_allow_html=True)

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

# ===================== 4) שיבוץ =====================
st.markdown("""
<div class="section">
  <h2 class="section-title"><span class="emoji">⚙️</span> ביצוע השיבוץ</h2>
  <div class="muted">השיבוץ מתחשב בתחום, בעיר, בבקשות מיוחדות, בקיבולת ובבני/בנות זוג. לחצו להפעלה.</div>
</div>
""", unsafe_allow_html=True)

run_btn = st.button("🚀 בצע שיבוץ", use_container_width=True)

result_df = None
if run_btn:
    if students_file is None or sites_file is None:
        st.error("נא להעלות את שני הקבצים לפני הפעלת השיבוץ.")
    else:
        try:
            # Clean + resolve
            for df in (df_students_raw, df_sites_raw):
                drop_cols = [c for c in df.columns if str(c).startswith("Unnamed")]
                df.drop(columns=drop_cols, inplace=True, errors="ignore")
            students = resolve_students(df_students_raw)
            sites = resolve_sites(df_sites_raw)
            result_df = greedy_match(students, sites, W)
            st.success("השיבוץ הושלם ✓")
        except Exception as e:
            st.exception(e)

# ===================== 5) תוצאות השיבוץ =====================
st.markdown("""
<div class="section">
  <h2 class="section-title"><span class="emoji">📊</span> תוצאות השיבוץ</h2>
</div>
""", unsafe_allow_html=True)

if result_df is not None and not result_df.empty:
    st.dataframe(result_df, use_container_width=True)
    csv = result_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("⬇️ הורדת קובץ התוצאות (CSV)", data=csv, file_name="student_site_matching.csv", mime="text/csv")
else:
    st.caption("טרם הופעל שיבוץ או שאין תוצאות להצגה.")
