
# streamlit_app.py (Auto-match, no manual mapping/choices)
import streamlit as st
import pandas as pd
import numpy as np
from math import radians, sin, cos, atan2, sqrt
from pathlib import Path

# =========================
# General + Modern Styling
# =========================
st.set_page_config(page_title="מערכת שיבוץ סטודנטים – אוטומטי", layout="wide")

st.markdown(r"""
<style>
:root{
  --ink:#0f172a;
  --muted:#64748b;
  --ring:rgba(56,189,248,.25);
  --card:rgba(255,255,255,.90);
  --grad1:#e0f2fe; /* blue-100 */
  --grad2:#f1f5f9; /* slate-100 */
  --grad3:#fae8ff; /* fuchsia-100 */
}

/* RTL + clean typography */
html, body, [class*="css"] { font-family: "Segoe UI", system-ui, -apple-system, Arial; }
.stApp, .main, [data-testid="stSidebar"]{ direction:rtl; text-align:right; }

/* background */
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 8% 8%, var(--grad1) 0%, transparent 65%),
    radial-gradient(1000px 500px at 92% 12%, var(--grad3) 0%, transparent 60%),
    radial-gradient(900px 500px at 20% 90%, var(--grad2) 0%, transparent 55%);
}
.block-container{ padding-top:1.2rem; }

/* card */
.section{
  background:var(--card);
  border:1px solid #e2e8f0;
  border-radius:18px;
  padding:18px 20px;
  box-shadow:0 10px 28px rgba(2,6,23,.06);
  margin-bottom:18px;
}

/* tables */
[data-baseweb="table"]{ border-radius:14px; overflow:hidden; }
thead th { background:#f8fafc !important; color:#0f172a !important; }

/* labels */
small.hint{ color:var(--muted); }
hr.sep{ border:none; border-top:1px solid #e2e8f0; margin:14px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="section">', unsafe_allow_html=True)
st.title("🧭 מערכת שיבוץ סטודנטים – אוטומטי")
st.caption("שיבוץ מלא ללא בחירות ידניות – לפי נתוני הסטודנטים והאתרים, עם הפרדת בני/בנות זוג, כיבוד קיבולות וחישוב מרחק (אם קיימות קואורדינטות).")
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# Constants & defaults
# =========================
DEFAULT_STUDENTS = "/mnt/data/2025-09-11T17-20_export.csv"
DEFAULT_SITES    = "/mnt/data/2025-09-11T17-21_export.csv"

W_DISTANCE = 0.85         # weight for distance in score (0..1)
SEP_PARTNERS = True       # separate couples across site/supervisor
ENFORCE_CAPACITY = True   # respect capacity

# =========================
# Helpers
# =========================
def haversine_km(lat1, lon1, lat2, lon2):
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return np.nan
    R = 6371.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2.0)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2.0)**2
    c = 2 * atan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

def normalize_series(s: pd.Series):
    s = pd.to_numeric(s, errors="coerce")
    if s.max(skipna=True) == s.min(skipna=True):
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.min(skipna=True)) / (s.max(skipna=True) - s.min(skipna=True))

def guess_column(cols, patterns):
    cl = {c: c.lower() for c in cols}
    for p in patterns:
        for c, lc in cl.items():
            if p in lc:
                return c
    return None

def load_csv_auto():
    """Load students & sites automatically from default paths if exist, otherwise try to read uploads silently."""
    stud_df = None
    site_df = None
    if Path(DEFAULT_STUDENTS).exists():
        stud_df = pd.read_csv(DEFAULT_STUDENTS)
    if Path(DEFAULT_SITES).exists():
        site_df = pd.read_csv(DEFAULT_SITES)
    return stud_df, site_df

# =========================
# Load data (no choices)
# =========================
stud_df, site_df = load_csv_auto()

# As a fallback, allow drag&drop without extra UI noise
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.subheader("📥 קובץ סטודנטים (CSV)")
    if stud_df is None:
        f = st.file_uploader("ניתן לגרור לכאן את קובץ הסטודנטים", type=["csv"], key="stud")
        if f is not None:
            stud_df = pd.read_csv(f)
    else:
        st.success("נטען אוטומטית מקובץ ברירת המחדל.")
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown('<div class="section">', unsafe_allow_html=True)
    st.subheader("🏥 קובץ אתרי שיבוץ (CSV)")
    if site_df is None:
        f = st.file_uploader("ניתן לגרור לכאן את קובץ האתרים", type=["csv"], key="site")
        if f is not None:
            site_df = pd.read_csv(f)
    else:
        st.success("נטען אוטומטית מקובץ ברירת המחדל.")
    st.markdown('</div>', unsafe_allow_html=True)

if stud_df is None or site_df is None:
    st.error("חסר קובץ אחד לפחות. ודאי שהקבצים קיימים בנתיב ברירת מחדל או גררי אותם לכאן.")
    st.stop()

# =========================
# Column detection (no manual mapping)
# =========================
stud_cols = list(stud_df.columns)
site_cols = list(site_df.columns)

# Students
stud_id_col  = guess_column(stud_cols, ["id", "תז", "ת.ז", "זהות", "student id"])
first_col    = guess_column(stud_cols, ["first", "שם פרטי", "פרטי"])
last_col     = guess_column(stud_cols, ["last", "family", "שם משפ", "משפחה"])
city_col     = guess_column(stud_cols, ["city", "יישוב", "עיר", "מגורים"])
phone_col    = guess_column(stud_cols, ["phone", "טל", "נייד"])
mail_col     = guess_column(stud_cols, ["mail", "email", "אימייל", "דוא", "דוא\"ל"])
s_lat_col    = guess_column(stud_cols, ["lat", "latitude", "קו רוחב"])
s_lon_col    = guess_column(stud_cols, ["lon", "lng", "longitude", "קו אורך"])
partner_col  = guess_column(stud_cols, ["partner", "בן זוג", "בת זוג", "זוגיות", "couple", "spouse"])
reason_col   = guess_column(stud_cols, ["reason", "סיבה", "בקשה", "התחשבות", "עדיפות"])

# Sites
site_name_col = guess_column(site_cols, ["שם אתר", "שם מקום", "site", "מקום", "ארגון"])
site_city_col = guess_column(site_cols, ["city", "יישוב", "עיר", "מיקום"])
site_zip_col  = guess_column(site_cols, ["zip", "מיקוד"])
site_type_col = guess_column(site_cols, ["type", "סוג", "קטגוריה"])
site_sup_col  = guess_column(site_cols, ["supervisor", "מדריך", "רכז", "מנחה"])
site_cap_col  = guess_column(site_cols, ["capacity", "קיבולת", "מכסה", "מקומות"])
t_lat_col     = guess_column(site_cols, ["lat", "latitude", "קו רוחב"])
t_lon_col     = guess_column(site_cols, ["lon", "lng", "longitude", "קו אורך"])

required = [stud_id_col, first_col, last_col, city_col, phone_col, mail_col, site_name_col, site_city_col]
if any(c is None for c in required):
    st.error("איתור עמודות נכשל עבור חלק מהשדות החיוניים. ודאי ששמות העמודות בקבצים ברורים (ת\"ז, שם פרטי, שם משפחה, עיר/יישוב, טלפון, אימייל; אתר: שם אתר, עיר).")
    st.stop()

# =========================
# Prepare normalized frames
# =========================
S = pd.DataFrame({
    "student_id": stud_df[stud_id_col],
    "first_name": stud_df[first_col],
    "last_name":  stud_df[last_col],
    "home_city":  stud_df[city_col],
    "phone":      stud_df[phone_col],
    "email":      stud_df[mail_col],
})
S["s_lat"] = pd.to_numeric(stud_df[s_lat_col], errors="coerce") if s_lat_col else np.nan
S["s_lon"] = pd.to_numeric(stud_df[s_lon_col], errors="coerce") if s_lon_col else np.nan
S["partner_id"] = stud_df[partner_col] if partner_col else ""
S["reason"] = stud_df[reason_col].astype(str) if reason_col else ""

T = pd.DataFrame({
    "site_name": site_df[site_name_col],
    "site_city": site_df[site_city_col],
})
T["zip"]   = site_df[site_zip_col] if site_zip_col else ""
T["sitetype"] = site_df[site_type_col] if site_type_col else ""
T["supervisor"] = site_df[site_sup_col] if site_sup_col else ""
T["capacity"] = pd.to_numeric(site_df[site_cap_col], errors="coerce").fillna(1).astype(int) if site_cap_col else 9999
T["t_lat"] = pd.to_numeric(site_df[t_lat_col], errors="coerce") if t_lat_col else np.nan
T["t_lon"] = pd.to_numeric(site_df[t_lon_col], errors="coerce") if t_lon_col else np.nan

S.fillna({"partner_id":"", "reason":""}, inplace=True)
T.fillna({"zip":"", "sitetype":"", "supervisor":"", "capacity":1}, inplace=True)

# =========================
# Distance matrix & score
# =========================
dist_matrix = pd.DataFrame(index=S.index, columns=T.index, dtype=float)
if S[["s_lat","s_lon"]].notna().all(axis=None) and T[["t_lat","t_lon"]].notna().all(axis=None):
    for i in S.index:
        for j in T.index:
            dist_matrix.loc[i, j] = haversine_km(S.loc[i,"s_lat"], S.loc[i,"s_lon"], T.loc[j,"t_lat"], T.loc[j,"t_lon"])
else:
    dist_matrix[:] = np.nan

norm_dist = dist_matrix.apply(normalize_series, axis=1)
score = pd.DataFrame(0.0, index=S.index, columns=T.index)
if norm_dist.notna().any().any():
    score = W_DISTANCE * (1 - norm_dist.fillna(norm_dist.max().fillna(1)))

# =========================
# Greedy assignment (auto)
# =========================
assignments = []
site_slots = T["capacity"].copy() if ENFORCE_CAPACITY else pd.Series([999999]*len(T), index=T.index)
preferred_sites = score.apply(lambda row: list(row.sort_values(ascending=False).index), axis=1)
assigned_site_idx = {}

for i in S.index:
    for site_idx in preferred_sites[i]:
        if site_slots[site_idx] <= 0:
            continue
        if SEP_PARTNERS and S.loc[i, "partner_id"]:
            partner_mask = (S["student_id"].astype(str) == str(S.loc[i, "partner_id"])) | \
                           (S["partner_id"].astype(str) == str(S.loc[i, "student_id"]))
            partner_indices = S.index[partner_mask].tolist()
            conflict = False
            for pi in partner_indices:
                if pi in assigned_site_idx:
                    other_site = assigned_site_idx[pi]
                    if other_site == site_idx:
                        conflict = True; break
                    if (T.loc[other_site, "supervisor"] and T.loc[site_idx, "supervisor"] and
                        T.loc[other_site, "supervisor"] == T.loc[site_idx, "supervisor"]):
                        conflict = True; break
            if conflict:
                continue
        assigned_site_idx[i] = site_idx
        site_slots[site_idx] -= 1
        break

# =========================
# Output
# =========================
rows = []
for i, site_idx in assigned_site_idx.items():
    s = S.loc[i]; t = T.loc[site_idx]
    d_km = np.nan
    if not np.isnan(s["s_lat"]) and not np.isnan(s["s_lon"]) and not np.isnan(t["t_lat"]) and not np.isnan(t["t_lon"]):
        d_km = haversine_km(s["s_lat"], s["s_lon"], t["t_lat"], t["t_lon"])
    pct = 0.0
    sc = score.loc[i, site_idx] if site_idx in score.columns else np.nan
    if pd.notna(sc):
        pct = float(np.clip(sc, 0, 1) * 100.0)

    rows.append({
        "ת\"ז הסטודנט": s["student_id"],
        "שם פרטי": s["first_name"],
        "שם משפחה": s["last_name"],
        "מקום מגורים": s["home_city"],
        "מספר טלפון": s["phone"],
        "אימייל": s["email"],
        "שם מקום השיבוץ": t["site_name"],
        "מיקום (עיר) השיבוץ": t["site_city"],
        "מיקוד": t["zip"],
        "אחוז התאמה (%)": round(pct, 1),
        "מרחק (ק\"מ)": round(d_km, 2) if pd.notna(d_km) else "",
        "סוג מקום השיבוץ": t["sitetype"],
    })

result_df = pd.DataFrame(rows)

st.markdown('<div class="section">', unsafe_allow_html=True)
st.subheader("📊 תוצאת השיבוץ (אוטומטי)")
st.dataframe(result_df, use_container_width=True)
csv_data = result_df.to_csv(index=False).encode("utf-8-sig")
st.download_button("⬇️ הורדת קובץ השיבוץ (CSV)", data=csv_data, file_name="שיבוץ_סטודנטים.csv", mime="text/csv")
st.markdown('</div>', unsafe_allow_html=True)

# Diagnostics (what columns were auto-detected)
with st.expander("ℹ️ עמודות שאותרו אוטומטית"):
    det = {
        "ת\"ז סטודנט": stud_id_col, "שם פרטי": first_col, "שם משפחה": last_col, "עיר מגורים": city_col,
        "טלפון": phone_col, "אימייל": mail_col, "סטודנט lat": s_lat_col, "סטודנט lon": s_lon_col,
        "מזהה בן/בת זוג": partner_col, "סיבת התחשבות": reason_col,
        "שם אתר": site_name_col, "עיר אתר": site_city_col, "מיקוד": site_zip_col,
        "סוג אתר": site_type_col, "מדריך": site_sup_col, "קיבולת": site_cap_col,
        "אתר lat": t_lat_col, "אתר lon": t_lon_col,
    }
    st.write(pd.DataFrame(det, index=["עמודה שנמצאה"]).T)
