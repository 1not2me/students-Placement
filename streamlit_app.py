
# matcher_streamlit_clean.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

# ---------------- Page & Style ----------------
st.set_page_config(page_title="מערכת שיבוץ סטודנטים – נקי ומודרני", layout="wide")

st.markdown("""
<style>
:root{
  --ink:#0f172a;
  --muted:#475569;
  --card:rgba(255,255,255,.86);
  --ring:rgba(99,102,241,.25);
}

/* RTL + base fonts */
html, body, [class*="css"]{ font-family: system-ui, "Segoe UI", Arial; }
.stApp, .main{ direction:rtl; text-align:right; }

/* Background */
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 8% 8%, #e0f7fa 0%, transparent 65%),
    radial-gradient(1000px 500px at 92% 12%, #ede7f6 0%, transparent 60%),
    radial-gradient(900px 500px at 20% 90%, #fff3e0 0%, transparent 55%);
}
.block-container{ padding-top:1.1rem; }

/* Centered card */
.center-card{
  background:var(--card);
  border:1px solid #e2e8f0;
  border-radius:18px;
  padding:22px 22px;
  box-shadow:0 10px 28px rgba(2,6,23,.08);
}
.center-wrap{ max-width:900px; margin:24px auto; }

h1,h2,h3{ color:var(--ink); }
.small-muted{ color:var(--muted); font-size:.9rem; }

/* Inputs inside forms */
[data-testid="stForm"] .stButton>button{
  border-radius:12px;
  padding:.6rem 1rem;
  box-shadow:0 8px 14px rgba(99,102,241,.18);
}
[data-testid="stForm"] input, [data-testid="stForm"] select{ direction:rtl; text-align:right; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="center-wrap">
  <h1>🏷️ מערכת שיבוץ סטודנטים – התאמה חכמה</h1>
  <p class="small-muted">העלו שני קבצים (סטודנטים ואתרי התמחות) ובצעו שיבוץ אוטומטי. ללא פרמטרים מסובכים.</p>
</div>
""", unsafe_allow_html=True)

# ---------------- Column synonyms & structures ----------------
@dataclass
class Weights:
    # fixed weights (no sliders in UI)
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
    # Normalize
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
    # supervisor
    sup_first = pick_col(out, SITE_COLS["sup_first"])
    sup_last  = pick_col(out, SITE_COLS["sup_last"])
    out["supervisor"] = ""
    if sup_first or sup_last:
        ff = out[sup_first] if sup_first else ""
        ll = out[sup_last]  if sup_last  else ""
        out["supervisor"] = (ff.astype(str) + " " + ll.astype(str)).str.strip()
    # Normalize
    for c in ["site_name","site_field","site_street","site_city","site_type","supervisor"]:
        out[c] = out[c].apply(normalize_text)
    return out

def tokens(s: str) -> List[str]:
    return [t for t in str(s).replace(","," ").replace("/"," ").replace("-"," ").split() if t]

def field_match_score(stu_pref: str, site_field: str) -> float:
    """Return 0..100 based on exact/partial overlap — calibrated to avoid low 10/30 plateaus."""
    if not stu_pref: 
        return 50.0  # בסיס אם אין העדפה – לא נמוך מידי
    sp = stu_pref.strip()
    sf = site_field.strip()
    if not sf:
        return 40.0
    if sp and sp in sf:
        return 90.0
    # partial overlap by tokens
    tp = set([w for w in tokens(sp) if len(w) > 1])
    tf = set([w for w in tokens(sf) if len(w) > 1])
    inter = tp.intersection(tf)
    if inter:
        return 75.0
    return 45.0

def special_req_score(req: str, site_type: str, same_city: bool) -> float:
    if not req:
        return 70.0  # ניטרלי-חיובי
    s = req
    # אם ביקש "לא בבית חולים" – ואתר בית חולים → אי-התאמה קיצונית
    if "לא בבית חולים" in s and site_type == "בית חולים":
        return 0.0
    # אם ביקש "קרוב" – קירוב לפי עיר זהה
    if "קרוב" in s:
        return 90.0 if same_city else 55.0
    return 75.0

def compute_score(stu: pd.Series, site: pd.Series, W: Weights) -> float:
    same_city = (stu.get("stu_city") and site.get("site_city") and stu.get("stu_city") == site.get("site_city"))
    field_s  = field_match_score(stu.get("stu_pref",""), site.get("site_field",""))
    city_s   = 100.0 if same_city else 65.0  # אם לא אותה עיר – לא 0, כדי לא להוריד מדי
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
        # match by name
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
    # internal settings (no UI)
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

    # Build export (NO distance fields)
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

# ---------------- Centered Upload UI ----------------
W = Weights()
df_students_raw = None
df_sites_raw = None
result_df = None

col_left, col_mid, col_right = st.columns([1, 1.6, 1], gap="large")
with col_mid:
    with st.form("upload_form", clear_on_submit=False):
        st.markdown('<div class="center-card">', unsafe_allow_html=True)
        st.subheader("📥 העלאת קבצים")
        st.write("נא להעלות **קובץ סטודנטים** ו**קובץ אתרי התמחות** (CSV/XLSX).")
        f_students = st.file_uploader("קובץ סטודנטים", type=["csv","xlsx","xls"], key="stu")
        f_sites    = st.file_uploader("קובץ אתרי התמחות/מדריכים", type=["csv","xlsx","xls"], key="site")
        submitted = st.form_submit_button("🚀 בצע שיבוץ", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

if submitted:
    if f_students is None or f_sites is None:
        st.error("נא להעלות את שני הקבצים.")
    else:
        try:
            df_students_raw = read_any(f_students)
            df_sites_raw = read_any(f_sites)
            # cleanup unnamed
            for df in (df_students_raw, df_sites_raw):
                drop_cols = [c for c in df.columns if str(c).startswith("Unnamed")]
                df.drop(columns=drop_cols, inplace=True, errors="ignore")
            students = resolve_students(df_students_raw)
            sites = resolve_sites(df_sites_raw)
            result_df = greedy_match(students, sites, W)
            st.success("השיבוץ הושלם ✓")
        except Exception as e:
            st.exception(e)

# ---------------- Results ----------------
if result_df is not None and not result_df.empty:
    st.subheader("📊 תוצאות השיבוץ")
    st.dataframe(result_df, use_container_width=True)
    csv = result_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("⬇️ הורדת קובץ השיבוץ (CSV)", data=csv, file_name="student_site_matching.csv", mime="text/csv")

# ---------------- Help / Guide ----------------
st.markdown("""
<div class="center-wrap">
  <div class="center-card">
    <h3>❓ מדריך שימוש מהיר</h3>
    <ol>
      <li>הכינו <b>קובץ סטודנטים</b> עם העמודות: שם פרטי, שם משפחה, תעודת זהות, כתובת/עיר, טלפון, אימייל. אופציונלי: תחום מועדף, בקשה מיוחדת, בן/בת זוג להכשרה.</li>
      <li>הכינו <b>קובץ אתרים/מדריכים</b> עם העמודות: מוסד/שירות, תחום התמחות, רחוב, עיר, מספר סטודנטים שניתן לקלוט השנה. אופציונלי: שם פרטי+שם משפחה של המדריך, טלפון, אימייל.</li>
      <li>לחצו על <b>בצע שיבוץ</b>. המערכת תחשב <b>אחוז התאמה</b> לפי התאמה לתחום, התאמת עיר ובקשות מיוחדות, ותשמור על קיבולת ואת הפרדת בני/בנות זוג (לא אותו מוסד/מדריך).</li>
      <li>הורידו את קובץ התוצאות בלחיצה על כפתור ההורדה.</li>
    </ol>
    <p class="small-muted">הערות: אם תוסיפו עמודת העדפה (תחום מועדף) הדיוק יעלה. בקשה כמו "לא בבית חולים" תפסול מוסדות מסוג בית חולים.</p>
  </div>
</div>
""", unsafe_allow_html=True)
