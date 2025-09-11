# streamlit_app.py
# ---------------------------------------------------------
# שיבוץ סטודנטים לפי "מי-מתאים-ל" (גמיש):
# - המשתמש מעלה כל קבצי סטודנטים/אתרים (CSV/XLSX) ובוחר גיליונות/עמודות.
# - ניקוד: תחום (חפיפה/הכלה), עיר (נירמול), מרחק (קירבה) + קיבולת.
# - עיצוב RTL בסגנון הדוגמה + מדריך שימוש מובנה.
# - תוצאה: assigned_site, assigned_city, assigned_distance_km, match_score, status
# ---------------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from io import BytesIO
import re, time, math, os

# ========= Geopy (לגיאוקוד) =========
try:
    from geopy.geocoders import Nominatim
    GEOPY_OK = True
except Exception:
    GEOPY_OK = False

# =========================
# הגדרות כלליות + עיצוב
# =========================
st.set_page_config(page_title="שיבוץ סטודנטים – מי-מתאים-ל", layout="wide")

st.markdown("""
<style>
:root{
  --ink:#0f172a; 
  --muted:#475569; 
  --ring:rgba(99,102,241,.25); 
  --card:rgba(255,255,255,.85);
  --border:#e2e8f0;
}

/* RTL + פונטים */
html, body, [class*="css"] { font-family: system-ui, "Segoe UI", Arial; }
.stApp, .main, [data-testid="stSidebar"]{ direction:rtl; text-align:right; }

/* רקע */
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 8% 8%, #e0f7fa 0%, transparent 65%),
    radial-gradient(1000px 500px at 92% 12%, #ede7f6 0%, transparent 60%),
    radial-gradient(900px 500px at 20% 90%, #fff3e0 0%, transparent 55%);
}
.block-container{ padding-top:1.1rem; }

/* כרטיסים */
.card{ background:var(--card); border:1px solid var(--border); border-radius:16px; padding:18px 20px; box-shadow:0 8px 24px rgba(2,6,23,.06); }
.hero{
  background:linear-gradient(180deg, rgba(255,255,255,.96), rgba(255,255,255,.9));
  border:1px solid var(--border); border-radius:18px; padding:22px 20px; box-shadow:0 8px 28px rgba(2,6,23,.06);
}
.hero h1{ margin:0 0 6px 0; color:var(--ink); font-size:28px; }
.hero p{ margin:0; color:var(--muted); }

/* מסגרת לטופס/קונטים */
[data-testid="stForm"], .boxed{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:16px;
  padding:18px 20px;
  box-shadow:0 8px 24px rgba(2,6,23,.06);
}

/* תוויות + נקודתיים מימין */
[data-testid="stWidgetLabel"] p{
  text-align:right; 
  margin-bottom:.25rem; 
  color:var(--muted); 
}
[data-testid="stWidgetLabel"] p::after{ content: " :"; }

/* שדות */
input, textarea, select{ direction:rtl; text-align:right; }

/* KPIs */
.metric{
  display:flex; align-items:center; justify-content:space-between;
  padding:10px 12px; border:1px solid var(--border); border-radius:14px; background:#fff;
}
.metric .label{ color:var(--muted); font-size:.9rem; }
.metric .value{ color:var(--ink); font-weight:700; }

hr{ border-color:var(--border); }
.small{ color:#64748b; font-size:.92rem; }
</style>
""", unsafe_allow_html=True)

# =========================
# קבועים וקבצי קאש
# =========================
GEOCODE_CACHE = Path("./geocode_cache.csv")

# =========================
# פונקציות עזר – קריאה/נירמול/פיצול/מרחק
# =========================
def read_anytable(upload, sheet_name=None):
    """קורא CSV/XLSX; אם XLSX ואין sheet_name -> יטען את הראשון."""
    if upload is None:
        return None, []
    name = upload.name.lower()
    if name.endswith(".csv"):
        try:
            return pd.read_csv(upload), []
        except Exception:
            upload.seek(0)
            return pd.read_csv(upload, encoding="utf-8-sig"), []
    else:
        # Excel
        try:
            xf = pd.ExcelFile(upload)
            sheets = xf.sheet_names
            if sheet_name and sheet_name in sheets:
                return xf.parse(sheet_name), sheets
            else:
                return xf.parse(sheets[0]), sheets
        except Exception:
            return None, []

def _strip(x): 
    return "" if pd.isna(x) else str(x).strip()

def _lc(x): 
    return _strip(x).lower()

_PUNCT_RE = re.compile(r"[\"'`”“׳״\.\!\?\:\;\|\·•\u2022\(\)\[\]\{\}]+")
_WS_RE    = re.compile(r"\s+")
def normalize_text(s: str) -> str:
    s = _strip(s)
    s = _PUNCT_RE.sub(" ", s)
    s = s.replace("-", " ").replace("–", " ").replace("—", " ").replace("/", " ")
    s = _WS_RE.sub(" ", s).strip()
    return s.lower()

def split_multi(raw) -> set:
    if pd.isna(raw): return set()
    s = str(raw).replace("\n", ",")
    s = re.sub(r"[;/|•·•]", ",", s)
    s = s.replace("–", ",").replace("—", ",").replace("/", ",")
    if "," not in s:
        s = re.sub(r"\s{2,}", ",", s)
    items = [normalize_text(p) for p in s.split(",") if normalize_text(p)]
    return set(items)

def overlap_count(set_a: set, set_b: set) -> int:
    cnt = 0
    for a in set_a:
        for b in set_b:
            if not a or not b: 
                continue
            if a == b:
                cnt += 1
            else:
                if (len(a) >= 3 and a in b) or (len(b) >= 3 and b in a):
                    cnt += 1
    return cnt

def haversine_km(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]: return None
    try:
        R = 6371.0
        p1 = math.radians(lat1); p2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c
    except Exception:
        return None

def bytes_for_download(df, filename):
    bio = BytesIO()
    df.to_csv(bio, index=False, encoding="utf-8-sig"); bio.seek(0)
    return bio, filename

# ---- קאש גיאוקוד ----
def load_geocode_cache():
    if GEOCODE_CACHE.exists():
        try:
            df = pd.read_csv(GEOCODE_CACHE)
            return {row["query"]: (row["lat"], row["lon"]) for _, row in df.iterrows()}
        except Exception:
            return {}
    return {}

def save_geocode_cache(cache_dict):
    try:
        df = pd.DataFrame([{"query": k, "lat": v[0], "lon": v[1]} for k, v in cache_dict.items()])
        df.to_csv(GEOCODE_CACHE, index=False, encoding="utf-8-sig")
    except Exception:
        pass

@st.cache_data(show_spinner=False)
def geocode_query(query):
    if not GEOPY_OK: return None
    geolocator = Nominatim(user_agent="student-placement-app")
    time.sleep(1.0)  # נימוס ל-OSM
    try:
        loc = geolocator.geocode(query)
        if loc: return (loc.latitude, loc.longitude)
    except Exception:
        return None
    return None

def geocode_many(queries, country_hint="ישראל"):
    cache = load_geocode_cache()
    out = {}
    for q in queries:
        if not q: out[q] = (None, None); continue
        q_norm = f"{q}, {country_hint}" if country_hint and country_hint not in q else q
        if q_norm in cache: out[q] = cache[q_norm]; continue
        res = geocode_query(q_norm)
        if res is None: out[q] = (None, None)
        else:
            out[q] = (float(res[0]), float(res[1]))
            cache[q_norm] = out[q]
    save_geocode_cache(cache)
    return out

# =========================
# משקולות ניקוד
# =========================
W_DOMAIN_MAIN  = 2.0   # תחום מועדף ↔ תחום ההתמחות
W_DOMAIN_MULTI = 1.0   # חפיפה/הכלה לכל ערך נוסף
W_CITY         = 1.2   # עיר (נירמול)
DEFAULT_W_DISTANCE = 1.8
DEFAULT_MAX_KM     = 60

# =========================
# העלאות + עמוד הבית
# =========================
st.markdown(
    """
<div class="hero">
  <h1>📅 שיבוץ סטודנטים – מי-מתאים-ל</h1>
  <p>העלו כל קובצי סטודנטים ואתרים (CSV/XLSX), מיפו עמודות, חשבו מרחק והפעילו שיבוץ לפי תחום + עיר + קירבה + קיבולת.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("העלאת נתונים")
    up_students = st.file_uploader("קובץ סטודנטים (CSV/XLSX)", type=["csv","xlsx","xls"])
    up_sites    = st.file_uploader("קובץ אתרים/מוסדות (CSV/XLSX)", type=["csv","xlsx","xls"])

    # בחירת גיליון אם Excel
    stu_df, stu_sheets = read_anytable(up_students)
    site_df, site_sheets = read_anytable(up_sites)

    if stu_sheets:
        sheet = st.selectbox("גיליון סטודנטים (Excel)", options=stu_sheets, index=0)
        stu_df, _ = read_anytable(up_students, sheet_name=sheet)
    if site_sheets:
        sheet = st.selectbox("גיליון אתרים (Excel)", options=site_sheets, index=0)
        site_df, _ = read_anytable(up_sites, sheet_name=sheet)

    st.divider()
    st.subheader("מרחק (קירבה)")
    use_distance   = st.checkbox("שקלול מרחק בציון", value=True)
    hard_limit_on  = st.checkbox("אל תשבץ מעבר לטווח מקסימלי", value=True)
    max_km         = st.slider("טווח מקסימלי (ק\"מ)", 10, 200, DEFAULT_MAX_KM, 5)
    w_distance     = st.slider("משקל המרחק", 0.0, 5.0, DEFAULT_W_DISTANCE, 0.1)
    st.caption("אם אין Lat/Lon בקבצים – נבצע גיאוקוד לפי עיר/כתובת (OSM) עם קאש.")

# =========================
# Tabs
# =========================
tab_guide, tab_map, tab_data, tab_match, tab_export = st.tabs(["📖 מדריך", "🗺️ מיפוי עמודות", "📥 תצוגת נתונים", "🧩 שיבוץ", "📤 ייצוא"])

# =========================
# מדריך
# =========================
with tab_guide:
    st.subheader("מדריך מלא לשימוש")
    st.markdown(f"""
1) **העלאת קבצים**: העלו קובץ סטודנטים וקובץ אתרים (CSV/XLSX). אם קובץ Excel – בחרו גיליון בסרגל הימני.  
2) **מיפוי עמודות**: בטאב *מיפוי עמודות* בחרו אילו עמודות מייצגות:
   - עבור **סטודנטים**: מזהה (או יוּצר אוטומטית), שם פרטי/משפחה או שם מלא, עיר מגורים, תחום מועדף, ותחומים מבוקשים (ריבוי ערכים אפשרי).
   - עבור **אתרים**: שם אתר/מוסד, עיר, תחום ההתמחות, קיבולת (ברירת מחדל 1 אם לא קיים), (אופציונלי) Lat/Lon.
3) **שקלול מרחק**: בסרגל הימני אפשר להפעיל ציון קירבה ו/או כלל קשיח "לא לשבץ מעל {DEFAULT_MAX_KM} ק\"מ".  
   נוסחת המרחק: `distance_score = w_distance * (1 - min(distance_km / max_km, 1))`.
4) **שיבוץ**: בטאב *שיבוץ*—הריצו. האלגוריתם Greedy בוחר לכל סטודנט/ית את האתר בעל הציון הגבוה ביותר שנותרה בו קיבולת.
5) **תוצאות**: תקבלו טבלה עם `assigned_site`, **`assigned_city`**, **`assigned_distance_km`**, `match_score`, `status`.  
6) **יצוא**: בטאב *ייצוא* ניתן להוריד CSV או לשמור בשם `assignments.csv`.
""")

# =========================
# מיפוי עמודות (גמיש!)
# =========================
with tab_map:
    if (up_students is None) or (up_sites is None) or (stu_df is None) or (site_df is None):
        st.warning("העלו שני קבצים (סטודנטים ואתרים) כדי למפות עמודות.", icon="⚠️")
    else:
        st.subheader("מיפוי שדות – סטודנטים")
        s_cols = list(stu_df.columns)

        col_id     = st.selectbox("עמודת מזהה סטודנט (או השאירו ריק ליצירה אוטומטית)", options=["(ליצור אוטומטית)"] + s_cols, index=0)
        col_fname  = st.selectbox("שם פרטי (או בחרו 'אין')", options=["(אין)"] + s_cols, index=0)
        col_lname  = st.selectbox("שם משפחה (או בחרו 'אין')", options=["(אין)"] + s_cols, index=0)
        col_fullnm = st.selectbox("שם מלא בודד (אם קיים, עדיף לבחור כאן)", options=["(אין)"] + s_cols, index=0)
        col_city_s = st.selectbox("עיר מגורים", options=s_cols)
        col_pref   = st.selectbox("תחום מועדף (ערך אחד או טקסט)", options=s_cols)
        col_domains= st.selectbox("תחומים מבוקשים (ריבוי ערכים מופרדים בפסיקים/נקודה-פסיק/קו-נטוי)", options=s_cols)

        # קואורדינטות סטודנטים (לא חובה)
        col_s_lat  = st.selectbox("סטודנטים – Latitude (אם קיים)", options=["(אין)"] + s_cols, index=0)
        col_s_lon  = st.selectbox("סטודנטים – Longitude (אם קיים)", options=["(אין)"] + s_cols, index=0)

        st.divider()
        st.subheader("מיפוי שדות – אתרים/מוסדות")
        t_cols = list(site_df.columns)
        col_site  = st.selectbox("שם אתר/מוסד", options=t_cols)
        col_city_t= st.selectbox("עיר אתר/מוסד", options=t_cols)
        col_domain= st.selectbox("תחום ההתמחות", options=t_cols)
        col_cap   = st.selectbox("קיבולת (אם אין – בחרו עמודה לא קיימת ונחשב 1)", options=["(אין)"] + t_cols, index=0)

        # קואורדינטות אתרים (לא חובה)
        col_t_lat = st.selectbox("אתרים – Latitude (אם קיים)", options=["(אין)"] + t_cols, index=0)
        col_t_lon = st.selectbox("אתרים – Longitude (אם קיים)", options=["(אין)"] + t_cols, index=0)

        # שמירה ל-session_state
        st.session_state["map"] = {
            "stu": dict(id=col_id, fname=col_fname, lname=col_lname, fullnm=col_fullnm,
                        city=col_city_s, pref=col_pref, doms=col_domains,
                        lat=col_s_lat, lon=col_s_lon),
            "site": dict(name=col_site, city=col_city_t, domain=col_domain,
                         cap=col_cap, lat=col_t_lat, lon=col_t_lon)
        }
        st.success("המיפוי נשמר. עברו ל'📥 תצוגת נתונים' לבדיקה או ל'🧩 שיבוץ' להרצה.")

# =========================
# תצוגת נתונים
# =========================
with tab_data:
    if (up_students is None) or (up_sites is None) or (stu_df is None) or (site_df is None):
        st.info("העלו קבצים ומפו עמודות בטאבים הקודמים.")
    else:
        cA, cB = st.columns(2)
        with cA:
            st.markdown("**סטודנטים (Raw):**")
            st.dataframe(stu_df, use_container_width=True, height=320)
        with cB:
            st.markdown("**אתרים/מוסדות (Raw):**")
            st.dataframe(site_df, use_container_width=True, height=320)

# =========================
# שיבוץ (כולל מרחק)
# =========================
with tab_match:
    if (up_students is None) or (up_sites is None) or ("map" not in st.session_state):
        st.warning("צריך להעלות קבצים ולבצע מיפוי עמודות בטאב '🗺️ מיפוי עמודות'.", icon="⚠️")
    else:
        M = st.session_state["map"]
        mS, mT = M["stu"], M["site"]

        # --- הכנה: סטודנטים
        stu = stu_df.copy()
        # מזהה
        if mS["id"] == "(ליצור אוטומטית)":
            stu["student_id"] = [f"S{i+1:03d}" for i in range(len(stu))]
        else:
            stu["student_id"] = stu[mS["id"]].astype(str).fillna("").replace("","S-NA").values

        # שם מלא
        if mS["fullnm"] != "(אין)":
            stu["student_name"] = stu[mS["fullnm"]].astype(str).fillna("").str.strip()
        else:
            first = stu[mS["fname"]].astype(str).fillna("") if mS["fname"] != "(אין)" else ""
            last  = stu[mS["lname"]].astype(str).fillna("") if mS["lname"]  != "(אין)" else ""
            if isinstance(first, str) and isinstance(last, str):
                # לא נבחרו עמודות שם – נשתמש ב-id
                stu["student_name"] = stu["student_id"]
            else:
                if isinstance(first, str): first = stu["student_id"].astype(str)
                if isinstance(last, str):  last  = ""
                stu["student_name"] = (first + " " + last).str.strip().replace("", np.nan).fillna(stu["student_id"])

        # שדות חובה
        for req in [mS["city"], mS["pref"], mS["doms"]]:
            if req not in stu.columns:
                st.error(f"עמודת סטודנטים חסרה: {req}")
                st.stop()

        # --- הכנה: אתרים
        site = site_df.copy()
        for req in [mT["name"], mT["city"], mT["domain"]]:
            if req not in site.columns:
                st.error(f"עמודת אתרים חסרה: {req}")
                st.stop()

        if mT["cap"] == "(אין)" or (mT["cap"] not in site.columns):
            site["capacity"] = 1
        else:
            site["capacity"] = pd.to_numeric(site[mT["cap"]], errors="coerce").fillna(1).astype(int).clip(lower=0)
        site = site[site["capacity"] > 0]

        # --- Lat/Lon עמודות (אופציונלי)
        def get_opt_col(df, colname):
            return None if (colname == "(אין)" or (colname not in df.columns)) else colname

        s_lat_col = get_opt_col(stu, mS["lat"]); s_lon_col = get_opt_col(stu, mS["lon"])
        t_lat_col = get_opt_col(site, mT["lat"]); t_lon_col = get_opt_col(site, mT["lon"])

        # --- איחוד תחומים לאתר + עיר לא ריקה
        def union_domains(series) -> str:
            acc = set()
            for v in series.dropna(): acc |= split_multi(v)
            return ", ".join(sorted(acc)) if acc else ""
        def first_non_empty(series) -> str:
            for v in series:
                if _strip(v): return v
            return ""
        sites_agg = site.groupby(mT["name"], as_index=False).agg({
            mT["city"]: first_non_empty,
            mT["domain"]: union_domains
        })
        site_capacity = site.groupby(mT["name"])["capacity"].sum().to_dict()
        site_city_map = pd.Series(sites_agg[mT["city"]].values, index=sites_agg[mT["name"]].astype(str)).to_dict()

        # --- קואורדינטות סטודנטים
        stu_coords = {}
        if s_lat_col and s_lon_col:
            for _, r in stu.iterrows():
                lat = pd.to_numeric(r[s_lat_col], errors="coerce"); lon = pd.to_numeric(r[s_lon_col], errors="coerce")
                stu_coords[r["student_id"]] = (lat if pd.notna(lat) else None, lon if pd.notna(lon) else None)
        elif use_distance and GEOPY_OK:
            cities = sorted(set(_strip(c) for c in stu[mS["city"]].fillna("").astype(str)))
            city2xy = geocode_many(cities, country_hint="ישראל")
            for _, r in stu.iterrows():
                stu_coords[r["student_id"]] = city2xy.get(_strip(r[mS["city"]]), (None, None))
        else:
            for _, r in stu.iterrows(): stu_coords[r["student_id"]] = (None, None)

        # --- קואורדינטות אתרים
        site_coords = {}
        if t_lat_col and t_lon_col:
            for _, r in site.iterrows():
                sname = _strip(r[mT["name"]])
                lat = pd.to_numeric(r[t_lat_col], errors="coerce"); lon = pd.to_numeric(r[t_lon_col], errors="coerce")
                site_coords[sname] = (lat if pd.notna(lat) else None, lon if pd.notna(lon) else None)
        elif use_distance and GEOPY_OK:
            queries = []
            for _, r in sites_agg.iterrows():
                q = _strip(r[mT["name"]]); c = _strip(r[mT["city"]])
                queries.append(f"{q}, {c}" if c else q)
            q2xy = geocode_many(sorted(set(queries)), country_hint="ישראל")
            for _, r in sites_agg.iterrows():
                q = _strip(r[mT["name"]]); c = _strip(r[mT["city"]])
                site_coords[q] = q2xy.get(f"{q}, {c}" if c else q, (None, None))
        else:
            for _, r in sites_agg.iterrows():
                site_coords[_strip(r[mT["name"]])] = (None, None)

        # --- ניקוד בסיס + בונוס מרחק
        def base_match_score(stu_row, site_row):
            score = 0.0
            pref_set = split_multi(stu_row.get(mS["pref"], ""))
            dom_site = split_multi(site_row.get(mT["domain"], "")) or {normalize_text(site_row.get(mT["domain"], ""))}
            if pref_set and dom_site:
                c1 = overlap_count(pref_set, dom_site)
                if c1 > 0: score += W_DOMAIN_MAIN + W_DOMAIN_MULTI * max(0, c1-1)
            all_set = split_multi(stu_row.get(mS["doms"], ""))
            if all_set and dom_site:
                c2 = overlap_count(all_set, dom_site)
                if c2 > 0: score += W_DOMAIN_MULTI * c2
            s_city  = normalize_text(stu_row.get(mS["city"], ""))
            t_city  = normalize_text(site_row.get(mT["city"], ""))
            if s_city and t_city and (s_city == t_city or s_city in t_city or t_city in s_city):
                score += W_CITY
            return score

        def distance_info(stu_id, site_name):
            lat1, lon1 = stu_coords.get(stu_id, (None, None))
            lat2, lon2 = site_coords.get(site_name, (None, None))
            return haversine_km(lat1, lon1, lat2, lon2)

        def distance_bonus(dist_km):
            if (not use_distance) or dist_km is None: return 0.0
            proximity = max(0.0, 1.0 - min(dist_km / max_km, 1.0))
            return w_distance * proximity

        # --- ציונים לכל צמד ---
        rows = []
        for _, srow in stu.iterrows():
            sid = srow["student_id"]; sname = srow["student_name"]
            for _, trow in sites_agg.iterrows():
                site_name = _strip(trow[mT["name"]])
                base = base_match_score(srow, trow)
                dkm = distance_info(sid, site_name)
                # כלל קשיח מרחק
                if hard_limit_on and use_distance and (dkm is None or dkm > max_km):
                    total = -1e9
                else:
                    total = base + distance_bonus(dkm)
                rows.append((sid, sname, site_name, total, _strip(trow.get(mT["city"], "")), None if dkm is None else round(dkm,1)))
        scores = pd.DataFrame(rows, columns=["student_id","student_name","site_name","score","site_city","distance_km"])

        st.markdown("##### Top-3 התאמות לכל סטודנט/ית (כולל עיר ומרחק)")
        top3 = scores.sort_values(["student_id","score"], ascending=[True, False]).groupby("student_id").head(3)
        st.dataframe(top3, use_container_width=True, height=320)

        # --- שיבוץ Greedy ---
        assignments, cap_left = [], site_capacity.copy()
        for sid, grp in scores.groupby("student_id"):
            grp = grp.sort_values("score", ascending=False)
            chosen, chosen_score, sname = "ללא שיבוץ", 0.0, grp.iloc[0]["student_name"]
            chosen_city, chosen_dist = "", None
            for _, r in grp.iterrows():
                if r["score"] < -1e8:  # נפסל בגלל מרחק
                    continue
                site_nm = r["site_name"]
                if cap_left.get(site_nm, 0) > 0:
                    chosen, chosen_score = site_nm, float(r["score"])
                    chosen_city = site_city_map.get(site_nm, _strip(r.get("site_city","")))
                    chosen_dist = r.get("distance_km", None)
                    cap_left[site_nm] -= 1
                    break
            assignments.append({
                "student_id": sid,
                "student_name": sname,
                "assigned_site": chosen,
                "assigned_city": chosen_city,
                "assigned_distance_km": (None if pd.isna(chosen_dist) or chosen_dist is None else float(chosen_dist)),
                "match_score": round(chosen_score, 3),
                "status": "שובץ" if chosen != "ללא שיבוץ" else "ממתין"
            })

        asg = pd.DataFrame(assignments).sort_values("student_id")
        st.success(f"שובצו {(asg['status']=='שובץ').sum()} • ממתינים {(asg['status']=='ממתין').sum()}")
        st.dataframe(asg, use_container_width=True, height=420)

        cA, cB, cC = st.columns(3)
        with cA: st.metric("סה\"כ סטודנטים", len(asg))
        with cB: st.metric("שובצו", int((asg["status"]=="שובץ").sum()))
        with cC: st.metric("ממתינים", int((asg["status"]=="ממתין").sum()))

        st.session_state["assignments_df"] = asg

# =========================
# ייצוא
# =========================
with tab_export:
    st.subheader("הורדה/שמירה")
    if isinstance(st.session_state.get("assignments_df"), pd.DataFrame):
        out = st.session_state["assignments_df"].copy()
        st.dataframe(out, use_container_width=True, height=340)
        fname = f"assignments_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        bio, _ = bytes_for_download(out, fname)
        st.download_button("⬇️ הורדת CSV", bio, file_name=fname, mime="text/csv", use_container_width=True)

        if st.checkbox("שמור גם בשם הקבוע assignments.csv"):
            try:
                out.to_csv("assignments.csv", index=False, encoding="utf-8-sig")
                st.success("נשמר assignments.csv בתיקיית האפליקציה.")
            except Exception as e:
                st.error(f"שגיאת שמירה: {e}")
    else:
        st.info("אין עדיין תוצאות – הריצו שיבוץ בטאב \"🧩 שיבוץ\".")
