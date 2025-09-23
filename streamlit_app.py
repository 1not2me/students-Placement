# matcher_streamlit_beauty_rtl_v5.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import csv
from io import BytesIO
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

# =========================
# קונפיגורציה כללית
# =========================
st.set_page_config(page_title="מערכת שיבוץ סטודנטים – התאמה חכמה", layout="wide")

# ====== CSS – עיצוב מודרני + RTL ======
st.markdown("""<style>
/* ... שמרתי את כל ה-CSS שלך כמו שהיה ... */
</style>""", unsafe_allow_html=True)

# ====== כותרת ======
st.markdown("<h1>מערכת שיבוץ סטודנטים – התאמה חכמה</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#475569;margin-top:-8px;'>כאן משבצים סטודנטים למקומות התמחות בקלות, בהתבסס על תחום, עיר ובקשות.</p>", unsafe_allow_html=True)

# ====== מודל ניקוד ======
@dataclass
class Weights:
    w_field: float = 0.70
    w_city: float = 0.20
    w_special: float = 0.10

# ---- כל הפונקציות שלך resolve_students / resolve_sites / compute_score נשארו ללא שינוי ----

def candidate_table_for_student(stu: pd.Series, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    tmp = sites_df.copy()
    tmp["score"] = tmp.apply(lambda r: compute_score(stu, r, W), axis=1).astype(float)
    return tmp.sort_values(["score"], ascending=[False])

def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    separate_couples = True
    top_k = 10

    def dec_cap(idx: int):
        cur = pd.to_numeric(sites_df.at[idx, "capacity_left"], errors="coerce")
        cur = 0 if pd.isna(cur) else int(cur)
        sites_df.at[idx, "capacity_left"] = max(0, cur - 1)

    results: List[Tuple[pd.Series, Optional[pd.Series]]] = []
    processed = set()
    partner_map = find_partner_map(students_df)

    # זוגות
    for _, s in students_df.iterrows():
        sid = s["stu_id"]
        if sid in processed: continue
        pid = partner_map.get(sid)
        if pid and partner_map.get(pid) == sid:
            partner_row = students_df[students_df["stu_id"] == pid]
            if partner_row.empty: continue
            s2 = partner_row.iloc[0]
            cand1 = candidate_table_for_student(s,  sites_df[sites_df["capacity_left"]>0], W).head(top_k)
            cand2 = candidate_table_for_student(s2, sites_df[sites_df["capacity_left"]>0], W).head(top_k)
            best = (-1.0, None, None)
            for i1, r1 in cand1.iterrows():
                for i2, r2 in cand2.iterrows():
                    if i1 == i2: continue
                    if separate_couples and r1.get("supervisor") and r1.get("supervisor") == r2.get("supervisor"):
                        continue
                    sc = float(r1["score"]) + float(r2["score"])
                    if sc > best[0]: best = (sc, i1, i2)
            if best[1] is not None and best[2] is not None:
                rsite1 = sites_df.loc[best[1]]; rsite2 = sites_df.loc[best[2]]
                dec_cap(best[1]); dec_cap(best[2])
                results.append((s, rsite1)); results.append((s2, rsite2))
                processed.add(sid); processed.add(pid)

    # בודדים
    for _, s in students_df.iterrows():
        sid = s["stu_id"]
        if sid in processed: continue
        cand = candidate_table_for_student(s, sites_df[sites_df["capacity_left"]>0], W).head(top_k)
        if not cand.empty:
            chosen_idx = cand.index[0]
            rsite = sites_df.loc[chosen_idx]
            dec_cap(chosen_idx)
            results.append((s, rsite))
            processed.add(sid)
        else:
            results.append((s, None))
            processed.add(sid)

    # פלט
    rows = []
    for s, r in results:
        if r is None:
            rows.append({
                "ת\"ז הסטודנט": s.get("stu_id"),
                "שם פרטי": s.get("stu_first"),
                "שם משפחה": s.get("stu_last"),
                "כתובת": s.get("stu_address"),
                "עיר": s.get("stu_city"),
                "מספר טלפון": s.get("stu_phone"),
                "אימייל": s.get("stu_email"),
                "אחוז התאמה": 0.0,
                "שם מקום ההתמחות": "לא שובץ",
                "עיר המוסד": "",
                "סוג מקום השיבוץ": "",
                "תחום ההתמחות במוסד": "",
            })
        else:
            score = compute_score(s, r, W)
            rows.append({
                "ת\"ז הסטודנט": s.get("stu_id"),
                "שם פרטי": s.get("stu_first"),
                "שם משפחה": s.get("stu_last"),
                "כתובת": s.get("stu_address"),
                "עיר": s.get("stu_city"),
                "מספר טלפון": s.get("stu_phone"),
                "אימייל": s.get("stu_email"),
                "אחוז התאמה": round(score, 1),
                "שם מקום ההתמחות": r.get("site_name"),
                "עיר המוסד": r.get("site_city"),
                "סוג מקום השיבוץ": r.get("site_type"),
                "תחום ההתמחות במוסד": r.get("site_field"),
            })
    out = pd.DataFrame(rows)
    desired = ["ת\"ז הסטודנט","שם פרטי","שם משפחה","כתובת","עיר","מספר טלפון","אימייל",
               "אחוז התאמה","שם מקום ההתמחות","עיר המוסד","סוג מקום השיבוץ","תחום ההתמחות במוסד"]
    remaining = [c for c in out.columns if c not in desired]
    return out[[c for c in desired if c in out.columns] + remaining]

# ---- יצירת XLSX ו-CSV ----
def df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "שיבוץ") -> bytes:
    xlsx_io = BytesIO()
    try:
        import xlsxwriter
        engine = "xlsxwriter"
    except Exception:
        engine = "openpyxl"
    with pd.ExcelWriter(xlsx_io, engine=engine) as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    xlsx_io.seek(0)
    return xlsx_io.getvalue()

TEXT_COLS = ["ת\"ז הסטודנט", "מספר טלפון", "אימייל"]
def df_to_excel_friendly_csv_bytes(df: pd.DataFrame) -> bytes:
    df2 = df.copy()
    for c in TEXT_COLS:
        if c in df2.columns:
            df2[c] = df2[c].astype(str).apply(lambda s: "'" + s if not s.startswith("'") else s)
    return df2.to_csv(index=False, sep=";", encoding="utf-8-sig", quoting=csv.QUOTE_ALL).encode("utf-8-sig")

# =========================
# 1) הוראות שימוש
# =========================
st.markdown("## 📘 הוראות שימוש")
st.markdown("""
1. **קובץ סטודנטים (CSV/XLSX):** שם פרטי, שם משפחה, תעודת זהות, כתובת/עיר, טלפון, אימייל.  
   אופציונלי: תחום מועדף, בקשה מיוחדת, בן/בת זוג להכשרה.  
2. **קובץ אתרים/מדריכים (CSV/XLSX):** מוסד/שירות, תחום התמחות, רחוב, עיר, מספר סטודנטים שניתן לקלוט השנה.  
3. **בצע שיבוץ** מחשב *אחוז התאמה* לפי תחום (70%), עיר (20%), בקשות (10%), כולל בני/בנות זוג וקיבולת.  
4. בסוף אפשר להוריד **XLSX** או **CSV**. הכפתורים נשארים זמינים לאחר השיבוץ.
""")

# =========================
# 2) דוגמאות (אופציונלי)
# =========================
st.markdown("## 🧪 דוגמה לשימוש")
example_students = pd.DataFrame([
    {"שם פרטי":"רות", "שם משפחה":"כהן", "תעודת זהות":"123456789", "כתובת":"הרצל 12", "עיר מגורים":"תל אביב", "טלפון":"0501111111", "דוא\"ל":"ruth@example.com", "תחום מועדף":"בריאות הנפש"},
    {"שם פרטי":"יואב", "שם משפחה":"לוי", "תעודת זהות":"987654321", "כתובת":"דיזנגוף 80", "עיר מגורים":"תל אביב", "טלפון":"0502222222", "דוא\"ל":"yoav@example.com", "תחום מועדף":"רווחה"}
])
example_sites = pd.DataFrame([
    {"מוסד / שירות הכשרה":"מרכז חוסן תל אביב", "תחום ההתמחות":"בריאות הנפש", "רחוב":"אבן גבירול 1", "עיר":"תל אביב", "מספר סטודנטים שניתן לקלוט השנה":2},
    {"מוסד / שירות הכשרה":"מחלקת רווחה רמת גן", "תחום ההתמחות":"רווחה", "רחוב":"ביאליק 10", "עיר":"רמת גן", "מספר סטודנטים שניתן לקלוט השנה":1},
])
colX, colY = st.columns(2, gap="large")
with colX:
    st.write("**דוגמה – סטודנטים**")
    st.dataframe(example_students, use_container_width=True)
with colY:
    st.write("**דוגמה – אתרי התמחות/מדריכים**")
    st.dataframe(example_sites, use_container_width=True)

# =========================
# 3) העלאת קבצים
# =========================
st.markdown("## 📤 העלאת קבצים")
colA, colB = st.columns(2, gap="large")

with colA:
    students_file = st.file_uploader("קובץ סטודנטים", type=["csv","xlsx","xls"], key="students_file")
    if students_file is not None:
        st.caption("הצצה ל-5 הרשומות הראשונות (לא מוחקים שום עמודה):")
        try:
            st.session_state["df_students_raw"] = read_any(students_file)
            st.dataframe(st.session_state["df_students_raw"].head(5), use_container_width=True)
        except Exception as e:
            st.error(f"לא ניתן לקרוא את קובץ הסטודנטים: {e}")

with colB:
    sites_file = st.file_uploader("קובץ אתרי התמחות/מדריכים", type=["csv","xlsx","xls"], key="sites_file")
    if sites_file is not None:
        st.caption("הצצה ל-5 הרשומות הראשונות (לא מוחקים שום עמודה):")
        try:
            st.session_state["df_sites_raw"] = read_any(sites_file)
            st.dataframe(st.session_state["df_sites_raw"].head(5), use_container_width=True)
        except Exception as e:
            st.error(f"לא ניתן לקרוא את קובץ האתרים/מדריכים: {e}")

# אתחול session_state למפתחות חשובים
for k in ["df_students_raw","df_sites_raw","result_df","unmatched_students","unused_sites"]:
    st.session_state.setdefault(k, None)

# =========================
# 4) שיבוץ
# =========================
st.markdown("## ⚙️ ביצוע השיבוץ")
run_btn = st.button("🚀 בצע שיבוץ", use_container_width=True)

if run_btn:
    try:
        ensure_df(st.session_state["df_students_raw"], "סטודנטים")
        ensure_df(st.session_state["df_sites_raw"], "אתרים/מדריכים")
        students = resolve_students(st.session_state["df_students_raw"])
        sites    = resolve_sites(st.session_state["df_sites_raw"])
        result_df = greedy_match(students, sites, Weights())
        st.session_state["result_df"] = result_df
        st.session_state["unmatched_students"] = result_df[result_df["שם מקום ההתמחות"] == "לא שובץ"]
        used_sites = set(result_df["שם מקום ההתמחות"].unique())
        st.session_state["unused_sites"] = sites[~sites["site_name"].isin(used_sites)]
        st.success("השיבוץ הושלם ✓")
    except Exception as e:
        st.exception(e)

# =========================
# 5) תוצאות והורדות
# =========================

st.markdown("## 📊 תוצאות השיבוץ")

if isinstance(st.session_state["result_df"], pd.DataFrame) and not st.session_state["result_df"].empty:
    st.dataframe(st.session_state["result_df"], use_container_width=True)

    # --- כפתור הורדת XLSX בלבד (רחב) ---
    try:
        xlsx_bytes = df_to_xlsx_bytes(st.session_state["result_df"])
        st.download_button(
            label="⬇️ הורדת XLSX / CSV",
            data=xlsx_bytes,
            file_name="student_site_matching.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_xlsx_btn",
            help="קובץ Excel בעברית"
        )
    except Exception as e:
        st.error(f"שגיאה ביצירת Excel: {e}.")

    # --- טבלאות נוספות ---
   if isinstance(st.session_state["result_df"], pd.DataFrame) and not st.session_state["result_df"].empty:
     st.dataframe(st.session_state["result_df"], use_container_width=True)

    try:
        xlsx_bytes = df_to_xlsx_bytes(st.session_state["result_df"])
        csv_bytes  = df_to_excel_friendly_csv_bytes(st.session_state["result_df"])

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="⬇️ הורדת XLSX",
                data=xlsx_bytes,
                file_name="student_site_matching.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with col2:
            st.download_button(
                label="⬇️ הורדת CSV",
                data=csv_bytes,
                file_name="student_site_matching.csv",
                mime="text/csv",
            )
    except Exception as e:
        st.error(f"שגיאה ביצירת קובצי Excel/CSV: {e}.")
