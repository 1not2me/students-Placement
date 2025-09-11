# streamlit_app.py
# ---------------------------------------------------------
# שיבוץ סטודנטים לפי "מי-מתאים-ל" עבור:
# 1) student_form_example_5.csv     (סטודנטים)
# 2) example_assignment_result_5.csv (אתרים/מדריכים)
# קריטריונים: תחום (חפיפה חכמה), עיר (נירמול), + קיבולת
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
  --brand:#6c5ce7; --card:rgba(255,255,255,.92);
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
.hero{ padding: 28px 24px; border-radius: 18px; background: linear-gradient(180deg, rgba(255,255,255,.95), rgba(255,255,255,.88)); border:1px solid #eaeef3; box-shadow: 0 6px 30px rgba(17,24,39,.06); }
.hero h1{ margin:0 0 6px 0; color:var(--ink); font-size: 28px;}
.hero p{ margin:0; color:var(--subtle); }
.card{ background:var(--card); border:1px solid #e8edf5; border-radius:16px; padding:16px; box-shadow: 0 4px 18px rgba(2,6,23,.04); }
.metric{ display:flex; align-items:center; justify-content:space-between; padding:12px 14px; border:1px solid #e8edf5; border-radius:14px; background:#fff; }
.metric .label{ color:#64748b; font-size:.9rem; }
.metric .value{ color:var(--ink); font-weight:700; }
hr{ border-color:#eef2f7; }
[data-testid="stSidebar"]{ background: linear-gradient(180deg, rgba(255,255,255,.95), rgba(255,255,255,.85)); border-left:1px solid #eaeef3; }
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
# פונקציות עזר – קריאה/נירמול/פיצול
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
    """נירמול: אותיות קטנות, הסרת סוגריים/גרשיים/נקודות, רווחים מיותרים."""
    s = _strip(s)
    s = _PUNCT_RE.sub(" ", s)          # הסר פיסוק/סוגריים/גרשיים
    s = s.replace("-", " ").replace("–", " ").replace("—", " ").replace("/", " ")
    s = _WS_RE.sub(" ", s).strip()
    return s.lower()

def split_multi(raw) -> set:
    """פיצול ערכים מרובים: מזהה פסיקים, נקודה-פסיק, קו־נטוי, תבליט, ירידת שורה, מקפים."""
    if pd.isna(raw): return set()
    s = str(raw).replace("\n", ",")
    s = re.sub(r"[;/|•·•]", ",", s)
    s = s.replace("–", ",").replace("—", ",").replace("/", ",")
    # אם עדיין אין פסיקים – אל נפצל על רווח יחיד כדי לא לשבור ביטוי, רק על 2+ רווחים
    if "," not in s:
        s = re.sub(r"\s{2,}", ",", s)
    items = [normalize_text(p) for p in s.split(",") if normalize_text(p)]
    return set(items)

def overlap_count(set_a: set, set_b: set) -> int:
    """סופרת התאמות 'חכמות': שוויון או הכלה (תת-מחרוזת >= 3 תווים)."""
    cnt = 0
    for a in set_a:
        for b in set_b:
            if not a or not b: 
                continue
            if a == b:
                cnt += 1
            else:
                # התאמת הכלה – אם אחד כולל את השני (מחרוזות מספיק 'ארוכות')
                if (len(a) >= 3 and a in b) or (len(b) >= 3 and b in a):
                    cnt += 1
    return cnt

def bytes_for_download(df, filename):
    bio = BytesIO()
    df.to_csv(bio, index=False, encoding="utf-8-sig")
    bio.seek(0)
    return bio, filename

# =========================
# משקולות
# =========================
W_DOMAIN_MAIN  = 2.0   # תחום מועדף ↔ תחום ההתמחות (פגיעה אחת לפחות)
W_DOMAIN_MULTI = 1.0   # חפיפה לכל ערך תואם (כולל הכלה)
W_CITY         = 1.2   # עיר (נירמול)

# =========================
# Sidebar – העלאות
# =========================
with st.sidebar:
    st.header("העלאת נתונים")
    up_students = st.file_uploader("סטודנטים – student_form_example_5.csv", type=["csv"])
    up_sites    = st.file_uploader("אתרים/מדריכים – example_assignment_result_5.csv", type=["csv"])

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
  <p>הציון מחושב על בסיס חפיפה חכמה בין <b>תחומי הסטודנט/ית</b> ל<b>תחום ההתמחות באתר</b>, התאמת <b>עיר מגורים</b> ל<b>עיר האתר</b>, ואז שיבוץ לפי <b>קיבולת</b>.</p>
</div>
""",
    unsafe_allow_html=True
)

c1, c2 = st.columns([1.2, 1])
with c1:
    st.markdown("### שלבי עבודה")
    st.markdown("- העלאת שני הקבצים (או טעינה אוטומטית).")
    st.markdown("- בדיקת הנתונים (לשונית נתונים).")
    st.markdown("- הרצת שיבוץ (לשונית שיבוץ).")
    st.markdown("- הורדה/שמירה (לשונית ייצוא).")
with c2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="metric"><span class="label">סטודנטים נטענו</span><span class="value">{0 if students_raw is None else len(students_raw)}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric"><span class="label">רשומות אתרים נטענו</span><span class="value">{0 if sites_raw is None else len(sites_raw)}</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# =========================
# Tabs
# =========================
tab1, tab3, tab4 = st.tabs(["📥 נתונים", "🧩 שיבוץ", "📤 ייצוא"])

# =========================
# לשונית נתונים
# =========================
with tab1:
    st.info(
        "**סטודנטים**: `שם פרטי`, `שם משפחה`, `עיר מגורים`, `תחומים מבוקשים`, `תחום מועדף`  \n"
        "**אתרים**: `מוסד / שירות הכשרה` (שם האתר), `תחום ההתמחות`, `עיר`, `מספר סטודנטים שניתן לקלוט השנה` (קיבולת)",
        icon="ℹ️"
    )

    if students_raw is None or sites_raw is None:
        st.warning("יש להעלות/לספק את שני הקבצים.", icon="⚠️")
    else:
        cA, cB = st.columns(2)
        with cA:
            with st.expander("סטודנטים – הצגה מקוצרת (Raw)", expanded=False):
                st.dataframe(students_raw, use_container_width=True, height=320)
                st.caption(f"לא ריקים: תחום מועדף: {(students_raw['תחום מועדף'].notna() & (students_raw['תחום מועדף'].astype(str).str.strip()!='')).sum()} / {len(students_raw)}")
        with cB:
            with st.expander("אתרים/מדריכים – הצגה מקוצרת (Raw)", expanded=False):
                st.dataframe(sites_raw, use_container_width=True, height=320)
                st.caption(f"לא ריקים: תחום ההתמחות: {(sites_raw['תחום ההתמחות'].notna() & (sites_raw['תחום ההתמחות'].astype(str).str.strip()!='')).sum()} / {len(sites_raw)}")

# =========================
# לשונית שיבוץ
# =========================
with tab3:
    if students_raw is None or sites_raw is None:
        st.warning("חסרים נתונים. העלי את שני הקבצים בלשונית הראשונה.", icon="⚠️")
    else:
        # שמות העמודות כפי שהוגדרו בטפסים
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

        # הכנה – סטודנטים
        stu  = students_raw.copy()
        stu["student_id"] = [f"S{i+1:03d}" for i in range(len(stu))]
        stu["student_name"] = (stu[STU_FIRST].astype(str).fillna("") + " " + stu[STU_LAST].astype(str).fillna("")).str.strip()

        # הכנה – אתרים: קיבולת + אגרגציה לאיחוד כפילויות
        site = sites_raw.copy()
        site["capacity"] = pd.to_numeric(site[SITE_CAP], errors="coerce").fillna(1).astype(int).clip(lower=0)
        site = site[site["capacity"] > 0]

        def union_domains(series) -> str:
            """איחוד תחומים מכל השורות של אותו אתר (סט ערכים מנורמלים)."""
            acc = set()
            for v in series.dropna():
                acc |= split_multi(v)
            return ", ".join(sorted(acc)) if acc else ""

        def first_non_empty(series) -> str:
            for v in series:
                if _strip(v): 
                    return v
            return ""

        # אגרגציה לפי שם אתר: עיר לא ריקה ראשונה + איחוד תחומים
        sites_agg = site.groupby(SITE_NAME, as_index=False).agg({
            SITE_CITY: first_non_empty,
            SITE_DOMAIN: union_domains
        })
        # קיבולת לכל אתר כסכום
        site_capacity = site.groupby(SITE_NAME)["capacity"].sum().to_dict()

        # פונקציית ציון התאמה (עם נירמול והכלה)
        def match_score(stu_row, site_row):
            score = 0.0

            pref_set    = split_multi(stu_row.get(STU_PREFDOM, ""))
            dom_site    = split_multi(site_row.get(SITE_DOMAIN, ""))  # כבר מאוחד ומנורמל
            # אם dom_site יצא ריק לגמרי – ננסה גם נירמול גס על הטקסט הגולמי
            if not dom_site and site_row.get(SITE_DOMAIN, ""):
                dom_site = { normalize_text(site_row.get(SITE_DOMAIN, "")) }

            # 1) תחום מועדף ↔ תחום ההתמחות
            if pref_set and dom_site:
                c1 = overlap_count(pref_set, dom_site)
                if c1 > 0:
                    score += W_DOMAIN_MAIN + W_DOMAIN_MULTI * (c1 - 1 if c1 > 1 else 0)

            # 2) תחומים מבוקשים ↔ תחום ההתמחות
            all_set = split_multi(stu_row.get(STU_DOMS, ""))
            if all_set and dom_site:
                c2 = overlap_count(all_set, dom_site)
                if c2 > 0:
                    score += W_DOMAIN_MULTI * c2

            # 3) עיר (נירמול)
            stu_city  = normalize_text(stu_row.get(STU_CITY, ""))
            site_city = normalize_text(site_row.get(SITE_CITY, ""))
            if stu_city and site_city and (stu_city == site_city or stu_city in site_city or site_city in stu_city):
                score += W_CITY

            return score

        # טבלת ציונים לכל צמד
        rows = []
        for _, s in stu.iterrows():
            for _, t in sites_agg.iterrows():
                rows.append((
                    s["student_id"], s["student_name"],
                    _strip(t.get(SITE_NAME, "")),
                    match_score(s, t)
                ))
        scores = pd.DataFrame(rows, columns=["student_id","student_name","site_name","score"])

        # TOP-3 לכל סטודנט
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
                    chosen, chosen_score = site_nm, float(r["score"])
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
        bio = BytesIO(); out.to_csv(bio, index=False, encoding="utf-8-sig"); bio.seek(0)
        st.download_button("⬇️ הורדת CSV", bio, file_name=fname, mime="text/csv", use_container_width=True)

        if st.checkbox("שמור גם בשם הקבוע assignments.csv"):
            try:
                out.to_csv(DEFAULT_ASSIGN, index=False, encoding="utf-8-sig")
                st.success("נשמר assignments.csv בתיקיית האפליקציה.")
            except Exception as e:
                st.error(f"שגיאת שמירה: {e}")
    else:
        st.info("אין עדיין תוצאות – הריצי שיבוץ בלשונית \"🧩 שיבוץ\".")
