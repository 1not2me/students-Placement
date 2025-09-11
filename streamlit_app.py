# streamlit_app.py
# ---------------------------------------------------------
# שיבוץ סטודנטים לפי "מי-מתאים-ל" עבור:
# 1) student_form_example_5.csv     (סטודנטים)
# 2) example_assignment_result_5.csv (אתרים/מדריכים)
# קריטריונים: תחום (חפיפה), עיר (התאמה), + קיבולת
# ---------------------------------------------------------

import streamlit as st
import pandas as pd
from pathlib import Path
from io import BytesIO
from datetime import datetime
import re

st.set_page_config(page_title="שיבוץ סטודנטים – מי-מתאים-ל", layout="wide")

# ===== עיצוב ו-RTL =====
st.markdown("""
<style>
:root{ --ink:#0f172a; --muted:#475569; --card:rgba(255,255,255,.9); }
html, body, [class*="css"] { font-family: system-ui, "Segoe UI", Arial; }
.stApp, .main, [data-testid="stSidebar"]{ direction:rtl; text-align:right; }
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 8% 8%, #e0f7fa 0%, transparent 65%),
    radial-gradient(1000px 500px at 92% 12%, #ede7f6 0%, transparent 60%),
    radial-gradient(900px 500px at 20% 90%, #fff3e0 0%, transparent 55%);
}
.block-container{ padding-top: 1.0rem; }
.kpi{ background:var(--card); border:1px solid #e2e8f0; padding:14px; border-radius:16px; }
.small{ color:#475569; font-size:0.92rem; }
hr{ border-color:#e2e8f0; }
</style>
""", unsafe_allow_html=True)

# ===== קבצים =====
DEFAULT_STUDENTS = Path("./student_form_example_5.csv")
DEFAULT_SITES    = Path("./example_assignment_result_5.csv")
DEFAULT_ASSIGN   = Path("./assignments.csv")

# ===== קריאה גמישה =====
def read_csv(path_or_upload):
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

# ===== עזר לניקוי/פיצול =====
def _strip(x): 
    return "" if pd.isna(x) else str(x).strip()

def _lc(x): 
    return _strip(x).lower()

def split_multi(x):
    if pd.isna(x): return set()
    s = str(x)
    s = re.sub(r"[;/|]", ",", s)
    if "," not in s:
        s = re.sub(r"\s{2,}", ",", s)
    return set(p.strip().lower() for p in s.split(",") if p.strip())

# ===== משקולות פשוטות (אפשר לשנות פה בלבד) =====
W_DOMAIN = 2.0     # תחום
W_DOMAIN_MULTI = 1.0  # חפיפה לכל ערך תואם
W_CITY   = 1.2     # עיר

# ===== UI – העלאה או טעינה אוטומטית =====
with st.sidebar:
    st.header("העלאת נתונים")
    st.caption("אם לא תעלי קבצים, נטען את הקבצים הדיפולטיים בתיקייה.")
    up_students = st.file_uploader("סטודנטים – student_form_example_5.csv", type=["csv"])
    up_sites    = st.file_uploader("אתרים/מדריכים – example_assignment_result_5.csv", type=["csv"])

# קריאה
students_raw = read_csv(up_students) if up_students else (read_csv(DEFAULT_STUDENTS) if DEFAULT_STUDENTS.exists() else None)
sites_raw    = read_csv(up_sites)    if up_sites    else (read_csv(DEFAULT_SITES)    if DEFAULT_SITES.exists()    else None)

# ===== כותרת + תקציר =====
c1, c2 = st.columns([1.25, 1])
with c1:
    st.title("🧮 שיבוץ סטודנטים – מי-מתאים-ל")
    st.markdown(
        "<div class='small'>השיבוץ נעשה ע\"פ חפיפה בין <b>תחומי הסטודנט</b> ל-<b>תחום ההתמחות באתר</b>, "
        "וע\"פ התאמת <b>עיר מגורים</b> ל-<b>עיר האתר</b>. לאחר חישוב ציונים, מבוצע שיבוץ Greedy בהתאם לקיבולת האתר.</div>",
        unsafe_allow_html=True
    )
with c2:
    with st.container(border=True):
        st.markdown('<div class="kpi">', unsafe_allow_html=True)
        st.subheader("סטטוס נתונים")
        st.write(f"סטודנטים: **{0 if students_raw is None else len(students_raw)}**")
        st.write(f"אתרים/מדריכים: **{0 if sites_raw is None else len(sites_raw)}**")
        st.markdown("</div>", unsafe_allow_html=True)

st.divider()

tab1, tab2, tab3 = st.tabs(["📥 נתונים", "🧩 שיבוץ", "📤 ייצוא"])

# ===== לשונית נתונים =====
with tab1:
    if students_raw is None or sites_raw is None:
        st.warning("יש להעלות/לספק את שני הקבצים.", icon="⚠️")
    else:
        cA, cB = st.columns(2)
        with cA:
            st.markdown("**סטודנטים (Raw):**")
            st.dataframe(students_raw, use_container_width=True, height=360)
        with cB:
            st.markdown("**אתרים/מדריכים (Raw):**")
            st.dataframe(sites_raw, use_container_width=True, height=360)

        st.info("""
**העמודות שבהן האפליקציה משתמשת (ממופות אוטומטית):**
- סטודנטים: `שם פרטי`, `שם משפחה`, `עיר מגורים`, `תחומים מבוקשים`, `תחום מועדף`
- אתרים: `מוסד / שירות הכשרה` (שם האתר), `תחום ההתמחות`, `עיר`, `מספר סטודנטים שניתן לקלוט השנה` (קיבולת)
        """, icon="ℹ️")

# ===== לשונית שיבוץ =====
with tab2:
    if students_raw is None or sites_raw is None:
        st.warning("חסרים נתונים. העלי את שני הקבצים בלשונית הראשונה.", icon="⚠️")
    else:
        # ---- מיפוי שמות עמודות (אוטומטי עבור הקבצים שלך) ----
        STU_FIRST   = "שם פרטי"
        STU_LAST    = "שם משפחה"
        STU_CITY    = "עיר מגורים"
        STU_DOMS    = "תחומים מבוקשים"
        STU_PREFDOM = "תחום מועדף"

        SITE_NAME   = "מוסד / שירות הכשרה"
        SITE_CITY   = "עיר"
        SITE_DOMAIN = "תחום ההתמחות"
        SITE_CAP    = "מספר סטודנטים שניתן לקלוט השנה"

        # ---- ניקוי/הכנה ----
        stu = students_raw.copy()
        site = sites_raw.copy()

        # מלאי מזהה ושם מלא
        stu["student_id"] = [f"S{i+1:03d}" for i in range(len(stu))]
        stu["student_name"] = (stu.get(STU_FIRST, "").astype(str).fillna("") + " " + stu.get(STU_LAST, "").astype(str).fillna("")).str.strip()

        # קיבולת
        cap_series = pd.to_numeric(site.get(SITE_CAP, 1), errors="coerce").fillna(1).astype(int)
        site = site.assign(capacity=cap_series.clip(lower=0))
        site = site[site["capacity"] > 0]

        # מיפוי קיבולת לפי שם אתר
        site_name_series = site.get(SITE_NAME, "").astype(str).fillna("").str.strip()
        site_capacity = {}
        for sname, grp in site.groupby(site_name_series):
            site_capacity[sname] = int(grp["capacity"].sum())

        # טבלת אתרים ייחודית לתכונות השוואה
        sites_unique = site.drop_duplicates(subset=[SITE_NAME]).reset_index(drop=True)

        # ---- פונקציית ציון התאמה ----
        def score_row(stu_row, site_row):
            score = 0.0
            # תחום מועדף מול תחום ההתמחות
            pref_set = split_multi(stu_row.get(STU_PREFDOM, ""))
            site_domain = split_multi(site_row.get(SITE_DOMAIN, "")) or { _lc(site_row.get(SITE_DOMAIN, "")) }
            inter1 = pref_set.intersection(site_domain)
            if len(inter1) > 0:
                score += W_DOMAIN + W_DOMAIN_MULTI * len(inter1)

            # תחומים מבוקשים (ריבוי) מול תחום ההתמחות (ריבוי)
            all_set = split_multi(stu_row.get(STU_DOMS, ""))
            inter2 = all_set.intersection(site_domain)
            if len(inter2) > 0:
                score += W_DOMAIN_MULTI * len(inter2)

            # עיר מגורים (התאמה מדויקת)
            if _lc(stu_row.get(STU_CITY, "")) != "" and _lc(stu_row.get(STU_CITY, "")) == _lc(site_row.get(SITE_CITY, "")):
                score += W_CITY

            return score

        # ---- חישוב ציונים לכל סטודנט-אתר ----
        rows = []
        for _, s in stu.iterrows():
            for _, t in sites_unique.iterrows():
                rows.append((
                    s["student_id"], s["student_name"],
                    _strip(t.get(SITE_NAME, "")),
                    score_row(s, t)
                ))
        scores = pd.DataFrame(rows, columns=["student_id","student_name","site_name","score"])

        # הצגה: TOP-3 לכל סטודנט (דיאגנוסטיקה)
        st.markdown("**TOP-3 התאמות לכל סטודנט:**")
        top3 = scores.sort_values(["student_id","score"], ascending=[True, False]).groupby("student_id").head(3)
        st.dataframe(top3, use_container_width=True, height=320)

        # ---- שיבוץ Greedy עם קיבולת ----
        assignments = []
        cap_left = site_capacity.copy()

        for sid, grp in scores.groupby("student_id"):
            grp = grp.sort_values("score", ascending=False)
            chosen, chosen_score, sname = "ללא שיבוץ", 0.0, grp.iloc[0]["student_name"]
            for _, r in grp.iterrows():
                site_nm = r["site_name"]
                if cap_left.get(site_nm, 0) > 0:
                    chosen, chosen_score = site_nm, r["score"]
                    cap_left[site_nm] -= 1
                    break
            assignments.append({
                "student_id": sid,
                "student_name": sname,
                "assigned_site": chosen,
                "match_score": round(chosen_score, 3),
                "status": "שובץ" if chosen != "ללא שיבוץ" else "ממתין"
            })

        asg = pd.DataFrame(assignments).sort_values("student_id")
        st.success(f"שובצו {(asg['status']=='שובץ').sum()} • ממתינים {(asg['status']=='ממתין').sum()}")
        st.dataframe(asg, use_container_width=True, height=420)

        # מדדים קטנים
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("סה\"כ סטודנטים", len(asg))
        with c2: st.metric("שובצו", int((asg["status"]=="שובץ").sum()))
        with c3: st.metric("ממתינים", int((asg["status"]=="ממתין").sum()))

        st.session_state["assignments_df"] = asg

# ===== לשונית ייצוא =====
with tab3:
    st.subheader("ייצוא תוצאות")
    if isinstance(st.session_state.get("assignments_df"), pd.DataFrame):
        out = st.session_state["assignments_df"].copy()
        st.dataframe(out, use_container_width=True, height=360)
        fname = f"assignments_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        buff = BytesIO(); out.to_csv(buff, index=False, encoding="utf-8-sig"); buff.seek(0)
        st.download_button("⬇️ הורדת CSV", buff, file_name=fname, mime="text/csv", use_container_width=True)

        if st.checkbox("שמור גם בשם הקבוע assignments.csv"):
            try:
                out.to_csv(DEFAULT_ASSIGN, index=False, encoding="utf-8-sig")
                st.success("נשמר assignments.csv בתיקיית האפליקציה.")
            except Exception as e:
                st.error(f"שגיאת שמירה: {e}")
    else:
        st.info("אין עדיין תוצאות לשמור – הריצי שיבוץ בלשונית '🧩 שיבוץ'.")
