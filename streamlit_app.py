# streamlit_app.py
# ---------------------------------------------------------
# שיבוץ סטודנטים לפי "מי-מתאים-ל" בין שני מקורות:
# 1) example_assignment_result_5.csv  -> טבלת אתרים/מדריכים (+קיבולת/מאפיינים)
# 2) student_form_example_5.csv       -> טבלת סטודנטים (+העדפות/מאפיינים)
#
# UI למיפוי עמודות, חישוב ציון התאמה, ושיבוץ Greedy מוגבל קיבולת.
# ---------------------------------------------------------

import streamlit as st
import pandas as pd
from pathlib import Path
from io import BytesIO
from datetime import datetime
import re

# =========================
# הגדרות כלליות + RTL/עיצוב
# =========================
st.set_page_config(page_title="שיבוץ סטודנטים – מי-מתאים-ל", layout="wide")

st.markdown("""
<style>
:root{ --ink:#0f172a; --muted:#475569; --ring:rgba(99,102,241,.25); --card:rgba(255,255,255,.85); }
html, body, [class*="css"] { font-family: system-ui, "Segoe UI", Arial; }
.stApp, .main, [data-testid="stSidebar"]{ direction:rtl; text-align:right; }
[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 8% 8%, #e0f7fa 0%, transparent 65%),
    radial-gradient(1000px 500px at 92% 12%, #ede7f6 0%, transparent 60%),
    radial-gradient(900px 500px at 20% 90%, #fff3e0 0%, transparent 55%);
}
.block-container{ padding-top: 1.1rem; }
.kpi{ background:var(--card); border:1px solid #e2e8f0; padding:14px; border-radius:16px; }
hr{ border-color:#e2e8f0; }
</style>
""", unsafe_allow_html=True)

# =========================
# קבצי ברירת מחדל (אם קיימים בתקייה)
# =========================
DEFAULT_STUDENTS = Path("./student_form_example_5.csv")
DEFAULT_SITES    = Path("./example_assignment_result_5.csv")
DEFAULT_ASSIGN   = Path("./assignments.csv")

# =========================
# עזרי קריאה וניקוי
# =========================
def read_csv_flexible(path_or_upload):
    """קורא CSV עם ניסיון חוזר ל-utf-8-sig בעת צורך."""
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

def _strip(s):
    if pd.isna(s): return ""
    return str(s).strip()

def _lc(s):
    return _strip(s).lower()

def _split_multi(x):
    """
    מפצל ערכים מרובים למבנה set:
    מזהה פסיקים/נקודה-פסיק/קו נטוי/רווחים מרובים ומנקה.
    """
    if pd.isna(x): return set()
    s = str(x)
    s = re.sub(r"[;/\|]", ",", s)
    if "," not in s:
        s = re.sub(r"\s{2,}", ",", s)
    return set(p.strip().lower() for p in s.split(",") if p.strip())

def get_pref_list_from_students(df, pref_cols=None, single_col=None):
    """
    מפיק רשימת העדפות מהסטודנטים:
    - או Pref1/Pref2/Pref3...
    - או עמודה אחת "העדפות"/"preferences" מופרדת בפסיקים
    """
    prefs_all = []
    if single_col:
        for val in df[single_col].fillna("").astype(str):
            prefs_all.append([p.strip() for p in val.split(",") if p.strip()])
        return prefs_all

    # Pref1..Pref10 (עד כמות גבוהה)
    cols = pref_cols or [c for c in df.columns if re.match(r'(?i)(pref|העדפ)[\s_]*\d+', str(c))]
    # מיון מספרי
    def _k(c):
        m = re.search(r'(\d+)', str(c))
        return int(m.group(1)) if m else 999
    cols = sorted(cols, key=_k)

    if cols:
        for _, row in df[cols].iterrows():
            prefs_all.append([_strip(x) for x in row.tolist() if _strip(x)])
        return prefs_all
    else:
        return [[] for _ in range(len(df))]

def df_to_csv_bytes(df, filename):
    buff = BytesIO()
    df.to_csv(buff, index=False, encoding="utf-8-sig")
    buff.seek(0)
    return buff, filename

# =========================
# סיידבר – העלאה והגדרות
# =========================
with st.sidebar:
    st.header("העלאת נתונים")
    st.caption("המערכת מיועדת לשני קבצים: אתרים/מדריכים + סטודנטים")

    up_sites = st.file_uploader("אתרים/מדריכים – example_assignment_result_5.csv", type=["csv"])
    up_students = st.file_uploader("סטודנטים – student_form_example_5.csv", type=["csv"])

    st.divider()
    st.subheader("משקלות התאמה")
    w_exact = st.number_input("משקל התאמה מדויקת (עמודה=עמודה)", min_value=0.0, max_value=10.0, value=1.0, step=0.1)
    w_overlap = st.number_input("משקל חפיפה ברשימות (Multi-value)", min_value=0.0, max_value=10.0, value=0.8, step=0.1)
    w_pref1 = st.number_input("בונוס העדפה 1", min_value=0.0, max_value=10.0, value=2.0, step=0.1)
    w_pref2 = st.number_input("בונוס העדפה 2", min_value=0.0, max_value=10.0, value=1.5, step=0.1)
    w_pref3 = st.number_input("בונוס העדפה 3", min_value=0.0, max_value=10.0, value=1.0, step=0.1)
    w_pref_other = st.number_input("בונוס העדפות 4+", min_value=0.0, max_value=10.0, value=0.7, step=0.1)

# קריאה בפועל
sites_df = read_csv_flexible(up_sites) if up_sites else (read_csv_flexible(DEFAULT_SITES) if DEFAULT_SITES.exists() else None)
students_df = read_csv_flexible(up_students) if up_students else (read_csv_flexible(DEFAULT_STUDENTS) if DEFAULT_STUDENTS.exists() else None)

# =========================
# כותרת וסטטוס
# =========================
c1, c2 = st.columns([1.2, 1])
with c1:
    st.title("🧮 שיבוץ סטודנטים – מי-מתאים-ל")
    st.write("שיבוץ Greedy לפי ציון התאמה בין מאפייני סטודנט לדרישות/מאפייני אתר, כולל העדפות ו-Capacity.")
with c2:
    with st.container(border=True):
        st.markdown('<div class="kpi">', unsafe_allow_html=True)
        st.subheader("סטטוס נתונים")
        st.write(f"סטודנטים: **{0 if students_df is None else len(students_df)}**")
        st.write(f"אתרים/מדריכים: **{0 if sites_df is None else len(sites_df)}**")
        st.markdown("</div>", unsafe_allow_html=True)

st.divider()
tab_data, tab_mapping, tab_match, tab_export = st.tabs(["📥 נתונים", "🗺️ מיפוי עמודות", "🧩 שיבוץ", "📤 ייצוא"])

# =========================
# לשונית נתונים (Raw)
# =========================
with tab_data:
    if students_df is None or sites_df is None:
        st.warning("יש להעלות שני הקבצים: example_assignment_result_5.csv + student_form_example_5.csv", icon="⚠️")
    else:
        cA, cB = st.columns(2)
        with cA:
            st.markdown("**סטודנטים (Raw):**")
            st.dataframe(students_df, use_container_width=True, height=360)
        with cB:
            st.markdown("**אתרים/מדריכים (Raw):**")
            st.dataframe(sites_df, use_container_width=True, height=360)
        st.info("עברי ללשונית ״🗺️ מיפוי עמודות״ כדי לקבוע מזהים/שמות/Capacity ושדות התאמה.", icon="ℹ️")

# =========================
# לשונית מיפוי עמודות
# =========================
with tab_mapping:
    if students_df is None or sites_df is None:
        st.warning("חסרים נתונים. העלי את שני הקבצים.", icon="⚠️")
    else:
        st.subheader("מיפוי עמודות – סטודנטים")
        s_cols = list(students_df.columns)
        stu_id_col = st.selectbox("עמודת מזהה סטודנט", s_cols, index=next((i for i,c in enumerate(s_cols) if c.lower() in ["student_id","id","תז","מספר סטודנט"]), 0))
        stu_name_col = st.selectbox("עמודת שם סטודנט", s_cols, index=next((i for i,c in enumerate(s_cols) if c.lower() in ["student_name","name","שם","שם סטודנט","full name","full_name"]), min(1,len(s_cols)-1)))
        # העדפות: או Pref1/Pref2/... או עמודה אחת עם רשימה
        single_pref_candidates = [c for c in s_cols if _lc(c) in ["העדפות","preferences","prefs","עדפות"]]
        has_single_pref = st.toggle("יש עמודה אחת של העדפות (מופרד בפסיקים)?", value=len(single_pref_candidates)>0)
        if has_single_pref:
            stu_pref_single = st.selectbox("עמודת העדפות (פסיקים)", s_cols, index=s_cols.index(single_pref_candidates[0]) if single_pref_candidates else 0)
            stu_pref_cols = []
        else:
            stu_pref_cols = st.multiselect("עמודות העדפות (Pref1/Pref2/...)", s_cols, default=[c for c in s_cols if re.match(r'(?i)(pref|העדפ)[\s_]*\d+', c)])
            stu_pref_single = None

        st.divider()
        st.subheader("מיפוי עמודות – אתרים/מדריכים")
        t_cols = list(sites_df.columns)
        # שם אתר + Capacity
        # ננסה לאתר שם אתר
        default_site_name = next((c for c in t_cols if _lc(c) in ["site_name","site","שם אתר","מוסד","מדריך","שם","organization","org","place"]), t_cols[0])
        site_name_col = st.selectbox("עמודת שם אתר/מדריך", t_cols, index=t_cols.index(default_site_name))
        default_cap = next((c for c in t_cols if _lc(c) in ["capacity","cap","קיבולת","מספר מקומות","מקומות","מס' מקומות","כמות"]), None)
        if default_cap is None:
            st.info("לא זוהתה עמודת קיבולת – נניח Capacity=1 לכל אתר.", icon="ℹ️")
            site_cap_col = None
        else:
            site_cap_col = st.selectbox("עמודת Capacity (קיבולת)", t_cols, index=t_cols.index(default_cap))

        st.divider()
        st.subheader("שדות התאמה (מי-מתאים-ל)")
        st.caption("בחרי זוגות שדות להשוואה בין סטודנט לאתר. למשל: עיר↔עיר, תחום↔תחום, שפה↔שפה, ימי זמינות↔ימים, וכו'. "
                   "ניתן לבחור שדות זהים בשם או שונים – המערכת תחשב התאמה מדויקת/חלקית.")

        # הצעה אוטומטית לפי חיתוך שמות
        auto_pairs = []
        for sc in s_cols:
            if sc == stu_id_col or sc == stu_name_col: continue
            if sc in t_cols:
                auto_pairs.append((sc, sc))

        # UI: טבלה “סטודנטים” ↔ “אתרים”
        pair_count = st.number_input("כמה זוגות שדות תרצי למפות?", min_value=0, max_value=20, value=min(3,len(auto_pairs)), step=1)
        match_pairs = []
        for i in range(int(pair_count)):
            c1, c2 = st.columns(2)
            with c1:
                left = st.selectbox(f"שדה סטודנט #{i+1}", s_cols, index=(s_cols.index(auto_pairs[i][0]) if i < len(auto_pairs) else 0), key=f"stu_field_{i}")
            with c2:
                right = st.selectbox(f"שדה אתר #{i+1}", t_cols, index=(t_cols.index(auto_pairs[i][1]) if i < len(auto_pairs) else 0), key=f"site_field_{i}")
            match_pairs.append((left, right))

        st.divider()
        st.subheader("אפשרויות התאמה מתקדמות")
        st.caption("סימני רשימה (פסיקים/נקודה-פסיק/קו-נטוי/רווחים מרובים) יזוהו אוטומטית כשדות Multi-Value.")
        multivalue_hint = st.checkbox("להפעיל זיהוי חפיפה רב-ערכית כברירת מחדל (מומלץ)", value=True)

# =========================
# לשונית שיבוץ
# =========================
with tab_match:
    if students_df is None or sites_df is None:
        st.warning("חסרים נתונים. העלי את שני הקבצים בלשונית הראשונה.", icon="⚠️")
    else:
        st.subheader("הרצת שיבוץ Greedy לפי ציון התאמה")
        run_btn = st.button("🚀 בצעי שיבוץ", type="primary")

        if run_btn:
            # הפקת העדפות מהסטודנטים
            prefs_list = get_pref_list_from_students(students_df,
                                                     pref_cols=stu_pref_cols if not has_single_pref else None,
                                                     single_col=stu_pref_single if has_single_pref else None)

            # בניית מבני עזר
            # קיבולת
            site_capacity = {}
            for _, r in sites_df.iterrows():
                sname = _strip(r[site_name_col])
                cap = int(pd.to_numeric(r[site_cap_col], errors="coerce").fillna(1)) if site_cap_col else 1
                site_capacity[sname] = site_capacity.get(sname, 0) + cap  # אם יש כפילויות – נסכם

            # רשימת אתרים ייחודית + טבלת תכונות האתר
            sites_unique = (sites_df.groupby(site_name_col).first()).reset_index()

            # פונקציית ציון התאמה
            def match_score(stu_row, site_row, stu_prefs):
                score = 0.0

                # 1) התאמת שדות (“מי-מתאים-ל”)
                for (s_field, t_field) in match_pairs:
                    v_s = stu_row[s_field] if s_field in stu_row else ""
                    v_t = site_row[t_field] if t_field in site_row else ""

                    if multivalue_hint or (isinstance(v_s, str) and ("," in v_s or ";" in v_s or "|" in v_s)) or (isinstance(v_t, str) and ("," in v_t or ";" in v_t or "|" in v_t)):
                        set_s = _split_multi(v_s)
                        set_t = _split_multi(v_t)
                        inter = set_s.intersection(set_t)
                        if len(set_s) > 0 and len(set_t) > 0 and len(inter) > 0:
                            score += w_overlap * len(inter)  # כל חפיפה מוסיפה משקל
                        # אפשר להוסיף נורמליזציה בעתיד (לפי גודל האוספים)
                    else:
                        if _lc(v_s) != "" and _lc(v_s) == _lc(v_t):
                            score += w_exact

                # 2) בונוס העדפות
                site_name_val = _strip(site_row[site_name_col])
                if site_name_val:
                    # מצא מיקום בהעדפות
                    pos = None
                    for idx, pref in enumerate(stu_prefs):
                        if _strip(pref) == site_name_val:
                            pos = idx
                            break
                    if pos is not None:
                        if pos == 0: score += w_pref1
                        elif pos == 1: score += w_pref2
                        elif pos == 2: score += w_pref3
                        else: score += w_pref_other

                return score

            # חישוב טבלת ציונים לכל סטודנט מול כל אתר
            scores = []
            for i, stu in students_df.iterrows():
                stu_id = _strip(stu[stu_id_col])
                stu_name = _strip(stu[stu_name_col])
                prefs = prefs_list[i] if i < len(prefs_list) else []
                for _, site in sites_unique.iterrows():
                    sname = _strip(site[site_name_col])
                    sc = match_score(stu, site, prefs)
                    scores.append((stu_id, stu_name, sname, sc))

            scores_df = pd.DataFrame(scores, columns=["student_id","student_name","site_name","score"])

            # דיאגנוסטיקה: שלושת האתרים הטובים לסטודנט
            topk = scores_df.sort_values(["student_id","score"], ascending=[True,False]).groupby("student_id").head(3)
            st.markdown("**TOP-3 התאמות לכל סטודנט (דיאגנוסטיקה):**")
            st.dataframe(topk, use_container_width=True, height=300)

            # שיבוץ Greedy לפי הציון (עם קיבולת)
            assignments = []
            # נעבוד סטודנט-סטודנט: ניקח את האתר הטוב ביותר מתוך אלו שנותרו עם קיבולת
            for stu_id, group in scores_df.groupby("student_id"):
                group_sorted = group.sort_values("score", ascending=False)
                chosen = "ללא שיבוץ"
                chosen_score = 0.0
                stu_name = group_sorted.iloc[0]["student_name"] if len(group_sorted)>0 else ""
                for _, row in group_sorted.iterrows():
                    site = row["site_name"]
                    if site_capacity.get(site,0) > 0:
                        chosen = site
                        chosen_score = row["score"]
                        site_capacity[site] -= 1
                        break
                assignments.append({
                    "student_id": stu_id,
                    "student_name": stu_name,
                    "assigned_site": chosen,
                    "match_score": chosen_score,
                    "status": "שובץ" if chosen != "ללא שיבוץ" else "ממתין"
                })

            asg_df = pd.DataFrame(assignments).sort_values("student_id")
            st.success(f"שיבוץ הושלם – שובצו {(asg_df['status']=='שובץ').sum()} סטודנטים/ות, ממתינים {(asg_df['status']=='ממתין').sum()}.")
            st.dataframe(asg_df, use_container_width=True, height=420)

            # מדדים
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("סה\"כ סטודנטים", len(asg_df))
            with c2: st.metric("שובצו", int((asg_df["status"]=="שובץ").sum()))
            with c3: st.metric("ממתינים", int((asg_df["status"]=="ממתין").sum()))

            # שמירה בזיכרון
            st.session_state["assignments_df"] = asg_df

# =========================
# לשונית ייצוא
# =========================
with tab_export:
    st.subheader("ייצוא assignments.csv")
    if isinstance(st.session_state.get("assignments_df"), pd.DataFrame):
        out = st.session_state["assignments_df"].copy()
        # סדר עמודות נוח
        cols = ["student_id","student_name","assigned_site","match_score","status"]
        out = out[[c for c in cols if c in out.columns]]

        st.dataframe(out, use_container_width=True, height=420)
        fname = f"assignments_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        buff, _ = df_to_csv_bytes(out, fname)
        st.download_button("⬇️ הורדת הקובץ", buff, file_name=fname, mime="text/csv", use_container_width=True)

        if st.checkbox("שמור גם בשם הקבוע assignments.csv"):
            try:
                out.to_csv(DEFAULT_ASSIGN, index=False, encoding="utf-8-sig")
                st.success("נשמר assignments.csv בתיקיית האפליקציה.")
            except Exception as e:
                st.error(f"שגיאה בשמירה: {e}")
    else:
        if DEFAULT_ASSIGN.exists():
            try:
                prev = pd.read_csv(DEFAULT_ASSIGN)
                st.info("נטען assignments.csv קיים (ברירת מחדל).")
                st.dataframe(prev, use_container_width=True, height=420)
                buff, _ = df_to_csv_bytes(prev, "assignments.csv")
                st.download_button("⬇️ הורדת assignments.csv", buff, file_name="assignments.csv", mime="text/csv", use_container_width=True)
            except Exception as e:
                st.error(f"שגיאה בטעינת assignments.csv: {e}")
        else:
            st.warning("אין תוצאות לשמירה/הורדה (הריצי שיבוץ בלשונית \"🧩 שיבוץ\").", icon="⚠️")
