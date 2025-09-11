# streamlit_app.py
# ---------------------------------------------------------
# שיבוץ סטודנטים לפי "מי-מתאים-ל":
# 1) student_form_example_5.csv     (סטודנטים)
# 2) example_assignment_result_5.csv (אתרים/מדריכים)
# ניקוד התאמה: תחום (חפיפה/הכלה), עיר (נירמול), מרחק (קירבה), + קיבולת
# כולל מדריך שימוש ועיצוב RTL נקי בסגנון הדוגמה שלך
# ---------------------------------------------------------

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from io import BytesIO
import re, time, math

# ========= ניסיון לייבא geopy (לגיאוקוד). אם אין - נסתדר חלקית =========
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

/* כרטיס יפה */
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
  text-align:right; margin-bottom:.25rem; color:var(--muted);
}
[data-testid="stWidgetLabel"] p::after{ content: " :"; }

/* שדות */
input, textarea, select{ direction:rtl; text-align:right; }

/* KPIs קטנים */
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
# קבועים ושמות קבצים
# =========================
DEFAULT_STUDENTS = Path("./student_form_example_5.csv")
DEFAULT_SITES    = Path("./example_assignment_result_5.csv")
DEFAULT_ASSIGN   = Path("./assignments.csv")
GEOCODE_CACHE    = Path("./geocode_cache.csv")   # קאש כתובות -> קואורדינטות

# =========================
# פונקציות עזר – קריאה/נירמול/פיצול/מרחק
# =========================
def read_csv_flex(path_or_upload):
    if path_or_upload is None: return None
    try:
        return pd.read_csv(path_or_upload)
    except Exception:
        try:
            if hasattr(path_or_upload, "seek"):
                path_or_upload.seek(0)
            return pd.read_csv(path_or_upload, encoding="utf-8-sig")
        except Exception:
            return None

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

def bytes_for_download(df, filename):
    bio = BytesIO()
    df.to_csv(bio, index=False, encoding="utf-8-sig")
    bio.seek(0)
    return bio, filename

# מרחק (Haversine)
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

# גיאוקוד + קאש
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
    """פונקציה ממודרת ל-cache של Streamlit (מעל קאש הקבצים)"""
    if not GEOPY_OK:
        return None
    geolocator = Nominatim(user_agent="student-placement-app")
    time.sleep(1.0)  # נימוס ל-OSM
    try:
        loc = geolocator.geocode(query)
        if loc:
            return (loc.latitude, loc.longitude)
    except Exception:
        return None
    return None

def geocode_many(queries, country_hint="ישראל"):
    """ממפה טקסט -> (lat,lon) עם קאש קבצי + קאש Streamlit."""
    cache = load_geocode_cache()
    out = {}
    for q in queries:
        if not q: 
            out[q] = (None, None)
            continue
        q_norm = f"{q}, {country_hint}" if country_hint and country_hint not in q else q
        if q_norm in cache:
            out[q] = cache[q_norm]
            continue
        res = geocode_query(q_norm)
        if res is None:
            out[q] = (None, None)
        else:
            out[q] = (float(res[0]), float(res[1]))
            cache[q_norm] = out[q]
    save_geocode_cache(cache)
    return out

# =========================
# משקולות ניקוד
# =========================
W_DOMAIN_MAIN  = 2.0   # תחום מועדף ↔ תחום ההתמחות (לפחות התאמה אחת)
W_DOMAIN_MULTI = 1.0   # חפיפה/הכלה לכל ערך נוסף
W_CITY         = 1.2   # עיר (נירמול)
# מרחק: נוסיף משקל לפי קירבה (0..max_km)
DEFAULT_W_DISTANCE = 1.5
DEFAULT_MAX_KM     = 60

# =========================
# Sidebar – העלאות + הגדרות מרחק
# =========================
with st.sidebar:
    st.header("העלאת נתונים")
    st.caption("אם לא תעלי קובץ – נטען את הקבצים הדיפולטיים מהתיקייה.")
    up_students = st.file_uploader("סטודנטים – student_form_example_5.csv", type=["csv"])
    up_sites    = st.file_uploader("אתרים/מדריכים – example_assignment_result_5.csv", type=["csv"])

    st.divider()
    st.subheader("שקלול מרחק")
    use_distance = st.checkbox("להוסיף ניקוד קירבה (מרחק קצר יותר = ציון גבוה יותר)", value=True)
    max_km = st.slider("טווח קירבה מרבי (ק\"מ)", min_value=10, max_value=200, value=DEFAULT_MAX_KM, step=5)
    w_distance = st.slider("משקל המרחק", min_value=0.0, max_value=5.0, value=DEFAULT_W_DISTANCE, step=0.1)

    st.caption("אם קיימות עמודות קואורדינטות – נשתמש בהן. אחרת נבצע גיאוקוד (OSM) עם קאש.")

# קריאה בפועל
students_raw = read_csv_flex(up_students) if up_students else (read_csv_flex(DEFAULT_STUDENTS) if DEFAULT_STUDENTS.exists() else None)
sites_raw    = read_csv_flex(up_sites)    if up_sites    else (read_csv_flex(DEFAULT_SITES)    if DEFAULT_SITES.exists()    else None)

# =========================
# Hero + סטטוס
# =========================
st.markdown(
    """
<div class="hero">
  <h1>📅 שיבוץ סטודנטים – מי-מתאים-ל</h1>
  <p>הציון מחושב על בסיס חפיפה בין <b>תחומי הסטודנט/ית</b> ל<b>תחום ההתמחות באתר</b>, התאמת <b>עיר מגורים</b> ל<b>עיר האתר</b>,
  <b>וקירבה גיאוגרפית</b> (אם הופעל), ולאחר מכן שיבוץ לפי <b>קיבולת</b>.</p>
</div>
""",
    unsafe_allow_html=True
)

c1, c2 = st.columns([1.2, 1])
with c1:
    st.markdown("### שלבי עבודה בקצרה")
    st.markdown("- העלאת שני הקבצים (או טעינה אוטומטית).")
    st.markdown("- בדיקה מהירה של הנתונים בטאב **📥 נתונים**.")
    st.markdown("- **הרצת שיבוץ** בטאב **🧩 שיבוץ**.")
    st.markdown("- **הורדה/שמירה** בטאב **📤 ייצוא**.")
with c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="metric"><span class="label">סטודנטים נטענו</span><span class="value">{0 if students_raw is None else len(students_raw)}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric"><span class="label">רשומות אתרים נטענו</span><span class="value">{0 if sites_raw is None else len(sites_raw)}</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# =========================
# Tabs
# =========================
tab_guide, tab_data, tab_match, tab_export = st.tabs(["📖 מדריך", "📥 נתונים", "🧩 שיבוץ", "📤 ייצוא"])

# =========================
# לשונית מדריך
# =========================
with tab_guide:
    st.subheader("מדריך מלא לשימוש באתר")
    st.markdown(f"""
**מטרה**  
שיבוץ אוטומטי של סטודנטים/ות למוסדות הכשרה לפי התאמה של **תחום**, **עיר**, **מרחק** (אופציונלי) ובכפוף **לקיבולת**.

### 1) הקבצים הדרושים
- **student_form_example_5.csv** – שדות נדרשים: `שם פרטי`, `שם משפחה`, `עיר מגורים`, `תחומים מבוקשים`, `תחום מועדף`.
- **example_assignment_result_5.csv** – שדות נדרשים: `מוסד / שירות הכשרה` (שם האתר), `תחום ההתמחות`, `עיר`, `מספר סטודנטים שניתן לקלוט השנה`.

### 2) שקלול מרחק
- אם קיימות עמודות קואורדינטות (Lat/Lon) לסטודנטים/אתרים – המערכת תזהה אותן ותחשב מרחק ישירות.  
- אם אין – נשתמש בגיאוקוד (OpenStreetMap) לפי **עיר**/כתובת. יש קאש כדי לא לחזור על פניות.  
- הנוסחה:  
  `distance_score = w_distance * (1 - min(distance_km / max_km, 1))`  
  כלומר עד {DEFAULT_MAX_KM} ק״מ תקבלי קרדיט, ומעבר לכך – 0.

### 3) איך מחושב הציון הכולל?
1. **תחום מועדף** ↔ **תחום ההתמחות**: בסיס {W_DOMAIN_MAIN} + {W_DOMAIN_MULTI} לכל ערך תואם נוסף (כולל הכלה).  
2. **תחומים מבוקשים** ↔ **תחום ההתמחות**: {W_DOMAIN_MULTI} לכל חפיפה.  
3. **עיר מגורים** ↔ **עיר האתר**: {W_CITY} (עם נירמול/הכלה).  
4. **מרחק** (אם הופעל): `{DEFAULT_W_DISTANCE}` כברירת מחדל, יורד לינארית עד {DEFAULT_MAX_KM} ק״מ.

### 4) שיבוץ
לאחר חישוב ציונים לכל צמד סטודנט–אתר, מופעל **Greedy**: לכל סטודנט/ית נבחר האתר עם הציון הגבוה ביותר שעוד נותר בו מקום.

### 5) תוצאות
- בטבלת התוצאות תמצאו: `student_id`, `student_name`, `assigned_site`, **`assigned_city`**, **`assigned_distance_km`**, `match_score`, `status`.  
- ניתן להוריד CSV או לשמור בשם הקבוע `assignments.csv`.

### 6) תקלות נפוצות
- ציון 0 לכל הצמדים → בדקו שדות תחום/עיר שאינם ריקים.  
- מרחק None → כתובת לא זוהתה בגיאוקוד; אפשר להוסיף עמודות Lat/Lon כדי לעקוף את זה.  
- קיבולת נמוכה → הגדלת `מספר סטודנטים שניתן לקלוט השנה` בקובץ האתרים.
""")

# =========================
# לשונית נתונים
# =========================
with tab_data:
    st.info("המערכת משתמשת בעמודות: סטודנטים → `שם פרטי`, `שם משפחה`, `עיר מגורים`, `תחומים מבוקשים`, `תחום מועדף` • אתרים → `מוסד / שירות הכשרה`, `תחום ההתמחות`, `עיר`, `מספר סטודנטים שניתן לקלוט השנה`", icon="ℹ️")
    if students_raw is None or sites_raw is None:
        st.warning("יש להעלות/לספק את שני הקבצים.", icon="⚠️")
    else:
        cA, cB = st.columns(2)
        with cA:
            with st.expander("סטודנטים – Raw", expanded=False):
                st.dataframe(students_raw, use_container_width=True, height=320)
        with cB:
            with st.expander("אתרים/מדריכים – Raw", expanded=False):
                st.dataframe(sites_raw, use_container_width=True, height=320)

# =========================
# לשונית שיבוץ (כולל מרחק)
# =========================
with tab_match:
    if students_raw is None or sites_raw is None:
        st.warning("חסרים נתונים. העלי את שני הקבצים בטאב הראשון.", icon="⚠️")
    else:
        # שמות עמודות לפי הטפסים
        STU_FIRST   = "שם פרטי"
        STU_LAST    = "שם משפחה"
        STU_CITY    = "עיר מגורים"
        STU_DOMS    = "תחומים מבוקשים"
        STU_PREFDOM = "תחום מועדף"

        SITE_NAME   = "מוסד / שירות הכשרה"
        SITE_CITY   = "עיר"
        SITE_DOMAIN = "תחום ההתמחות"
        SITE_CAP    = "מספר סטודנטים שניתן לקלוט השנה"

        # בדיקת קיום עמודות
        missing = []
        for req in [STU_FIRST, STU_LAST, STU_CITY, STU_DOMS, STU_PREFDOM]:
            if req not in students_raw.columns: missing.append(f"סטודנטים: {req}")
        for req in [SITE_NAME, SITE_CITY, SITE_DOMAIN, SITE_CAP]:
            if req not in sites_raw.columns: missing.append(f"אתרים: {req}")
        if missing:
            st.error("עמודות חסרות: " + " | ".join(missing))
            st.stop()

        # ===== הכנה: סטודנטים =====
        stu = students_raw.copy()
        stu["student_id"] = [f"S{i+1:03d}" for i in range(len(stu))]
        stu["student_name"] = (stu[STU_FIRST].astype(str).fillna("") + " " + stu[STU_LAST].astype(str).fillna("")).str.strip()

        # איתור קואורדינטות אם קיימות
        def detect_latlon_cols(df):
            lat = next((c for c in df.columns if c.lower() in ["lat","latitude","קו רוחב","רוחב"]), None)
            lon = next((c for c in df.columns if c.lower() in ["lon","lng","longitude","קו אורך","אורך"]), None)
            return lat, lon

        stu_lat_col, stu_lon_col = detect_latlon_cols(stu)

        # ===== הכנה: אתרים – קיבולת + אגרגציה =====
        site = sites_raw.copy()
        site["capacity"] = pd.to_numeric(site[SITE_CAP], errors="coerce").fillna(1).astype(int).clip(lower=0)
        site = site[site["capacity"] > 0]

        # קואורדינטות לאתרים אם קיימות
        site_lat_col, site_lon_col = detect_latlon_cols(site)

        def union_domains(series) -> str:
            acc = set()
            for v in series.dropna():
                acc |= split_multi(v)
            return ", ".join(sorted(acc)) if acc else ""

        def first_non_empty(series) -> str:
            for v in series:
                if _strip(v): 
                    return v
            return ""

        sites_agg = site.groupby(SITE_NAME, as_index=False).agg({
            SITE_CITY: first_non_empty,
            SITE_DOMAIN: union_domains
        })
        # קיבולת לכל אתר כסכום
        site_capacity = site.groupby(SITE_NAME)["capacity"].sum().to_dict()
        site_city_map = pd.Series(sites_agg[SITE_CITY].values, index=sites_agg[SITE_NAME].astype(str)).to_dict()

        # ===== קואורדינטות (גיאוקוד אם צריך) =====
        # סטודנטים: לפי עיר (אם אין Lat/Lon)
        stu_coords = {}
        if stu_lat_col and stu_lon_col:
            for _, r in stu.iterrows():
                stu_coords[r["student_id"]] = (pd.to_numeric(r[stu_lat_col], errors="coerce"), pd.to_numeric(r[stu_lon_col], errors="coerce"))
        elif use_distance:
            if not GEOPY_OK:
                st.warning("לא נמצא geopy – מרחק יחושב רק אם יש Lat/Lon בקבצים.", icon="⚠️")
            else:
                unique_cities = sorted(set(_strip(c) for c in stu[STU_CITY].fillna("").astype(str)))
                city_to_xy = geocode_many(unique_cities, country_hint="ישראל")
                for _, r in stu.iterrows():
                    city = _strip(r[STU_CITY])
                    lat, lon = city_to_xy.get(city, (None, None))
                    stu_coords[r["student_id"]] = (lat, lon)
        else:
            for _, r in stu.iterrows():
                stu_coords[r["student_id"]] = (None, None)

        # אתרים: לפי Lat/Lon אם יש, אחרת לפי עיר/שם
        site_coords = {}
        if site_lat_col and site_lon_col:
            for _, r in site.iterrows():
                site_coords[_strip(r[SITE_NAME])] = (pd.to_numeric(r[site_lat_col], errors="coerce"), pd.to_numeric(r[site_lon_col], errors="coerce"))
        elif use_distance and GEOPY_OK:
            unique_queries = []
            for _, r in sites_agg.iterrows():
                q = _strip(r[SITE_NAME])
                city = _strip(r[SITE_CITY])
                query = f"{q}, {city}" if city else q
                unique_queries.append(query)
            q_to_xy = geocode_many(sorted(set(unique_queries)), country_hint="ישראל")
            for _, r in sites_agg.iterrows():
                q = _strip(r[SITE_NAME]); city = _strip(r[SITE_CITY])
                lat, lon = q_to_xy.get(f"{q}, {city}" if city else q, (None, None))
                site_coords[q] = (lat, lon)
        else:
            for _, r in sites_agg.iterrows():
                site_coords[_strip(r[SITE_NAME])] = (None, None)

        # ===== ניקוד התאמה + מרחק =====
        def base_match_score(stu_row, site_row):
            score = 0.0
            pref_set    = split_multi(stu_row.get(STU_PREFDOM, ""))
            dom_site    = split_multi(site_row.get(SITE_DOMAIN, "")) or {normalize_text(site_row.get(SITE_DOMAIN, ""))}

            # 1) תחום מועדף
            if pref_set and dom_site:
                c1 = overlap_count(pref_set, dom_site)
                if c1 > 0:
                    score += W_DOMAIN_MAIN + W_DOMAIN_MULTI * max(0, c1-1)
            # 2) תחומים מבוקשים
            all_set = split_multi(stu_row.get(STU_DOMS, ""))
            if all_set and dom_site:
                c2 = overlap_count(all_set, dom_site)
                if c2 > 0:
                    score += W_DOMAIN_MULTI * c2
            # 3) עיר
            stu_city  = normalize_text(stu_row.get(STU_CITY, ""))
            site_city = normalize_text(site_row.get(SITE_CITY, ""))
            if stu_city and site_city and (stu_city == site_city or stu_city in site_city or site_city in stu_city):
                score += W_CITY
            return score

        def distance_bonus(stu_id, site_name):
            if not use_distance: 
                return 0.0, None
            lat1, lon1 = stu_coords.get(stu_id, (None, None))
            lat2, lon2 = site_coords.get(site_name, (None, None))
            d = haversine_km(lat1, lon1, lat2, lon2)
            if d is None:
                return 0.0, None
            proximity = max(0.0, 1.0 - min(d / max_km, 1.0))
            return w_distance * proximity, float(d)

        # ----- טבלת ציונים לכל צמד -----
        rows = []
        for _, s in stu.iterrows():
            sid = s["student_id"]; sname = s["student_name"]
            for _, t in sites_agg.iterrows():
                site_name = _strip(t.get(SITE_NAME, ""))
                base = base_match_score(s, t)
                dist_add, dist_km = distance_bonus(sid, site_name)
                rows.append((sid, sname, site_name, base + dist_add, _strip(t.get(SITE_CITY, "")), dist_km))
        scores = pd.DataFrame(rows, columns=["student_id","student_name","site_name","score","site_city","distance_km"])

        # דיאגנוסטיקה: TOP-3 לכל סטודנט (כולל עיר + מרחק)
        st.markdown("##### Top-3 התאמות לכל סטודנט/ית (כולל עיר האתר ומרחק משוער)")
        top3 = scores.sort_values(["student_id","score"], ascending=[True, False]).groupby("student_id").head(3)
        st.dataframe(top3, use_container_width=True, height=320)

        # ===== שיבוץ Greedy עם קיבולת =====
        assignments, cap_left = [], site_capacity.copy()
        for sid, grp in scores.groupby("student_id"):
            grp = grp.sort_values("score", ascending=False)
            chosen, chosen_score, sname = "ללא שיבוץ", 0.0, grp.iloc[0]["student_name"]
            chosen_city, chosen_dist = "", None
            for _, r in grp.iterrows():
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
                "assigned_distance_km": (None if pd.isna(chosen_dist) or chosen_dist is None else round(float(chosen_dist), 1)),
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
# לשונית ייצוא
# =========================
with tab_export:
    st.subheader("הורדה/שמירה")
    if isinstance(st.session_state.get("assignments_df"), pd.DataFrame):
        out = st.session_state["assignments_df"].copy()
        st.dataframe(out, use_container_width=True, height=340)

        fname = f"assignments_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        bio = BytesIO(); out.to_csv(bio, index=False, encoding="utf-8-sig"); bio.seek(0)
        st.download_button("⬇️ הורדת CSV", bio, file_name=fname, mime="text/csv", use_container_width=True)

        if st.checkbox("שמור גם בשם הקבוע assignments.csv"):
            try:
                out.to_csv(DEFAULT_ASSIGN, index=False, encoding="utf-8-sig")
                st.success("נשמר assignments.csv בתיקיית האפליקציה.")
            except Exception as e:
                st.error(f"שגיאת שמירה: {e}")
    else:
        st.info("אין עדיין תוצאות – הריצי שיבוץ בטאב \"🧩 שיבוץ\".")
