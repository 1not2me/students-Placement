# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import re, json, io
from datetime import datetime

# =========================
# הגדרות כלליות + עיצוב
# =========================
st.set_page_config(page_title="מערכת שיבוץ – ממשק מנהלים", layout="wide")

st.markdown("""
<style>
:root{ --ink:#0f172a; --ring:rgba(155,93,229,.35); --primary:#9b5de5; --primary-700:#f15bb5; }
.stApp, .main { direction:rtl; text-align:right; }
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 15% 10%, #ede7f6 0%, transparent 70%),
    radial-gradient(900px 500px at 50% 80%, #fce4ec 0%, transparent 70%),
    radial-gradient(700px 400px at 10% 85%, #e8f5e9 0%, transparent 70%),
    linear-gradient(135deg, #e0f7fa 0%, #ffffff 100%) !important;
}
.main .block-container{
  background: rgba(255,255,255,.78);
  backdrop-filter: blur(10px);
  border:1px solid rgba(15,23,42,.08);
  box-shadow:0 15px 35px rgba(15,23,42,.08);
  border-radius:24px;
  padding:1.5rem 1.5rem 2rem;
}
.stTabs [data-baseweb="tab"]{
  border-radius:14px!important; background:rgba(255,255,255,.7);
  margin-inline-start:.5rem; padding:.5rem 1rem; font-weight:600;
}
.stTabs [data-baseweb="tab"]:hover{ background:rgba(255,255,255,.95); }
.stButton > button{
  background:linear-gradient(135deg,var(--primary) 0%,var(--primary-700) 100%)!important;
  color:#fff!important;border:none!important;border-radius:14px!important;
  padding:.6rem 1.1rem!important;font-weight:600!important;box-shadow:0 6px 16px var(--ring)!important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# אימות מנהל
# =========================
# אם לא הוגדר ב-secrets, תהיה סיסמת ברירת-מחדל "admin123"
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")

st.title("🧭 מערכת שיבוץ – ממשק מנהלים")
with st.expander("🔐 כניסת מנהל", expanded=True):
    pwd = st.text_input("סיסמה", type="password", value="")
    if pwd != ADMIN_PASSWORD:
        st.info("הכניסו סיסמה. (ברירת-מחדל לדמו: **admin123**) – מומלץ לשים ADMIN_PASSWORD ב-Secrets")
        st.stop()

# =========================
# עוזרי טקסט וניקוי
# =========================
def norm(x):
    if pd.isna(x): return ""
    s = str(x).strip().lower()
    s = re.sub(r"[^\w\u0590-\u05FF\s,;:/\-]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def split_multi(val):
    s = norm(val)
    if not s: return []
    parts = re.split(r"[;,/|]+|\s{2,}", s)
    return [p.strip() for p in parts if p.strip()]

def rank_to_score(rank, max_rank=10):
    if pd.isna(rank): return 0.0
    try:
        r = int(rank)
        if r<=0: return 0.0
        return (max_rank - r + 1)
    except:
        return 0.0

# =========================
# קריאת קבצים בטוחה (CSV/Excel)
# =========================
def read_any(upload):
    """קורא CSV/Excel. אם חסר openpyxl – מודיע ומחזיר None עבור Excel."""
    if upload is None:
        return None
    name = upload.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(upload, encoding="utf-8-sig")
    if name.endswith(".xlsx"):
        try:
            # pandas יבחר openpyxl; אם לא מותקן – נתפוס ונסביר
            return pd.read_excel(upload)
        except ImportError as e:
            st.error("נדרש המודול **openpyxl** לקריאת Excel בענן. "
                     "העלו CSV או הוסיפו `openpyxl` ל-requirements.txt (מצורף בהמשך).")
            return None
        except Exception as e:
            st.error(f"שגיאה בקריאת Excel: {e}")
            return None
    st.error("סוג קובץ לא נתמך. השתמשו ב-CSV או Excel (xlsx).")
    return None

# =========================
# העלאת נתונים
# =========================
st.header("1) נתונים")
c1,c2 = st.columns(2)
with c1:
    stu_file = st.file_uploader("טעינת קובץ סטודנטים (CSV/Excel)", type=["csv","xlsx"], key="stu")
with c2:
    site_file = st.file_uploader("טעינת קובץ אתרים/מדריכים (CSV/Excel)", type=["csv","xlsx"], key="site")

students_df = read_any(stu_file)
sites_df     = read_any(site_file)

if students_df is not None:
    st.success(f"סטודנטים נטענו ({len(students_df):,}).")
    with st.expander("תצוגה מהירה – סטודנטים"):
        st.dataframe(students_df.head(50), use_container_width=True)
if sites_df is not None:
    st.success(f"אֲתָרִים/מדריכים נטענו ({len(sites_df):,}).")
    with st.expander("תצוגה מהירה – אתרים/מדריכים"):
        st.dataframe(sites_df.head(50), use_container_width=True)

if students_df is None or sites_df is None:
    st.stop()

# =========================
# מיפוי עמודות
# =========================
st.header("2) מיפוי עמודות")
sc1, sc2 = st.columns(2)

with sc1:
    st.subheader("סטודנטים")
    stu_cols = students_df.columns.tolist()
    m_stu = {}
    m_stu["id"]         = st.selectbox("מזהה/ת״ז סטודנט", stu_cols, index=0)
    m_stu["first"]      = st.selectbox("שם פרטי", stu_cols, index=min(1,len(stu_cols)-1))
    m_stu["last"]       = st.selectbox("שם משפחה", stu_cols, index=min(2,len(stu_cols)-1))
    m_stu["city"]       = st.selectbox("עיר/יישוב סטודנט (לא חובה)", ["— אין —"]+stu_cols, index=0)
    m_stu["top_domain"] = st.selectbox("תחום מוביל", stu_cols)
    m_stu["domains"]    = st.selectbox("רשימת תחומים (מופרד בפסיקים/נקודה פסיק)", ["— אין —"]+stu_cols, index=0)
    m_stu["score_col"]  = st.selectbox("מדד עדיפות/ממוצע (אופציונלי)", ["— אין —"]+stu_cols, index=0)
    rank_candidates = [c for c in stu_cols if norm(c).startswith("rank")]
    rank_hint = st.multiselect("עמודות דירוג אתרים (מומלץ: rank_שם_אתר)", rank_candidates, default=rank_candidates)

with sc2:
    st.subheader("אתרים/מדריכים")
    site_cols = sites_df.columns.tolist()
    m_site = {}
    m_site["id"]      = st.selectbox("מזהה אתר", site_cols, index=0)
    m_site["name"]    = st.selectbox("שם אתר", site_cols, index=min(1,len(site_cols)-1))
    m_site["city"]    = st.selectbox("עיר/יישוב אתר (לא חובה)", ["— אין —"]+site_cols, index=0)
    m_site["domains"] = st.selectbox("תחום/תחומים של האתר", site_cols)
    m_site["cap"]     = st.selectbox("קיבולת (מספר סטודנטים)", site_cols)
    m_site["mentor"]  = st.selectbox("שם מדריך (לא חובה)", ["— אין —"]+site_cols, index=0)

# DataFrames מנורמלים
stu = students_df.copy()
stu["_id"]   = stu[m_stu["id"]].astype(str)
stu["_first"]= stu[m_stu["first"]].astype(str)
stu["_last"] = stu[m_stu["last"]].astype(str)
stu["_city"] = "" if m_stu["city"]=="— אין —" else stu[m_stu["city"]].astype(str)
stu["_top"]  = stu[m_stu["top_domain"]].astype(str)
stu["_domains"] = "" if m_stu["domains"]=="— אין —" else stu[m_stu["domains"]].astype(str)
stu["_prio"] = 0.0
if m_stu["score_col"]!="— אין —":
    with pd.option_context('mode.use_inf_as_na', True):
        stu["_prio"] = pd.to_numeric(stu[m_stu["score_col"]], errors="coerce").fillna(0.0)

site = sites_df.copy()
site["_sid"]   = site[m_site["id"]].astype(str)
site["_sname"] = site[m_site["name"]].astype(str)
site["_city"]  = "" if m_site["city"]=="— אין —" else site[m_site["city"]].astype(str)
site["_domains"]= site[m_site["domains"]].astype(str)
site["_cap"]   = pd.to_numeric(site[m_site["cap"]], errors="coerce").fillna(0).astype(int)
site["_mentor"]= "" if m_site["mentor"]=="— אין —" else site[m_site["mentor"]].astype(str)

rank_map_cols = {}
for col in rank_hint:
    rank_map_cols[norm(col).replace("rank","rank").strip()] = col

# =========================
# משקולות וחוקים
# =========================
st.header("3) משקולות וחוקים")
wcol1,wcol2,wcol3 = st.columns(3)
with wcol1:
    W_DOMAIN_MATCH     = st.slider("משקל חפיפת תחומים", 0.0, 10.0, 5.0, 0.5)
    W_TOP_DOMAIN_BONUS = st.slider("בונוס תחום מוביל", 0.0, 10.0, 3.0, 0.5)
with wcol2:
    W_RANK_SITE        = st.slider("משקל דירוג אתרים (rank_*)", 0.0, 10.0, 4.0, 0.5)
    MAX_RANK_VAL       = st.slider("ערך דירוג מקס׳ (למשל 10)", 5, 20, 10, 1)
with wcol3:
    W_STUDENT_PRIORITY = st.slider("משקל עדיפות/ממוצע סטודנט", 0.0, 10.0, 2.0, 0.5)
    RANDOM_SEED        = st.number_input("Seed לשחזור", min_value=0, value=42, step=1)

st.caption("האלגוריתם: חישוב ציון לכל צמד סטודנט×אתר → מיון יורד → גרידי עם קיבולות.")

# =========================
# ניקוד לכל צמד
# =========================
def site_rank_for_student(row, sname):
    if not rank_map_cols: return 0.0
    key = "rank_" + norm(sname).replace(" ", "_")
    for k, col in rank_map_cols.items():
        if key in k:
            return rank_to_score(row.get(col, np.nan), MAX_RANK_VAL)
    for k, col in rank_map_cols.items():
        if norm(sname) in k:
            return rank_to_score(row.get(col, np.nan), MAX_RANK_VAL)
    return 0.0

def compute_scores(stu_df: pd.DataFrame, site_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, s in stu_df.iterrows():
        s_domains = set(split_multi(s["_domains"])) | set(split_multi(s["_top"]))
        s_top     = norm(s["_top"])
        for _, t in site_df.iterrows():
            t_domains = set(split_multi(t["_domains"]))
            inter = len(s_domains & t_domains)
            union = max(1, len(s_domains | t_domains))
            domain_score = (inter/union) * W_DOMAIN_MATCH if union>0 else 0.0
            top_bonus    = W_TOP_DOMAIN_BONUS if s_top and (s_top in t_domains) else 0.0
            rank_score   = site_rank_for_student(s, t["_sname"]) * (W_RANK_SITE/10.0)
            prio_score   = float(s["_prio"]) * (W_STUDENT_PRIORITY/10.0)

            total = domain_score + top_bonus + rank_score + prio_score
            rows.append({
                "student_id": s["_id"],
                "student_name": f'{s["_first"]} {s["_last"]}',
                "site_id": t["_sid"],
                "site_name": t["_sname"],
                "mentor": t["_mentor"],
                "score": round(total, 5),
                "domain_score": round(domain_score, 4),
                "top_bonus": round(top_bonus, 4),
                "rank_score": round(rank_score, 4),
                "prio_score": round(prio_score, 4),
                "student_prio_raw": s["_prio"],
            })
    return pd.DataFrame(rows)

# =========================
# שיבוץ גרידי
# =========================
def greedy_assign(scores: pd.DataFrame, site_caps: pd.Series, seed: int = 42):
    rnd = np.random.RandomState(seed)
    scores = scores.copy()
    scores["tie"] = rnd.rand(len(scores))
    scores = scores.sort_values(by=["score","student_prio_raw","tie"], ascending=[False,False,True])

    assigned = {}
    used_caps = {sid:int(site_caps.get(sid,0)) for sid in site_caps.index}
    taken_students = set()
    steps = []

    for _, r in scores.iterrows():
        sid = r["site_id"]
        stid = r["student_id"]
        if stid in taken_students: 
            continue
        if used_caps.get(sid,0) <= 0:
            continue
        taken_students.add(stid)
        used_caps[sid] -= 1
        assigned.setdefault(sid, []).append(r)
        steps.append({
            "student_id": stid,
            "student_name": r["student_name"],
            "site_id": sid,
            "site_name": r["site_name"],
            "mentor": r["mentor"],
            "score": r["score"]
        })

    asg_rows = []
    for sid, items in assigned.items():
        for r in items:
            asg_rows.append(r)
    asg = pd.DataFrame(asg_rows)
    log = pd.DataFrame(steps)
    return asg, log, used_caps

# =========================
# ריצה
# =========================
st.header("4) הרצה")
if st.button("🚀 חשב ניקוד ושבץ"):
    with st.spinner("מחשב ניקודים…"):
        scores_df = compute_scores(stu, site)
    st.success(f"נוצרו {len(scores_df):,} צמדי סטודנט×אתר.")
    with st.expander("🔎 פירוט ניקוד (דגימה)", expanded=False):
        st.dataframe(scores_df.sample(min(500, len(scores_df))), use_container_width=True)

    with st.spinner("מריץ שיבוץ גרידי…"):
        caps = site.set_index("_sid")["_cap"]
        asg, log, left_caps = greedy_assign(scores_df, caps, seed=int(RANDOM_SEED))

    st.success(f"שובצו {asg['student_id'].nunique():,} סטודנטים ב-{asg['site_id'].nunique():,} אתרים.")

    # טבלת שיבוץ
    st.subheader("📋 תוצאות שיבוץ")
    out = asg[["student_id","student_name","site_id","site_name","mentor","score"]].copy()

    # כל הסטודנטים – גם מי שלא שובץ
    not_asg = set(stu["_id"]) - set(out["student_id"])
    if not_asg:
        add = pd.DataFrame({
            "student_id": list(not_asg),
            "student_name": [
                (stu.loc[stu["_id"]==sid, "_first"].astype(str).str.cat(
                 stu.loc[stu["_id"]==sid, "_last"].astype(str), sep=" ").iloc[0]
                 if (stu["_id"]==sid).any() else "")
                for sid in not_asg
            ],
            "site_id": [""]*len(not_asg),
            "site_name": ["(טרם שובץ)"]*len(not_asg),
            "mentor": ["" for _ in not_asg],
            "score": [0.0 for _ in not_asg],
        })
        out = pd.concat([out, add], ignore_index=True)

    st.dataframe(out.sort_values(["site_name","student_name"]), use_container_width=True, height=420)

    # הורדות
    st.subheader("⬇️ הורדה")
    st.download_button("📥 הורדת שיבוצים (CSV)",
                       data=out.to_csv(index=False, encoding="utf-8-sig"),
                       file_name="assignments.csv", mime="text/csv")

    xls_buf = io.BytesIO()
    with pd.ExcelWriter(xls_buf, engine="xlsxwriter") as w:
        out.to_excel(w, sheet_name="assignments", index=False)
        scores_df.head(5000).to_excel(w, sheet_name="scores_sample", index=False)
        log.to_excel(w, sheet_name="log", index=False)
    xls_buf.seek(0)
    st.download_button("📥 הורדת חבילה (Excel)",
                       data=xls_buf.getvalue(),
                       file_name=f"placements_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # קונפיג לשחזור
    st.subheader("🧩 קונפיג")
    config = {
        "student_mapping": m_stu, "site_mapping": m_site,
        "weights": {
            "W_DOMAIN_MATCH": W_DOMAIN_MATCH,
            "W_TOP_DOMAIN_BONUS": W_TOP_DOMAIN_BONUS,
            "W_RANK_SITE": W_RANK_SITE,
            "MAX_RANK_VAL": MAX_RANK_VAL,
            "W_STUDENT_PRIORITY": W_STUDENT_PRIORITY,
            "RANDOM_SEED": int(RANDOM_SEED),
        },
        "rank_map_cols": rank_map_cols,
        "timestamp": datetime.now().isoformat()
    }
    st.download_button("🔒 הורדת קובץ קונפיג (JSON)",
                       data=json.dumps(config, ensure_ascii=False, indent=2),
                       file_name="placement_config.json", mime="application/json")
else:
    st.info("טענו קבצים, מיפו עמודות, הגדירו משקולות ולחצו על **🚀 חשב ניקוד ושבץ**.")
