# streamlit_app.py
import streamlit as st
import pandas as pd
import numpy as np
from math import radians, sin, cos, atan2, sqrt
from pathlib import Path

# =========================
# הגדרות כלליות + עיצוב
# =========================
st.set_page_config(page_title="מנגנון שיבוץ סטודנטים", layout="wide")

st.markdown(r"""
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

/* כרטיס/טופס */
[data-testid="stForm"], .st-emotion-cache-ue6h4q, .st-emotion-cache-0{
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

st.title("🧭 מנגנון שיבוץ סטודנטים להתמחויות")
st.caption("שיבוץ אוטומטי המתחשב במרחק, קיבולת, והפרדה בין בני/ות זוג (לא אותו מדריך/אתר).")

# =========================
# עזר: פונקציות
# =========================
def haversine_km(lat1, lon1, lat2, lon2):
    """מרחק קו אווירי בק\"מ בין שתי נקודות (lat/lon)"""
    if pd.isna(lat1) or pd.isna(lon1) or pd.isna(lat2) or pd.isna(lon2):
        return np.nan
    R = 6371.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi/2.0)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2.0)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def normalize_series(s: pd.Series):
    s = s.astype(float)
    if s.max(skipna=True) == s.min(skipna=True):
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - s.min(skipna=True)) / (s.max(skipna=True) - s.min(skipna=True))

def guess_column(cols, patterns):
    """ניחוש שם עמודה לפי רשימת תבניות (lower)"""
    cl = {c: c.lower() for c in cols}
    for p in patterns:
        for c, lc in cl.items():
            if p in lc:
                return c
    return None

# =========================
# טעינת קבצים
# =========================
LEFT, RIGHT = st.columns([1,1])

DEFAULT_STUDENTS = "/mnt/data/2025-09-11T17-20_export.csv"
DEFAULT_SITES    = "/mnt/data/2025-09-11T17-21_export.csv"

with LEFT:
    st.subheader("📥 קובץ הסטודנטים")
    use_defaults = st.checkbox("להשתמש בקבצים כברירת מחדל (אם קיימים בשרת)", value=True)
    stud_file = st.file_uploader("בחרי CSV של סטודנטים", type=["csv"], key="stud_csv")
    if use_defaults and stud_file is None and Path(DEFAULT_STUDENTS).exists():
        st.info("נטען קובץ הסטודנטים מברירת המחדל.")
        stud_df = pd.read_csv(DEFAULT_STUDENTS)
    elif stud_file is not None:
        stud_df = pd.read_csv(stud_file)
    else:
        stud_df = None

with RIGHT:
    st.subheader("🏥 קובץ אתרי השיבוץ")
    site_file = st.file_uploader("בחרי CSV של אתרי שיבוץ", type=["csv"], key="site_csv")
    if use_defaults and site_file is None and Path(DEFAULT_SITES).exists():
        st.info("נטען קובץ האתרים מברירת המחדל.")
        site_df = pd.read_csv(DEFAULT_SITES)
    elif site_file is not None:
        site_df = pd.read_csv(site_file)
    else:
        site_df = None

if stud_df is None or site_df is None:
    st.warning("יש להעלות שני קבצים (סטודנטים + אתרים) או להפעיל ברירת מחדל אם זמינה.")
    st.stop()

st.success("הקבצים נטענו בהצלחה.")

with st.expander("📄 הצצה לנתונים (5 שורות ראשונות)"):
    st.write("סטודנטים")
    st.dataframe(stud_df.head())
    st.write("אתרים")
    st.dataframe(site_df.head())

# =========================
# מיפוי עמודות (כדי להתאים לשמות שלכם)
# =========================
st.subheader("🧩 מיפוי עמודות")

stud_cols = list(stud_df.columns)
site_cols = list(site_df.columns)

# ניחושים לשמות
stud_id_guess  = guess_column(stud_cols, ["id", "תז", "ת.ז", "זהות"])
first_guess    = guess_column(stud_cols, ["first", "שם פרטי", "פרטי"])
last_guess     = guess_column(stud_cols, ["last", "family", "שם משפ", "משפחה"])
city_guess     = guess_column(stud_cols, ["city", "יישוב", "עיר", "מגורים"])
phone_guess    = guess_column(stud_cols, ["phone", "טל", "נייד"])
mail_guess     = guess_column(stud_cols, ["mail", "email", "אימייל", "דוא", "דוא\"ל"])
lat_guess      = guess_column(stud_cols, ["lat", "latitude", "קו רוחב"])
lon_guess      = guess_column(stud_cols, ["lon", "lng", "longitude", "קו אורך"])
partner_guess  = guess_column(stud_cols, ["partner", "בן זוג", "בת זוג", "זוגיות", "couple"])
reason_guess   = guess_column(stud_cols, ["reason", "סיבה", "בקשה", "התחשבות"])

site_name_guess = guess_column(site_cols, ["שם אתר", "שם מקום", "site", "מקום", "ארגון"])
site_city_guess = guess_column(site_cols, ["city", "יישוב", "עיר", "מיקום"])
site_zip_guess  = guess_column(site_cols, ["zip", "מיקוד"])
site_type_guess = guess_column(site_cols, ["type", "סוג", "קטגוריה"])
site_sup_guess  = guess_column(site_cols, ["supervisor", "מדריך", "רכז", "מנחה"])
site_cap_guess  = guess_column(site_cols, ["capacity", "קיבולת", "מכסה", "מקומות"])
site_lat_guess  = guess_column(site_cols, ["lat", "latitude", "קו רוחב"])
site_lon_guess  = guess_column(site_cols, ["lon", "lng", "longitude", "קו אורך"])

with st.form("mapping"):
    m1, m2, m3 = st.columns(3)
    with m1:
        stud_id_col  = st.selectbox("ת\"ז סטודנט", stud_cols, index=stud_cols.index(stud_id_guess) if stud_id_guess in stud_cols else 0)
        first_col    = st.selectbox("שם פרטי", stud_cols, index=stud_cols.index(first_guess) if first_guess in stud_cols else 0)
        last_col     = st.selectbox("שם משפחה", stud_cols, index=stud_cols.index(last_guess) if last_guess in stud_cols else 0)
        city_col     = st.selectbox("מקום מגורים (עיר/יישוב)", stud_cols, index=stud_cols.index(city_guess) if city_guess in stud_cols else 0)
    with m2:
        phone_col    = st.selectbox("מספר טלפון", stud_cols, index=stud_cols.index(phone_guess) if phone_guess in stud_cols else 0)
        mail_col     = st.selectbox("אימייל", stud_cols, index=stud_cols.index(mail_guess) if mail_guess in stud_cols else 0)
        s_lat_col    = st.selectbox("סטודנט: קו רוחב (אופציונלי)", [None] + stud_cols, index=(stud_cols.index(lat_guess)+1) if lat_guess in stud_cols else 0)
        s_lon_col    = st.selectbox("סטודנט: קו אורך (אופציונלי)", [None] + stud_cols, index=(stud_cols.index(lon_guess)+1) if lon_guess in stud_cols else 0)
    with m3:
        partner_col  = st.selectbox("מזהה בן/בת זוג (אופציונלי)", [None] + stud_cols, index=(stud_cols.index(partner_guess)+1) if partner_guess in stud_cols else 0)
        reason_col   = st.selectbox("סיבת התחשבות (טקסט/עדיפות) אופציונלי", [None] + stud_cols, index=(stud_cols.index(reason_guess)+1) if reason_guess in stud_cols else 0)

    st.markdown("---")
    n1, n2, n3 = st.columns(3)
    with n1:
        site_name_col = st.selectbox("שם מקום השיבוץ", site_cols, index=site_cols.index(site_name_guess) if site_name_guess in site_cols else 0)
        site_city_col = st.selectbox("מיקום (עיר) השיבוץ", site_cols, index=site_cols.index(site_city_guess) if site_city_guess in site_cols else 0)
        site_zip_col  = st.selectbox("מיקוד", [None] + site_cols, index=(site_cols.index(site_zip_guess)+1) if site_zip_guess in site_cols else 0)
    with n2:
        site_type_col = st.selectbox("סוג מקום השיבוץ (כלא/בית חולים/…)", [None] + site_cols, index=(site_cols.index(site_type_guess)+1) if site_type_guess in site_cols else 0)
        site_sup_col  = st.selectbox("שם המדריך/ה (אופציונלי)", [None] + site_cols, index=(site_cols.index(site_sup_guess)+1) if site_sup_guess in site_cols else 0)
        site_cap_col  = st.selectbox("קיבולת (מספר סטודנטים)", [None] + site_cols, index=(site_cols.index(site_cap_guess)+1) if site_cap_guess in site_cols else 0)
    with n3:
        site_lat_col  = st.selectbox("אתר: קו רוחב (אופציונלי)", [None] + site_cols, index=(site_cols.index(site_lat_guess)+1) if site_lat_guess in site_cols else 0)
        site_lon_col  = st.selectbox("אתר: קו אורך (אופציונלי)", [None] + site_cols, index=(site_cols.index(site_lon_guess)+1) if site_lon_guess in site_cols else 0)

    st.markdown("---")
    w1, w2, w3 = st.columns(3)
    with w1:
        w_distance = st.slider("משקל מרחק (גבוה = עדיפות לקרוב)", min_value=0.0, max_value=1.0, value=0.8, step=0.05)
    with w2:
        sep_partners = st.checkbox("להפריד בני/ות זוג (לא אותו אתר/מדריך)", value=True)
    with w3:
        enforce_capacity = st.checkbox("להכיל קיבולת אתרים", value=True)

    submitted = st.form_submit_button("🧮 חשב שיבוץ")

# =========================
# הכנת נתונים
# =========================
if not submitted:
    st.stop()

# הכן עותקים עם שמות עמודות סטנדרטיים
S = pd.DataFrame({
    "student_id": stud_df[stud_id_col],
    "first_name": stud_df[first_col],
    "last_name":  stud_df[last_col],
    "home_city":  stud_df[city_col],
    "phone":      stud_df[phone_col],
    "email":      stud_df[mail_col],
})
if s_lat_col: S["s_lat"] = pd.to_numeric(stud_df[s_lat_col], errors="coerce")
else:         S["s_lat"] = np.nan
if s_lon_col: S["s_lon"] = pd.to_numeric(stud_df[s_lon_col], errors="coerce")
else:         S["s_lon"] = np.nan
if partner_col: S["partner_id"] = stud_df[partner_col]
else:           S["partner_id"] = None
if reason_col:  S["reason"] = stud_df[reason_col].astype(str)
else:           S["reason"] = ""

T = pd.DataFrame({
    "site_name": site_df[site_name_col],
    "site_city": site_df[site_city_col],
})
if site_zip_col:  T["zip"]   = site_df[site_zip_col]
else:             T["zip"]   = ""
if site_type_col: T["sitetype"] = site_df[site_type_col]
else:             T["sitetype"] = ""
if site_sup_col:  T["supervisor"] = site_df[site_sup_col]
else:             T["supervisor"] = ""
if site_cap_col:  T["capacity"] = pd.to_numeric(site_df[site_cap_col], errors="coerce").fillna(1).astype(int)
else:             T["capacity"] = 9999  # ללא מגבלה
if site_lat_col:  T["t_lat"] = pd.to_numeric(site_df[site_lat_col], errors="coerce")
else:             T["t_lat"] = np.nan
if site_lon_col:  T["t_lon"] = pd.to_numeric(site_df[site_lon_col], errors="coerce")
else:             T["t_lon"] = np.nan

S.fillna({"partner_id":"", "reason":""}, inplace=True)
T.fillna({"zip":"", "sitetype":"", "supervisor":"", "capacity":1}, inplace=True)

# =========================
# מטריצת מרחקים + ניקוד
# =========================
dist_matrix = pd.DataFrame(index=S.index, columns=T.index, dtype=float)

if S[["s_lat","s_lon"]].notna().all(axis=None) and T[["t_lat","t_lon"]].notna().all(axis=None):
    for i in S.index:
        for j in T.index:
            dist_matrix.loc[i, j] = haversine_km(S.loc[i,"s_lat"], S.loc[i,"s_lon"], T.loc[j,"t_lat"], T.loc[j,"t_lon"])
else:
    dist_matrix[:] = np.nan

# נרמול מרחק לפי סטודנט (0..1 לכל שורה)
norm_dist = dist_matrix.apply(normalize_series, axis=1)

# ציון התאמה: מרחק קטן -> ציון גבוה (אם חסר מרחק, נחשב כרחוק)
score = pd.DataFrame(0.0, index=S.index, columns=T.index)
if norm_dist.notna().any().any():
    score = w_distance * (1 - norm_dist.fillna(norm_dist.max().fillna(1)))

# =========================
# אלגוריתם שיבוץ גרידי
# =========================
assignments = []
site_slots = T["capacity"].copy() if enforce_capacity else pd.Series([999999]*len(T), index=T.index)

# סדר עדיפויות: עבור כל סטודנט – האתר עם הציון הגבוה ביותר
preferred_sites = score.apply(lambda row: list(row.sort_values(ascending=False).index), axis=1)

assigned_site_idx = {}  # map student idx -> site idx

for i in S.index:
    for site_idx in preferred_sites[i]:
        # קיבולת
        if site_slots[site_idx] <= 0:
            continue

        # הפרדת בני/בנות זוג
        if sep_partners and S.loc[i, "partner_id"]:
            partner_mask = (S["student_id"].astype(str) == str(S.loc[i, "partner_id"])) | \
                           (S["partner_id"].astype(str) == str(S.loc[i, "student_id"]))
            partner_indices = S.index[partner_mask].tolist()
            conflict = False
            for pi in partner_indices:
                if pi in assigned_site_idx:
                    other_site = assigned_site_idx[pi]
                    # לא אותו אתר
                    if other_site == site_idx:
                        conflict = True
                        break
                    # לא אותו מדריך (אם יש)
                    if T.loc[other_site, "supervisor"] and T.loc[other_site, "supervisor"] == T.loc[site_idx, "supervisor"]:
                        conflict = True
                        break
            if conflict:
                continue  # נסה אתר אחר

        # שיבוץ
        assigned_site_idx[i] = site_idx
        site_slots[site_idx] -= 1
        break

# =========================
# בניית פלט
# =========================
rows = []
for i, site_idx in assigned_site_idx.items():
    s = S.loc[i]
    t = T.loc[site_idx]

    # מרחק בק"מ
    d_km = np.nan
    if not np.isnan(s["s_lat"]) and not np.isnan(s["s_lon"]) and not np.isnan(t["t_lat"]) and not np.isnan(t["t_lon"]):
        d_km = haversine_km(s["s_lat"], s["s_lon"], t["t_lat"], t["t_lon"])

    # אחוז התאמה – מהציון (0..1) -> 0..100
    pct = 0.0
    if site_idx in score.columns:
        sc = score.loc[i, site_idx]
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

st.subheader("📊 תוצאת השיבוץ")
st.dataframe(result_df, use_container_width=True)

# הורדה כ-CSV
csv_data = result_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ הורדת קובץ השיבוץ (CSV)",
    data=csv_data,
    file_name="שיבוץ_סטודנטים.csv",
    mime="text/csv"
)

st.caption("הערה: אם אין עמודות קואורדינטות (lat/lon) לסטודנטים ולאתרים – המרחק יחושב כלא זמין והציון יתבסס רק על אילוצים אחרים. מומלץ להוסיף lat/lon לכל רשומה לקבלת מרחק מדויק.")
