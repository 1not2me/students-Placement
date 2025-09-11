
# matcher_streamlit_xlsx_csv.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
from math import radians, sin, cos, asin, sqrt
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any, List

# ================= UI & Styling (per user's style) =================
st.set_page_config(page_title="מערכת שיבוץ סטודנטים – התאמה חכמה", layout="wide")

st.markdown("""
<style>
:root{
  --ink:#0f172a; 
  --muted:#475569; 
  --ring:rgba(99,102,241,.25); 
  --card:rgba(255,255,255,.85);
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

/* מסגרת לטופס */
[data-testid="stForm"]{
  background:var(--card);
  border:1px solid #e2e8f0;
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
[data-testid="stWidgetLabel"] p::after{
  content: " :";
}

/* שדות */
input, textarea, select{ direction:rtl; text-align:right; }
</style>
""", unsafe_allow_html=True)

st.title("🏷️ מערכת שיבוץ סטודנטים – התאמה לפי מרחק, תחום והעדפות")
st.caption("מחשב מרחקים, ניקוד התאמה ושיבוץ מתוך קבצי CSV/XLSX של סטודנטים ואתרי התמחות.")

# ================= Utilities & Config =================

@dataclass
class Weights:
    w_distance: float = 0.7
    w_preferred_field: float = 0.2
    w_special_request: float = 0.1

# Synonyms for columns (Hebrew variations across exports)
STU_COLS = {
    "id": ["מספר תעודת זהות", "תעודת זהות", "ת\"ז", "תז", "תעודת זהות הסטודנט"],
    "first": ["שם פרטי"],
    "last": ["שם משפחה"],
    "address": ["כתובת", "כתובת הסטודנט", "רחוב"],
    "city": ["עיר מגורים", "עיר"],
    "phone": ["טלפון", "מספר טלפון"],
    "email": ["דוא\"ל", "דוא״ל", "אימייל", "כתובת אימייל", "כתובת מייל"],
    "preferred_field": ["תחום מועדף"],
    "special_req": ["בקשה מיוחדת"],
    "mobility": ["ניידות"],
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

def get_val(row: pd.Series, df: pd.DataFrame, synonyms: Dict[str, List[str]], key: str, default: Any = None):
    col = pick_col(df, synonyms.get(key, []))
    return row.get(col, default) if col else default

def build_student_address(row: pd.Series, df: pd.DataFrame) -> str:
    addr = str(get_val(row, df, STU_COLS, "address", "") or "").strip()
    city = str(get_val(row, df, STU_COLS, "city", "") or "").strip()
    if addr and city and city not in addr:
        return f"{addr}, {city}, ישראל"
    if addr:
        return f"{addr}, ישראל"
    if city:
        return f"{city}, ישראל"
    return ""

def build_site_address(row: pd.Series, df: pd.DataFrame) -> str:
    name = str(get_val(row, df, SITE_COLS, "name", "") or "").strip()
    street = str(get_val(row, df, SITE_COLS, "street", "") or "").strip()
    city = str(get_val(row, df, SITE_COLS, "city", "") or "").strip()
    return ", ".join([p for p in [name, street, city, "ישראל"] if p])

def detect_site_type(name: str, field: str) -> str:
    text = f"{name or ''} {field or ''}".replace("־", " ").replace("-", " ").lower()
    rules = [
        ("כלא", "כלא"),
        ("בית סוהר", "כלא"),
        ("בית חולים", "בית חולים"),
        ("מרכז רפואי", "בית חולים"),
        ("מרפאה", "בריאות"),
        ("בי\"ס", "בית ספר"),
        ("בית ספר", "בית ספר"),
        ("תיכון", "בית ספר"),
        ("גן", "גן ילדים"),
        ("מרכז קהילתי", "קהילה"),
        ("רווחה", "רווחה"),
        ("חוסן", "בריאות הנפש"),
        ("בריאות הנפש", "בריאות הנפש"),
    ]
    for key, val in rules:
        if key in text:
            return val
    if "חינוך" in (field or ""):
        return "חינוך"
    return "אחר"

# Haversine distance (km)
def haversine(lat1, lon1, lat2, lon2) -> float:
    if None in (lat1, lon1, lat2, lon2) or any(pd.isna([lat1, lon1, lat2, lon2])):
        return np.nan
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371
    return c * r

# Optional geocoding (online). Lazy init.
_GEOCODER = None
_CACHE: Dict[str, Tuple[Optional[float], Optional[float]]] = {}

def _ensure_geocoder():
    global _GEOCODER
    if _GEOCODER is None:
        try:
            from geopy.geocoders import Nominatim
            from geopy.extra.rate_limiter import RateLimiter
            geolocator = Nominatim(user_agent="student-matcher")
            _GEOCODER = RateLimiter(geolocator.geocode, min_delay_seconds=1)
        except Exception:
            _GEOCODER = None

def geocode(addr: str, allow_online: bool) -> Tuple[Optional[float], Optional[float]]:
    if not isinstance(addr, str) or not addr.strip():
        return (None, None)
    if addr in _CACHE:
        return _CACHE[addr]
    lat, lon = None, None
    if allow_online:
        _ensure_geocoder()
        if _GEOCODER:
            try:
                loc = _GEOCODER(addr)
                if loc:
                    lat, lon = loc.latitude, loc.longitude
            except Exception:
                lat, lon = None, None
    _CACHE[addr] = (lat, lon)
    return lat, lon

def ensure_latlon(df: pd.DataFrame, addr_col: str, prefix: str, allow_online: bool) -> pd.DataFrame:
    lat_col, lon_col = f"{prefix}_lat", f"{prefix}_lon"
    if lat_col in df.columns and lon_col in df.columns:
        return df
    df[lat_col], df[lon_col] = None, None
    for i, row in df.iterrows():
        addr = row.get(addr_col, "")
        lat, lon = geocode(addr, allow_online)
        df.at[i, lat_col] = lat
        df.at[i, lon_col] = lon
    return df

def normalize_distance_score(km: float, max_km: float) -> float:
    if pd.isna(km):
        return 0.0
    if km <= 0:
        return 100.0
    if km >= max_km:
        return 0.0
    return (1 - (km / max_km)) * 100.0

def compute_score(stu: pd.Series, site: pd.Series, km: float, weights: Weights, no_car_km: float) -> float:
    distance_component = normalize_distance_score(km, st.session_state.get("max_km", 50.0))
    # field preference
    stu_pref = str(stu.get("stu_pref", "") or "")
    site_field = str(site.get("site_field", "") or "")
    preferred_component = 100.0 if stu_pref and (stu_pref in site_field) else 0.0
    # special requests
    req = str(stu.get("stu_req", "") or "")
    site_type = str(site.get("site_type", "") or "")
    special_component = 100.0
    if req:
        if "לא בבית חולים" in req and site_type == "בית חולים":
            special_component = 0.0
        if "קרוב" in req and (not pd.isna(km)) and km > no_car_km:
            special_component = 0.0
    # mobility
    mobility = str(stu.get("stu_mobility", "") or "")
    if mobility and ("אין" in mobility or "ללא" in mobility) and (not pd.isna(km)) and km > no_car_km:
        distance_component *= 0.4

    score = (weights.w_distance * distance_component +
             weights.w_preferred_field * preferred_component +
             weights.w_special_request * special_component)
    return max(0.0, min(100.0, float(score)))

def candidate_table_for_student(stu: pd.Series, sites_df: pd.DataFrame, weights: Weights, no_car_km: float) -> pd.DataFrame:
    lat1, lon1 = stu.get("stu_lat"), stu.get("stu_lon")
    tmp = sites_df.copy()
    tmp["distance_km"] = tmp.apply(lambda r: haversine(lat1, lon1, r.get("site_lat"), r.get("site_lon")), axis=1)
    tmp["score"] = tmp.apply(lambda r: compute_score(stu, r, r["distance_km"], weights, no_car_km), axis=1)
    return tmp.sort_values(["score", "distance_km"], ascending=[False, True])

def resolve_students(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Core identity
    out["stu_id"]  = out[pick_col(out, STU_COLS["id"])]
    out["stu_first"] = out[pick_col(out, STU_COLS["first"])]
    out["stu_last"]  = out[pick_col(out, STU_COLS["last"])]
    out["stu_phone"] = out[pick_col(out, STU_COLS["phone"])]
    out["stu_email"] = out[pick_col(out, STU_COLS["email"])]
    out["stu_pref"]  = out[pick_col(out, STU_COLS["preferred_field"])] if pick_col(out, STU_COLS["preferred_field"]) else ""
    out["stu_req"]   = out[pick_col(out, STU_COLS["special_req"])] if pick_col(out, STU_COLS["special_req"]) else ""
    out["stu_mobility"] = out[pick_col(out, STU_COLS["mobility"])] if pick_col(out, STU_COLS["mobility"]) else ""
    out["stu_partner"]  = out[pick_col(out, STU_COLS["partner"])] if pick_col(out, STU_COLS["partner"]) else ""
    # Address
    out["stu_address_full"] = out.apply(lambda r: build_student_address(r, out), axis=1)
    return out

def resolve_sites(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["site_name"]  = out[pick_col(out, SITE_COLS["name"])]
    out["site_field"] = out[pick_col(out, SITE_COLS["field"])]
    out["site_phone"] = out[pick_col(out, SITE_COLS["phone"]) ] if pick_col(out, SITE_COLS["phone"]) else ""
    out["site_email"] = out[pick_col(out, SITE_COLS["email"]) ] if pick_col(out, SITE_COLS["email"]) else ""
    # capacity
    cap_col = pick_col(out, SITE_COLS["capacity"])
    if cap_col is None:
        out["site_capacity"] = 1
    else:
        out["site_capacity"] = pd.to_numeric(out[cap_col], errors="coerce").fillna(1).astype(int)
    out["capacity_left"] = out["site_capacity"].astype(int)
    # Address + type
    out["site_address_full"] = out.apply(lambda r: build_site_address(r, out), axis=1)
    out["site_type"] = out.apply(lambda r: detect_site_type(r.get("site_name"), r.get("site_field")), axis=1)
    # Supervisor name if exists (to separate couples under same mentor if desired)
    sup_first = pick_col(out, SITE_COLS["sup_first"])
    sup_last  = pick_col(out, SITE_COLS["sup_last"])
    out["supervisor"] = ""
    if sup_first or sup_last:
        ff = out[sup_first] if sup_first else ""
        ll = out[sup_last] if sup_last else ""
        out["supervisor"] = (ff.astype(str) + " " + ll.astype(str)).str.strip()
    return out

def find_partner_map(students_df: pd.DataFrame) -> Dict[str, str]:
    ids = set(students_df["stu_id"].astype(str))
    mapping = {}
    for _, r in students_df.iterrows():
        sid = str(r.get("stu_id", ""))
        pid = str(r.get("stu_partner", "") or "").strip()
        if not pid:
            continue
        # direct id
        if pid in ids and pid != sid:
            mapping[sid] = pid
            continue
        # try by full name
        for _, r2 in students_df.iterrows():
            fullname = f"{r2.get('stu_first','')} {r2.get('stu_last','')}".strip()
            if pid and fullname and pid in fullname:
                pid2 = str(r2.get("stu_id", ""))
                if pid2 and pid2 != sid:
                    mapping[sid] = pid2
                    break
    return mapping

def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame, weights: Weights, no_car_km: float,
                 top_k: int, separate_couples: bool) -> pd.DataFrame:

    # Helper to decrement capacity
    def dec_cap(idx: int):
        sites_df.at[idx, "capacity_left"] = int(sites_df.at[idx, "capacity_left"]) - 1

    results = []
    processed: set[str] = set()
    partner_map = find_partner_map(students_df)

    # Couples first (mutual reference)
    for _, s in students_df.iterrows():
        sid = str(s["stu_id"])
        if sid in processed: 
            continue
        pid = partner_map.get(sid)
        if pid and partner_map.get(pid) == sid:
            partner_row = students_df[students_df["stu_id"].astype(str) == pid]
            if partner_row.empty:
                continue
            s2 = partner_row.iloc[0]
            # top candidates for both
            cand1 = candidate_table_for_student(s, sites_df[sites_df["capacity_left"]>0], weights, no_car_km).head(top_k)
            cand2 = candidate_table_for_student(s2, sites_df[sites_df["capacity_left"]>0], weights, no_car_km).head(top_k)
            best = (-1.0, None, None)
            for i1, r1 in cand1.iterrows():
                for i2, r2 in cand2.iterrows():
                    if i1 == i2:  # not same site
                        continue
                    if separate_couples:
                        if r1.get("supervisor") and r1.get("supervisor") == r2.get("supervisor"):
                            continue
                    sc = float(r1["score"]) + float(r2["score"])
                    if sc > best[0]:
                        best = (sc, i1, i2)
            if best[1] is not None and best[2] is not None:
                # assign
                rsite1 = sites_df.loc[best[1]]
                rsite2 = sites_df.loc[best[2]]
                dec_cap(best[1]); dec_cap(best[2])
                results.append((s, rsite1))
                results.append((s2, rsite2))
                processed.add(sid); processed.add(pid)

    # Singles
    for _, s in students_df.iterrows():
        sid = str(s["stu_id"])
        if sid in processed: 
            continue
        cand = candidate_table_for_student(s, sites_df[sites_df["capacity_left"]>0], weights, no_car_km).head(top_k)
        if not cand.empty:
            chosen_idx = cand.index[0]
            rsite = sites_df.loc[chosen_idx]
            dec_cap(chosen_idx)
            results.append((s, rsite))
            processed.add(sid)

    # Build output
    rows = []
    for s, r in results:
        km = haversine(s.get("stu_lat"), s.get("stu_lon"), r.get("site_lat"), r.get("site_lon"))
        score = compute_score(s, r, km, weights, no_car_km)
        rows.append({
            "ת\"ז הסטודנט": s.get("stu_id"),
            "שם פרטי": s.get("stu_first"),
            "שם משפחה": s.get("stu_last"),
            "כתובת": s.get("stu_address_full"),
            "מספר טלפון": s.get("stu_phone"),
            "אימייל": s.get("stu_email"),
            "אחוז התאמה": round(score, 1),
            "מרחק ק\"מ (סטודנט←מוסד)": None if pd.isna(km) else round(float(km), 2),
            "סוג מקום השיבוץ": r.get("site_type"),
            # extras:
            "שם מוסד ההתמחות": r.get("site_name"),
            "תחום ההתמחות במוסד": r.get("site_field"),
        })
    out = pd.DataFrame(rows)
    desired = ["ת\"ז הסטודנט","שם פרטי","שם משפחה","כתובת","מספר טלפון","אימייל","אחוז התאמה","מרחק ק\"מ (סטודנט←מוסד)","סוג מקום השיבוץ",
               "שם מוסד ההתמחות","תחום ההתמחות במוסד"]
    out = out[[c for c in desired if c in out.columns]]
    return out

def read_any(uploaded) -> pd.DataFrame:
    if uploaded is None:
        return None
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded, encoding="utf-8-sig")
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded)
    # fallback try both
    try:
        return pd.read_excel(uploaded)
    except Exception:
        return pd.read_csv(uploaded, encoding="utf-8-sig")

def preprocess_frames(stu_raw: pd.DataFrame, site_raw: pd.DataFrame, allow_geo: bool):
    # Drop Unnamed
    for df in (stu_raw, site_raw):
        drop_cols = [c for c in df.columns if str(c).startswith("Unnamed")]
        df.drop(columns=drop_cols, inplace=True, errors="ignore")
    # Resolve
    students = resolve_students(stu_raw)
    sites = resolve_sites(site_raw)
    # Addresses
    students["stu_address_full"] = students["stu_address_full"].fillna("")
    sites["site_address_full"] = sites["site_address_full"].fillna("")
    # Lat/Lon
    students = ensure_latlon(students, "stu_address_full", "stu", allow_geo)
    sites = ensure_latlon(sites, "site_address_full", "site", allow_geo)
    return students, sites

# ================= Sidebar =================
with st.sidebar:
    st.header("העלאת קבצים והגדרות")
    students_file = st.file_uploader("סטודנטים – CSV/XLSX", type=["csv","xlsx","xls"])
    sites_file = st.file_uploader("אתרי התמחות – CSV/XLSX", type=["csv","xlsx","xls"])
    st.divider()
    allow_geo = st.checkbox("בצע גיאוקוד אונליין (כתובת → קואורדינטות)", value=False)
    max_km = st.slider("טווח מרחק לנרמול (ק\"מ)", 10, 200, 50, step=5)
    st.session_state["max_km"] = float(max_km)
    no_car_km = st.slider("מרחק מקסימלי ללא רכב (ק\"מ)", 2, 50, 12, step=1)
    st.subheader("משקולות ניקוד")
    w_distance = st.slider("משקל מרחק", 0.0, 1.0, 0.7, 0.05)
    w_pref = st.slider("משקל תחום מועדף", 0.0, 1.0, 0.2, 0.05)
    w_req = st.slider("משקל בקשות מיוחדות/מגבלות", 0.0, 1.0, 0.1, 0.05)
    weights = Weights(w_distance, w_pref, w_req)
    st.divider()
    separate_couples = st.checkbox("הפרד בני/בנות זוג (לא אותו מוסד/מדריך)", value=True)
    top_k = st.slider("מספר אתרים לבחינה לכל סטודנט (Top-K)", 3, 25, 10, step=1)
    run_btn = st.button("🚀 הפעל שיבוץ")

# ================= Tabs =================
tab1, tab2 = st.tabs(["📤 העלאת נתונים", "📊 תוצאות השיבוץ"])

with tab1:
    st.subheader("1) העלו את טבלאות המקור (או דוגמאות)")
    st.write("קבצים נתמכים: **CSV, XLSX**. הקוד יזהה עמודות נפוצות אוטומטית (שם פרטי, שם משפחה, ת\"ז, כתובת/עיר, טלפון, דוא\"ל, תחום מועדף, בקשה מיוחדת, ניידות; ובאתרים: מוסד/תחום/רחוב/עיר/קיבולת).")
    st.info("טיפ: להאצת חישוב מרחקים ניתן להוסיף קואורדינטות מוכנות: לסטודנטים `stu_lat, stu_lon` ולאתרים `site_lat, site_lon`.")
    if students_file:
        st.success(f"קובץ סטודנטים נטען: {students_file.name}")
        df_students_raw = read_any(students_file)
        st.dataframe(df_students_raw.head(10), use_container_width=True)
    else:
        st.warning("לא הועלה קובץ סטודנטים.")
        df_students_raw = None

    if sites_file:
        st.success(f"קובץ אתרי התמחות נטען: {sites_file.name}")
        df_sites_raw = read_any(sites_file)
        st.dataframe(df_sites_raw.head(10), use_container_width=True)
    else:
        st.warning("לא הועלה קובץ אתרים.")
        df_sites_raw = None

with tab2:
    st.subheader("2) הרצת שיבוץ והורדת קובץ תוצאה")
    if run_btn:
        if df_students_raw is None or df_sites_raw is None:
            st.error("חסר אחד הקבצים. נא להעלות גם סטודנטים וגם אתרים.")
        else:
            with st.spinner("מחשב מרחקים, ניקוד ושיבוץ..."):
                stu_proc, site_proc = preprocess_frames(df_students_raw.copy(), df_sites_raw.copy(), allow_geo)
                result = greedy_match(stu_proc, site_proc, weights, float(no_car_km), int(top_k), bool(separate_couples))
            st.success("השיבוץ הושלם ✓")
            st.dataframe(result, use_container_width=True)
            csv_data = result.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("⬇️ הורדת קובץ השיבוץ (CSV)",
                               data=csv_data,
                               file_name="student_site_matching.csv",
                               mime="text/csv")
            st.caption("הערה: אם המרחקים ריקים, הפעילו גיאוקוד אונליין או הוסיפו עמודות קואורדינטות לקבצים.")
