# streamlit_app.py
# ---------------------------------------------------------
# שיבוץ סטודנטים – "מי-מתאים-ל"
# קבצים נתמכים כברירת מחדל:
#   1) example_assignment_result_5.csv  -> אתרים/מדריכים (+Capacity ושדות)
#   2) student_form_example_5.csv       -> סטודנטים (+העדפות ושדות)
# UI פשוט: העלאה, מיפוי אוטומטי, הסבר מובנה, שיבוץ וייצוא
# ---------------------------------------------------------

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from io import BytesIO
import re

# =============== הגדרות מסך + RTL ===============
st.set_page_config(page_title="שיבוץ סטודנטים – מי-מתאים-ל", layout="wide")
st.markdown("""
<style>
:root{ --ink:#0f172a; --muted:#475569; --ring:rgba(99,102,241,.25); --card:rgba(255,255,255,.9); }
html, body, [class*="css"] { font-family: system-ui, "Segoe UI", Arial; }
.stApp, .main, [data-testid="stSidebar"]{ direction:rtl; text-align:right; }
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 8% 8%, #e0f7fa 0%, transparent 65%),
    radial-gradient(1000px 500px at 92% 12%, #ede7f6 0%, transparent 60%),
    radial-gradient(900px 500px at 20% 90%, #fff3e0 0%, transparent 55%);
}
.block-container{ padding-top: 1rem; }
.small{ font-size: 0.9rem; color: var(--muted); }
.kpi{ background:var(--card); border:1px solid #e2e8f0; padding:12px; border-radius:14px; }
hr{ border-color:#e2e8f0; }
</style>
""", unsafe_allow_html=True)

# =============== קבצי ברירת מחדל ===============
DEFAULT_STUDENTS = Path("./student_form_example_5.csv")
DEFAULT_SITES    = Path("./example_assignment_result_5.csv")
DEFAULT_ASSIGN   = Path("./assignments.csv")

# =============== עזרי קריאה וניקוי ===============
def read_csv_smart(obj):
    if obj is None: return None
    try:
        return pd.read_csv(obj)
    except Exception:
        try:
            if hasattr(obj, "seek"): obj.seek(0)
            return pd.read_csv(obj, encoding="utf-8-sig")
        except Exception:
            return None

def _strip(x): 
    return "" if pd.isna(x) else str(x).strip()

def _lc(x): 
    return _strip(x).lower()

def _split_multi(x):
    """פיצול שדות רב-ערכיים ('א,ב;ג|ד' וכו') לסט ערכים קטנים."""
    if pd.isna(x): return set()
    s = str(x)
    s = re.sub(r"[;/\|]", ",", s)
    if "," not in s:
        s = re.sub(r"\s{2,}", ",", s)
    return set(p.strip().lower() for p in s.split(",") if p.strip())

def df_to_csv_bytes(df, filename):
    buff = BytesIO()
    df.to_csv(buff, index=False, encoding="utf-8-sig")
    buff.seek(0)
    return buff, filename

# =============== קריאת קבצים ===============
with st.sidebar:
    st.header("העלאת קבצים")
    st.caption("ברירת מחדל: הקבצים בשם המדויק בתקייה. אפשר גם להעלות ידנית.")
    up_sites    = st.file_uploader("אתרים/מדריכים – example_assignment_result_5.csv", type=["csv"])
    up_students = st.file_uploader("סטודנטים – student_form_example_5.csv", type=["csv"])

sites_df = read_csv_smart(up_sites) if up_sites else (read_csv_smart(DEFAULT_SITES) if DEFAULT_SITES.exists() else None)
students_df = read_csv_smart(up_students) if up_students else (read_csv_smart(DEFAULT_STUDENTS) if DEFAULT_STUDENTS.exists() else None)

# =============== כותרת + סטטוס ===============
c1, c2 = st.columns([1.4, 1])
with c1:
    st.title("📋 שיבוץ סטודנטים – מי-מתאים-ל")
    with st.expander("איך השיבוץ עובד? (הסבר קצר)", expanded=True):
        st.markdown("""
- מחשבים **ציון התאמה** בין כל סטודנט לכל אתר:
  - התאמת שדות שנבחרו (עיר/תחום/שפה/ימים וכו׳):  
    חד-ערכי זהה = ‎**+1.0**;  
    רב-ערכי (רשימות) – לכל ערך חופף = ‎**+0.8**.
  - **בונוס העדפות** לשם אתר זהה: Pref1=+2.0, Pref2=+1.5, Pref3=+1.0, Pref4+=+0.7.
- לאחר מכן מקצים **גרידית לפי קיבולת**: לכל סטודנט נבחר האתר עם הציון הגבוה ביותר שעדיין יש בו מקום.
- אם אין אתר פנוי/מתאים → "ללא שיבוץ".
        """)
with c2:
    with st.container(border=True):
        st.markdown('<div class="kpi">', unsafe_allow_html=True)
        st.subheader("סטטוס נתונים")
        st.write(f"סטודנטים: **{0 if students_df is None else len(students_df)}**")
        st.write(f"אתרים/מדריכים: **{0 if sites_df is None else len(sites_df)}**")
        st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# =============== לשונית נתונים ===============
tab_data, tab_match, tab_export = st.tabs(["📥 נתונים", "🧩 שיבוץ", "📤 ייצוא"])

with tab_data:
    if students_df is None or sites_df is None:
        st.warning("חסרים קבצים. ודאי שהעלית את שני הקבצים או שהם בתיקייה בשם המדויק.", icon="⚠️")
    else:
        cA, cB = st.columns(2)
        with cA:
            st.markdown("**סטודנטים (Raw):**")
            st.dataframe(students_df, use_container_width=True, height=360)
        with cB:
            st.markdown("**אתרים/מדריכים (Raw):**")
            st.dataframe(sites_df, use_container_width=True, height=360)
        st.caption("טיפ: השמות בהעדפות חייבים להיות זהים בדיוק לשדה שם האתר כדי לקבל בונוס העדפות.")

# =============== מיפוי אוטומטי של עמודות ===============
def guess(colnames, wanted):
    """מוצא עמודה מתאימה לפי רשימת מילות מפתח."""
    lo = [c.lower() for c in colnames]
    for w in wanted:
        if w.lower() in lo:
            return colnames[lo.index(w.lower())]
    # ניסיון לפי 'contains'
    for c in colnames:
        lc = c.lower()
        for w in wanted:
            if w.lower() in lc:
                return c
    return None

def sorted_pref_cols(cols):
    pref_cols = [c for c in cols if re.match(r'(?i)(pref|העדפ)[\s_]*\d+', c)]
    def k(c):
        m = re.search(r'(\d+)', c)
        return int(m.group(1)) if m else 999
    return sorted(pref_cols, key=k)

# סטודנטים
stu_id_col = None; stu_name_col = None; stu_pref_single = None; stu_pref_cols = []
if students_df is not None:
    scols = list(students_df.columns)
    stu_id_col = guess(scols, ["student_id","id","תז","מספר סטודנט"])
    if stu_id_col is None: stu_id_col = scols[0]
    stu_name_col = guess(scols, ["student_name","name","שם","שם סטודנט","full name","full_name"])
    if stu_name_col is None: stu_name_col = scols[min(1, len(scols)-1)]
    # העדפות
    stu_pref_single = guess(scols, ["העדפות","preferences","prefs","עדפות"])
    if stu_pref_single is None:
        stu_pref_cols = sorted_pref_cols(scols)

# אתרים
site_name_col = None; site_cap_col = None
common_pairs = []  # זוגות שדות מי-מתאים-ל
if sites_df is not None:
    tcols = list(sites_df.columns)
    site_name_col = guess(tcols, ["site_name","site","שם אתר","מוסד","מדריך","organization","place","שם"])
    if site_name_col is None: site_name_col = tcols[0]
    site_cap_col = guess(tcols, ["capacity","cap","קיבולת","מספר מקומות","מקומות","מס' מקומות","כמות"])
    # זוגות התאמה מוצעים אוטומטית: שדות בעלי אותו שם
    if students_df is not None:
        for sc in students_df.columns:
            if sc == stu_id_col or sc == stu_name_col: 
                continue
            if sc in tcols:
                common_pairs.append((sc, sc))
# אם אין כלל – נציע שמות שכיחים
if not common_pairs and students_df is not None and sites_df is not None:
    candidates = [("עיר","עיר"), ("תחום","תחום"), ("שפה","שפה"), ("ימים","ימים"), ("קהל יעד","קהל יעד")]
    for a,b in candidates:
        if a in students_df.columns and b in sites_df.columns:
            common_pairs.append((a,b))

# =============== פרמטרים (פשוטים, עם "מתקדמות" אופציונלי) ===============
with st.sidebar:
    st.divider()
    st.subheader("משקלים (פשוט)")
    w_exact = st.number_input("חד-ערכי זהה", 0.0, 10.0, 1.0, 0.1)
    w_overlap = st.number_input("חפיפה בערכי רשימה (לכל ערך)", 0.0, 10.0, 0.8, 0.1)
    st.caption("העדפות: Pref1=2.0, Pref2=1.5, Pref3=1.0, Pref4+=0.7 (ניתן לשנות ב'מתקדמות').")
    show_adv = st.checkbox("מתקדמות (שינוי בונוסים/זוגות שדות/בחירה ידנית)", value=False)

    if show_adv:
        w_pref1 = st.number_input("בונוס Pref1", 0.0, 10.0, 2.0, 0.1)
        w_pref2 = st.number_input("בונוס Pref2", 0.0, 10.0, 1.5, 0.1)
        w_pref3 = st.number_input("בונוס Pref3", 0.0, 10.0, 1.0, 0.1)
        w_pref_other = st.number_input("בונוס Pref4+", 0.0, 10.0, 0.7, 0.1)
        st.markdown("**זוגות שדות מי-מתאים-ל**")
        adv_pairs = []
        if students_df is not None and sites_df is not None:
            s_cols = list(students_df.columns); t_cols = list(sites_df.columns)
            count = st.number_input("כמה זוגות?", 0, 20, min(3, len(common_pairs)), 1)
            for i in range(int(count)):
                c1, c2 = st.columns(2)
                with c1:
                    left = st.selectbox(f"שדה סטודנט #{i+1}", s_cols, index=(s_cols.index(common_pairs[i][0]) if i < len(common_pairs) else 0), key=f"adv_stu_{i}")
                with c2:
                    right = st.selectbox(f"שדה אתר #{i+1}", t_cols, index=(t_cols.index(common_pairs[i][1]) if i < len(common_pairs) else 0), key=f"adv_site_{i}")
                adv_pairs.append((left, right))
        chosen_pairs = adv_pairs if show_adv and len(adv_pairs)>0 else common_pairs
        pref_manual = True
    else:
        # ברירות מחדל פשוטות
        w_pref1, w_pref2, w_pref3, w_pref_other = 2.0, 1.5, 1.0, 0.7
        chosen_pairs = common_pairs
        pref_manual = False

# =============== פונקציות עיקריות ===============
def extract_preferences(df):
    """רשימת העדפות לכל סטודנט: או עמודה אחת עם פסיקים, או Pref1/2/..."""
    if stu_pref_single and stu_pref_single in df.columns:
        prefs = []
        for val in df[stu_pref_single].fillna("").astype(str):
            prefs.append([p.strip() for p in val.split(",") if p.strip()])
        return prefs
    elif stu_pref_cols:
        # מיון מספרי
        def k(c):
            m = re.search(r'(\d+)', str(c)); return int(m.group(1)) if m else 999
        cols = sorted(stu_pref_cols, key=k)
        prefs = []
        for _, row in df[cols].iterrows():
            prefs.append([_strip(x) for x in row.tolist() if _strip(x)])
        return prefs
    else:
        return [[] for _ in range(len(df))]

def calc_match_score(stu_row, site_row, prefs):
    score = 0.0
    # זוגות מי-מתאים-ל
    for (sf, tf) in chosen_pairs:
        vs = stu_row[sf] if sf in stu_row else ""
        vt = site_row[tf] if tf in site_row else ""
        # אם אחד מהשדות נראה רב-ערכי – חפיפה
        if (isinstance(vs, str) and ("," in vs or ";" in vs or "|" in vs)) or \
           (isinstance(vt, str) and ("," in vt or ";" in vt or "|" in vt)):
            sset, tset = _split_multi(vs), _split_multi(vt)
            inter = sset.intersection(tset)
            score += w_overlap * len(inter)
        else:
            if _lc(vs) != "" and _lc(vs) == _lc(vt):
                score += w_exact
    # בונוס העדפות מול שם האתר
    site_name = _strip(site_row[site_name_col])
    if site_name:
        pos = None
        for i, p in enumerate(prefs):
            if _strip(p) == site_name:
                pos = i; break
        if pos is not None:
            if pos == 0: score += w_pref1
            elif pos == 1: score += w_pref2
            elif pos == 2: score += w_pref3
            else: score += w_pref_other
    return score

# =============== לשונית שיבוץ ===============
with tab_match:
    if students_df is None or sites_df is None:
        st.warning("חסרים נתונים. העלי את שני הקבצים בלשונית הראשונה.", icon="⚠️")
    else:
        # הצגה קצרה של המיפוי שנקבע
        with st.expander("מיפוי שנקבע (לבדיקה מהירה)", expanded=True):
            st.markdown(f"- **מזהה סטודנט:** `{stu_id_col}`  |  **שם סטודנט:** `{stu_name_col}`")
            if stu_pref_single: st.markdown(f"- **עמודת העדפות (יחידה):** `{stu_pref_si
