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
from datetime import datetime
from io import BytesIO
import re

# =========================
# הגדרות כלליות + עיצוב
# =========================
st.set_page_config(page_title="שיבוץ סטודנטים – מי-מתאים-ל", layout="wide")

st.markdown("""
<style>
:root{
  --ink:#0f172a; --muted:#475569; --subtle:#64748b;
  --brand:#6c5ce7; --brand-2:#a78bfa; --card:rgba(255,255,255,.92);
}
html, body, [class*="css"] { font-family: "Heebo", system-ui, -apple-system, "Segoe UI", Arial; }
.stApp, .main, [data-testid="stSidebar"]{ direction:rtl; text-align:right; }
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1100px 540px at 12% 8%, #e6faff 0%, transparent 65%),
    radial-gradient(900px 480px at 88% 10%, #efe9ff 0%, transparent 60%),
    radial-gradient(900px 520px at 18% 90%, #fff2df 0%, transparent 55%);
}
.block-container{ padding-top: 0.8rem; }

.hero{
  padding: 28px 24px; border-radius: 18px;
  background: linear-gradient(180deg, rgba(255,255,255,.95), rgba(255,255,255,.88));
  border:1px solid #eaeef3;
  box-shadow: 0 6px 30px rgba(17,24,39,.06);
}
.hero h1{ margin:0 0 6px 0; color:var(--ink); font-size: 28px;}
.hero p{ margin: 0; color:var(--subtle); }

.card{
  background:var(--card); border:1px solid #e8edf5; border-radius:16px; padding:16px;
  box-shadow: 0 4px 18px rgba(2,6,23,.04);
}
.metric{
  display:flex; align-items:center; justify-content:space-between;
  padding:12px 14px; border:1px solid #e8edf5; border-radius:14px; background:#fff;
}
.metric .label{ color:var(--subtle); font-size:.9rem; }
.metric .value{ color:var(--ink); font-weight:700; }

.section-title{
  margin: 8px 0 6px 0; font-weight:700; color:var(--ink);
}
hr{ border-color:#eef2f7; }

[data-testid="stSidebar"]{
  background: linear-gradient(180deg, rgba(255,255,255,.95), rgba(255,255,255,.85));
  border-left:1px solid #eaeef3;
}
.small{ color:#64748b; font-size:.92rem; }
</style>
""", unsafe_allow_html=True)

# =========================
# קבועים ושמות קבצים
# =========================
DEFAULT_STUDENTS = Path("./student_form_example_5.csv")
DEFAULT_SITES    = Path("./example_assignment_result_5.csv")
DEFAULT_ASSIGN   = Path("./assignments.csv")

# =========================
# פונקציות עזר
# =========================
def read_csv_flex(path_or_upload):
    if path_or_upload is None:
        return None
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

def split_multi(x):
    if pd.isna(x): return set()
    s = str(x)
    s = re.sub(r"[;/|]", ",", s)      # מפרידים חלופיים
    if "," not in s:
        s = re.sub(r"\s{2,}", ",", s) # רווחים מרובים -> פסיק
    return set(p.strip().lower() for p in s.split(",") if p.strip())

def bytes_for_download(df, filename):
    bio = BytesIO()
    df.to_csv(bio, index=False, encoding="utf-8-sig")
    bio.seek(0)
    return bio, filename

# =========================
# משקולות חישוב (פשוט וברור)
# =========================
W_DOMAIN_MAIN  = 2.0   # התאמה בין "תחום מועדף" ל"תחום ההתמחות"
W_DOMAIN_MULTI = 1.0   # חפיפה נוספת ערך-ערך בין רשימות
W_CITY         = 1.2   # התאמת עיר מגורים לעיר אתר

# =========================
# Sidebar – העלאות
# =========================
with st.sidebar:
    st.header("העלאת נתונים")
    st.caption("אם לא תעלי קובץ – נטען מהתיקייה בשם הדיפולטי.")
    up_students = st.file_uploader("סטודנטים – student_form_example_5.csv", type=["csv"])
    up_sites    = st.file_uploader("אתרים/מדריכים – example_assignment_result_5.csv", type=["csv"])

# קריאה בפועל
students_raw = read_csv_flex(up_students) if up_students else (read_csv_flex(DEFAULT_STUDENTS) if DEFAULT_STUDENTS.exists() else None)
sites_raw    = read_csv_flex(up_sites)    if up_sites    else (read_csv_flex(DEFAULT_SITES)    if DEFAULT_SITES.exists()    else None)

# =========================
# Hero
# =========================
st.markdown(
    """
<div class="hero">
  <h1>📅 שיבוץ סטודנטים – מי-מתאים-ל</h1>
  <p>השיבוץ מבוצע לפי חפיפה בין <b>תחומי הסטודנט/ית</b> ל<b>תחום ההתמחות באתר</b>, התאמת <b>עיר מגורים</b> ל<b>עיר האתר</b>, ולאחר מכן חלוקת מקומות לפי <b>קיבולת</b>.</p>
</div>
""",
    unsafe_allow_html=True
)

st.write("")

# =========================
# כרטיס סטטוס
# =========================
c1, c2 = st.columns([1.2, 1])
with c1:
    st.markdown("### שלבי עבודה")
    st.markdown("- העלאת שני הקבצים (או טעינה אוטומטית).")
    st.markdown("- בדיקה קצרה של הנתונים (לשונית נתונים).")
    st.markdown("- לחיצה על \"הרצת שיבוץ\" (לשונית שיבוץ).")
    st.markdown("- הורדה/שמירה של התוצאות (לשונית ייצוא).")
with c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="metric"><span class="label">סטודנטים נטענו</span><span class="value">{}</span></div>'.format(0 if students_raw is None else len(students_raw)), unsafe_allow_html=True)
    st.markdown('<div class="metric"><span class="label">רשומות אתרים נטענו</span><span class="value">{}</span></div>'.format(0 if sites_raw is None else len(sites_raw)), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")
st.markdown("---")

# =========================
# Tabs
# =========================
tab1, tab2, tab3, tab4 = st.tabs(["📥 נתונים", "ℹ️ איך מחשבים ציון", "🧩 שיבוץ", "📤 ייצוא"])

# =========================
# לשונית נתונים
# =========================
with tab1:
    st.markdown("#### מיפוי עמודות אוטומטי לקבצים שלך")
    st.info(
        "**סטודנטים**: `שם פרטי`, `שם משפחה`, `עיר מגורים`, `תחומים מבוקשים`, `תחום מועדף`  \n"
        "**אתרים**: `מוסד / שירות הכשרה` (שם האתר), `תחום ההתמחות`, `עיר`, `מספר סטודנטים שניתן לקלוט השנה` (קיבולת)",
        icon="ℹ️"
    )

    if students_raw is None or sites_raw is None:
        st.warning("יש להעלות/לספק את שני הקבצים.", icon="⚠️")
    else:
        with st.expander("סטודנטים – הצגה מקוצרת (Raw)", expanded=False):
            st.dataframe(students_raw, use_container_width=True, height=340)
        with st.expander("אתרים/מדריכים – הצגה מקוצרת (Raw)", expanded=False):
            st.dataframe(sites_raw, use_container_width=True, height=340)

# =========================
# לשונית הסבר ציון
# =========================
with tab2:
    st.markdown("#### כך מחושב ציון ההתאמה")
    st.markdown(
        f"""
1. **תחום מועדף** ↔ **תחום ההתמחות**: אם קיים חיתוך – ציון בסיסי **{W_DOMAIN_MAIN}** + **{W_DOMAIN_MULTI}** לכל ערך תואם נוסף.  
2. **תחומים מבוקשים** ↔ **תחום ההתמחות**: עבור כל ערך תואם מתקבל **{W_DOMAIN_MULTI}**.  
3. **עיר מגורים** ↔ **עיר האתר**: התאמה מדויקת מוסיפה **{W_CITY}**.  

לאחר חישוב כל הציונים, מופעל שיבוץ Greedy: לכל סטודנט/ית נלקח האתר עם הציון הגבוה ביותר שעוד יש בו מקום.
"""
    )

# =========================
# לשונית שיבוץ
# =========================
with tab3:
    if students_raw is None or sites_raw is None:
        st.warning("חסרים נתונים. העלי את שני הקבצים בלשונית הראשונה.", icon="⚠️")
    else:
        # שמות העמודות כפי שהוגדרו בטפסים שלך
        STU_FIRST   = "שם פרטי"
        STU_LAST    = "שם משפחה"
        STU_CITY    = "עיר מגורים"
        STU_DOMS    = "תחומים מבוקשים"
        STU_PREFDOM = "תחום מועדף"

        SITE_NAME   = "מוסד / שירות הכשרה"
        SITE_CITY   = "עיר"
        SITE_DOMAIN = "תחום ההתמחות"
        SITE_CAP    = "מספר סטודנטים שניתן לקלוט השנה"

        # בדיקת קיום עמודות חיוניות
        missing = []
        for req in [STU_FIRST, STU_LAST, STU_CITY, STU_DOMS, STU_PREFDOM]:
            if req not in students_raw.columns: missing.append(f"סטודנטים: {req}")
        for req in [SITE_NAME, SITE_CITY, SITE_DOMAIN, SITE_CAP]:
            if req not in sites_raw.columns: missing.append(f"אתרים: {req}")
        if missing:
            st.error("עמודות חסרות: " + " | ".join(missing))
            st.stop()

        # הכנה
        stu  = students_raw.copy()
        site = sites_raw.copy()

        stu["student_id"] = [f"S{i+1:03d}" for i in range(len(stu))]
        stu["student_name"] = (
            stu[STU_FIRST].astype(str).fillna("") + " " +
            stu[STU_LAST].astype(str).fillna("")
        ).str.strip()

        cap_series = pd.to_numeric(site[SITE_CAP], errors="coerce").fillna(1).astype(int)
        site = site.assign(capacity=cap_series.clip(lower=0))
        site = site[site["capacity"] > 0]

        # קיבולת לפי שם אתר
        site_capacity = {}
        for sname, grp in site.groupby(site[SITE_NAME].astype(str).str.strip()):
            site_capacity[sname] = int(grp["capacity"].sum())

        # אתרים ייחודיים (תכונות)
        sites_unique = site.drop_duplicates(subset=[SITE_NAME]).reset_index(drop=True)

        # ציון התאמה
        def match_score(stu_row, site_row):
            score = 0.0

            # תחום מועדף מול תחום ההתמחות
            pref_set    = split_multi(stu_row.get(STU_PREFDOM, ""))
            site_domain = split_multi(site_row.get(SITE_DOMAIN, "")) or {_lc(site_row.get(SITE_DOMAIN, ""))}
            inter1 = pref_set.intersection(site_domain)
            if len(inter1) > 0:
                score += W_DOMAIN_MAIN + W_DOMAIN_MULTI * len(inter1)

            # תחומים מבוקשים (ריבוי) מול תחום ההתמחות (ריבוי)
            all_set = split_multi(stu_row.get(STU_DOMS, ""))
            inter2 = all_set.intersection(site_domain)
            if len(inter2) > 0:
                score += W_DOMAIN_MULTI * len(inter2)

            # עיר
            if _lc(stu_row.get(STU_CITY, "")) != "" and _lc(stu_row.get(STU_CITY, "")) == _lc(site_row.get(SITE_CITY, "")):
                score += W_CITY

            return score

        # טבלת ציונים לכל צמד
        rows = []
        for _, s in stu.iterrows():
            for _, t in sites_unique.iterrows():
                rows.append((
                    s["student_id"], s["student_name"],
                    _strip(t.get(SITE_NAME, "")),
                    match_score(s, t)
                ))
        scores = pd.DataFrame(rows, columns=["student_id","student_name","site_name","score"])

        # דיאגנוסטיקה: TOP-3 לכל סטודנט
        st.markdown("##### Top-3 התאמות לכל סטודנט/ית")
        top3 = scores.sort_values(["student_id","score"], ascending=[True, False]).groupby("student_id").head(3)
        st.dataframe(top3, use_container_width=True, height=320)

        # שיבוץ Greedy עם קיבולת
        assignments, cap_left = [], site_capacity.copy()
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

        # KPI
        cA, cB, cC = st.columns(3)
        with cA: st.metric("סה\"כ סטודנטים", len(asg))
        with cB: st.metric("שובצו", int((asg["status"]=="שובץ").sum()))
        with cC: st.metric("ממתינים", int((asg["status"]=="ממתין").sum()))

        st.session_state["assignments_df"] = asg

# =========================
# לשונית ייצוא
# =========================
with tab4:
    st.markdown("#### הורדת תוצאות")
    if isinstance(st.session_state.get("assignments_df"), pd.DataFrame):
        out = st.session_state["assignments_df"].copy()
        st.dataframe(out, use_container_width=True, height=340)

        fname = f"assignments_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        buff, _ = bytes_for_download(out, fname)
        st.download_button("⬇️ הורדת CSV", buff, file_name=fname, mime="text/csv", use_container_width=True)

        if st.checkbox("שמור גם בשם הקבוע assignments.csv"):
            try:
                out.to_csv(DEFAULT_ASSIGN, index=False, encoding="utf-8-sig")
                st.success("נשמר assignments.csv בתיקיית האפליקציה.")
            except Exception as e:
                st.error(f"שגיאת שמירה: {e}")
    else:
        st.info("אין עדיין תוצאות – הריצי שיבוץ בלשונית \"🧩 שיבוץ\".")
