# matcher_streamlit_beauty_rtl_v7_final.py
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from dataclasses import dataclass
from typing import Optional, Any, List

# =========================
# קונפיגורציה כללית
# =========================
st.set_page_config(page_title="מערכת שיבוץ סטודנטים – התאמה חכמה", layout="wide")

# ====== CSS – עיצוב מודרני + RTL ======
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;600&display=swap');
html, body, [class*="css"] { font-family: 'Rubik', 'David', sans-serif !important; }

:root{
  --bg-1:#e0f7fa;
  --bg-2:#ede7f6;
  --bg-3:#fff3e0;
  --bg-4:#fce4ec;
  --bg-5:#e8f5e9;
  --ink:#0f172a;
  --primary:#9b5de5;
  --primary-700:#f15bb5;
  --ring:rgba(155,93,229,.35);
}

[data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 600px at 15% 10%, var(--bg-2) 0%, transparent 70%),
    radial-gradient(1000px 700px at 85% 20%, var(--bg-3) 0%, transparent 70%),
    radial-gradient(900px 500px at 50% 80%, var(--bg-4) 0%, transparent 70%),
    radial-gradient(700px 400px at 10% 85%, var(--bg-5) 0%, transparent 70%),
    linear-gradient(135deg, var(--bg-1) 0%, #ffffff 100%) !important;
  color: var(--ink);
}

.main .block-container{
  background: rgba(255,255,255,.78);
  backdrop-filter: blur(10px);
  border:1px solid rgba(15,23,42,.08);
  box-shadow:0 15px 35px rgba(15,23,42,.08);
  border-radius:24px;
  padding:2.5rem;
  margin-top:1rem;
}

h1,h2,h3,.stMarkdown h1,.stMarkdown h2{
  text-align:center;
  font-weight:700;
  color:#222;
  margin-bottom:1rem;
}
.stButton > button{width:100% !important;}
.stApp,.main,[data-testid="stSidebar"]{ direction:rtl; text-align:right; }
</style>
""", unsafe_allow_html=True)

# ====== כותרת ======
st.markdown("<h1>מערכת שיבוץ סטודנטים – התאמה חכמה</h1>", unsafe_allow_html=True)

# ====== מודל ניקוד ======
@dataclass
class Weights:
    w_field: float = 0.50
    w_city: float = 0.05
    w_special: float = 0.45

# עמודות סטודנטים
STU_COLS = {
    "id": ["מספר תעודת זהות", "תעודת זהות", "ת\"ז", "תז"],
    "first": ["שם פרטי"],
    "last": ["שם משפחה"],
    "city": ["עיר מגורים", "עיר"],
    "phone": ["טלפון"],
    "email": ["דוא\"ל", "דוא״ל"],
    "preferred_field": ["תחום מועדף","תחומים מועדפים"],
    "special_req": ["בקשה מיוחדת"],
    "partner": ["בן/בת זוג להכשרה"]
}

# עמודות אתרים
SITE_COLS = {
    "name": ["מוסד / שירות הכשרה", "מוסד", "שם מוסד ההתמחות"],
    "field": ["תחום ההתמחות", "תחום התמחות"],
    "city": ["עיר"],
    "capacity": ["מספר סטודנטים שניתן לקלוט השנה", "קיבולת"],
    "sup_first": ["שם פרטי"],
    "sup_last": ["שם משפחה"],
}

def pick_col(df: pd.DataFrame, options: List[str]) -> Optional[str]:
    for opt in options:
        if opt in df.columns: return opt
    return None

# קריאת קבצים
def read_any(uploaded) -> pd.DataFrame:
    name = (uploaded.name or "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded, encoding="utf-8-sig")
    if name.endswith((".xlsx",".xls")):
        return pd.read_excel(uploaded)
    return pd.read_csv(uploaded, encoding="utf-8-sig")

def normalize_text(x: Any) -> str:
    if x is None: return ""
    return str(x).strip()

# סטודנטים
def resolve_students(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["stu_id"] = out[pick_col(out, STU_COLS["id"])]
    out["stu_first"] = out[pick_col(out, STU_COLS["first"])]
    out["stu_last"]  = out[pick_col(out, STU_COLS["last"])]
    out["stu_city"]  = out[pick_col(out, STU_COLS["city"])]
    out["stu_pref"]  = out[pick_col(out, STU_COLS["preferred_field"])]
    out["stu_req"]   = out[pick_col(out, STU_COLS["special_req"])]
    for c in ["stu_id","stu_first","stu_last","stu_city","stu_pref","stu_req"]:
        out[c] = out[c].apply(normalize_text)
    return out

# אתרים
def resolve_sites(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["site_name"]  = out[pick_col(out, SITE_COLS["name"])]
    out["site_field"] = out[pick_col(out, SITE_COLS["field"])]
    out["site_city"]  = out[pick_col(out, SITE_COLS["city"])]
    cap_col = pick_col(out, SITE_COLS["capacity"])
    out["site_capacity"] = pd.to_numeric(out[cap_col], errors="coerce").fillna(1).astype(int) if cap_col else 1
    out["capacity_left"] = out["site_capacity"].astype(int)
    sup_first = pick_col(out, SITE_COLS["sup_first"])
    sup_last  = pick_col(out, SITE_COLS["sup_last"])
    out["supervisor"] = ""
    if sup_first or sup_last:
        ff = out[sup_first] if sup_first else ""
        ll = out[sup_last]  if sup_last else ""
        out["supervisor"] = (ff.astype(str) + " " + ll.astype(str)).str.strip()
    for c in ["site_name","site_field","site_city","supervisor"]:
        out[c] = out[c].apply(normalize_text)
    return out

# חישוב ציון
def compute_score(stu: pd.Series, site: pd.Series, W: Weights) -> float:
    same_city = (stu.get("stu_city") and site.get("site_city") and stu.get("stu_city") == site.get("site_city"))
    field_s   = 90.0 if stu.get("stu_pref") and stu.get("stu_pref") in site.get("site_field","") else 60.0
    city_s    = 100.0 if same_city else 65.0
    special_s = 90.0 if "קרוב" in stu.get("stu_req","") and same_city else 70.0
    score = W.w_field*field_s + W.w_city*city_s + W.w_special*special_s
    return float(np.clip(score, 0, 100))

# שיבוץ
def greedy_match(students_df: pd.DataFrame, sites_df: pd.DataFrame, W: Weights) -> pd.DataFrame:
    results = []
    for _, s in students_df.iterrows():
        cand = sites_df[sites_df["capacity_left"]>0].copy()
        cand["score"] = cand.apply(lambda r: compute_score(s, r, W), axis=1)
        cand = cand.sort_values("score", ascending=False)
        if cand.empty:
            continue
        chosen = cand.iloc[0]
        idx = chosen.name
        sites_df.at[idx, "capacity_left"] -= 1
        results.append({
            "ת\"ז הסטודנט": s["stu_id"],
            "שם פרטי": s["stu_first"],
            "שם משפחה": s["stu_last"],
            "שם מקום ההתמחות": chosen["site_name"],
            "עיר המוסד": chosen.get("site_city",""),
            "תחום ההתמחות במוסד": chosen["site_field"],
            "מדריך": chosen["supervisor"],
            "אחוז התאמה": round(chosen["score"],1)
        })
    return pd.DataFrame(results)

# הורדה ל-Excel
def df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "שיבוץ") -> bytes:
    xlsx_io = BytesIO()
    with pd.ExcelWriter(xlsx_io, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    xlsx_io.seek(0)
    return xlsx_io.getvalue()

# =========================
# העלאת קבצים
# =========================
st.markdown("## 📤 העלאת קבצים")
students_file = st.file_uploader("קובץ סטודנטים", type=["csv","xlsx","xls"])
sites_file = st.file_uploader("קובץ אתרי התמחות/מדריכים", type=["csv","xlsx","xls"])

# =========================
# ביצוע שיבוץ
# =========================
# =========================
# ביצוע שיבוץ
# =========================
if st.button("🚀 בצע שיבוץ", use_container_width=True):
    if not students_file or not sites_file:
        st.error("❌ יש להעלות גם קובץ סטודנטים וגם קובץ אתרי התמחות לפני ביצוע השיבוץ")
    else:
        try:
            students = resolve_students(read_any(students_file))
            sites    = resolve_sites(read_any(sites_file))
            result_df = greedy_match(students, sites, Weights())

            if result_df.empty:
                st.warning("⚠️ לא נמצאו שיבוצים – בדוק שהקבצים מכילים נתונים מתאימים")
            else:
                # --- טבלת סיכום בלבד ---
                summary_df = (
                    result_df
                    .groupby(["שם מקום ההתמחות","תחום ההתמחות במוסד","מדריך"])
                    .agg({
                        "ת\"ז הסטודנט":"count",
                        "שם פרטי": list,
                        "שם משפחה": list
                    }).reset_index()
                )
                summary_df["המלצת שיבוץ"] = summary_df.apply(
                    lambda r: " + ".join([f"{fn} {ln}" for fn, ln in zip(r["שם פרטי"], r["שם משפחה"])]),
                    axis=1
                )
                summary_df.rename(columns={"ת\"ז הסטודנט":"כמה סטודנטים"}, inplace=True)
                summary_df = summary_df[[
                    "שם מקום ההתמחות",
                    "מדריך",
                    "כמה סטודנטים",
                    "המלצת שיבוץ",
                    "תחום ההתמחות במוסד"
                ]]

                st.success("✅ השיבוץ הושלם בהצלחה")
                st.dataframe(summary_df, use_container_width=True)

                # הורדה ל-Excel
                xlsx_summary = df_to_xlsx_bytes(summary_df, sheet_name="סיכום")
                st.download_button("⬇️ הורדת XLSX – טבלת סיכום", data=xlsx_summary,
                    file_name="student_site_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"שגיאה בשיבוץ: {e}")
