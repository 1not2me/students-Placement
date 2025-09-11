
import streamlit as st
import pandas as pd
from datetime import datetime
import re
from io import BytesIO  # <-- for XLSX export

# ===== הגדרות =====
st.set_page_config(page_title="מיפוי מדריכים לשיבוץ סטודנטים - תשפ\"ו", layout="centered")
ADMIN_PASSWORD = "rawan_0304"
CSV_FILE = "mapping_data.csv"

# ===== עיצוב =====
st.markdown("""
<style>
/* ===== כפתור הורדת Excel (XLSX) – כמו בתמונה ===== */
.stDownloadButton > button{
  display:flex; align-items:center; justify-content:center; gap:.6rem;
  direction:rtl; text-align:right;
  background:#ffffff; color:#111827;
  border:1px solid #e5e7eb;
  border-radius:12px;
  padding:.6rem 1rem;
  font-weight:600;
  box-shadow:0 4px 12px rgba(2,6,23,.06);
  transition:transform .12s ease, box-shadow .12s ease, background .12s ease;
}
.stDownloadButton > button:hover{
  transform:translateY(-2px);
  box-shadow:0 8px 18px rgba(2,6,23,.09);
  background:#f9fafb;
}

/* אייקון ההורדה – ריבוע כחול עם חץ לבן בצד ימין */
.stDownloadButton > button::after{
  content:"";
  width:22px; height:22px; border-radius:6px; flex:0 0 22px;
  background:#3b82f6;                  /* כחול */
  -webkit-mask: url('data:image/svg+xml;utf8,\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white">\
<path d="M12 3a1 1 0 0 1 1 1v8.586l2.293-2.293a1 1 0 1 1 1.414 1.414l-4 4a1 1 0 0 1-1.414 0l-4-4a1 1 0 1 1 1.414-1.414L11 12.586V4a1 1 0 0 1 1-1zM5 20a1 1 0 1 1 0-2h14a1 1 0 1 1 0 2H5z"/></svg>') center/14px 14px no-repeat;
          mask: url('data:image/svg+xml;utf8,\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white">\
<path d="M12 3a1 1 0 0 1 1 1v8.586l2.293-2.293a1 1 0 1 1 1.414 1.414l-4 4a1 1 0 0 1-1.414 0l-4-4a1 1 0 1 1 1.414-1.414L11 12.586V4a1 1 0 0 1 1-1zM5 20a1 1 0 1 1 0-2h14a1 1 0 1 1 0 2H5z"/></svg>') center/14px 14px no-repeat;
}
</style>
""", unsafe_allow_html=True)

# ===== מצב מנהל =====
is_admin_mode = (st.query_params.get("admin", "0") == "1")

if is_admin_mode:
    st.title("🔑 גישת מנהל - צפייה בנתונים")
    password = st.text_input("הכנס סיסמת מנהל", type="password")
    if password == ADMIN_PASSWORD:
        try:
            df = pd.read_csv(CSV_FILE)
            st.success("התחברת בהצלחה ✅")
            st.dataframe(df, use_container_width=True)

            # ---- הורדה כ-Excel (XLSX) בלבד ----
            xlsx_buf = BytesIO()
            with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="מיפוי")
            st.download_button(
                "הורדת Excel (XLSX) ⬇️",
                data=xlsx_buf.getvalue(),
                file_name="mapping_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except FileNotFoundError:
            st.warning("⚠ עדיין אין נתונים שנשמרו.")
    else:
        if password:
            st.error("סיסמה שגויה")
    st.stop()

# ===== טופס למילוי =====
st.title("📋 מיפוי מדריכים לשיבוץ סטודנטים - שנת הכשרה תשפ\"ו")
st.write("""
שלום רב, מטרת טופס זה היא לאסוף מידע עדכני על מדריכים ומוסדות הכשרה לקראת שיבוץ הסטודנטים לשנת ההכשרה הקרובה.  
אנא מלא/י את כל השדות בצורה מדויקת. המידע ישמש לצורך תכנון השיבוץ בלבד.
""")

with st.form("mapping_form"):
    st.subheader("פרטים אישיים")
    last_name = st.text_input("שם משפחה *")
    first_name = st.text_input("שם פרטי *")

    st.subheader("מוסד והכשרה")
    institution = st.text_input("מוסד / שירות ההכשרה *")
    specialization = st.selectbox("תחום ההתמחות *", ["בחר מהרשימה", "חינוך", "בריאות", "רווחה", "אחר"])
    specialization_other = ""
    if specialization == "אחר":
        specialization_other = st.text_input("אם ציינת אחר, אנא כתוב את תחום ההתמחות *")

    st.subheader("כתובת מקום ההכשרה")
    internship_place = st.text_input("שם מקום ההתמחות *")   # ➕ שדה חדש
    street = st.text_input("רחוב *")
    internship_city = st.text_input("עיר כתובת ההתמחות *")   # ➕ שדה חדש
    city = st.text_input("עיר *")
    postal_code = st.text_input("מיקוד *")

    st.subheader("קליטת סטודנטים")
    num_students = st.number_input("מספר סטודנטים שניתן לקלוט השנה *", min_value=0, step=1)
    continue_mentoring = st.radio("האם מעוניין/ת להמשיך להדריך השנה *", ["כן", "לא"])

    st.subheader("פרטי התקשרות")
    phone = st.text_input("טלפון * (לדוגמה: 050-1234567)")
    email = st.text_input("כתובת אימייל *")

    submit_btn = st.form_submit_button("שלח/י")

# ===== טיפול בטופס =====
if submit_btn:
    errors = []

    if not last_name.strip():
        errors.append("יש למלא שם משפחה")
    if not first_name.strip():
        errors.append("יש למלא שם פרטי")
    if not institution.strip():
        errors.append("יש למלא מוסד/שירות ההכשרה")
    if specialization == "בחר מהרשימה":
        errors.append("יש לבחור תחום התמחות")
    if specialization == "אחר" and not specialization_other.strip():
        errors.append("יש למלא את תחום ההתמחות")
    if not internship_place.strip():
        errors.append("יש למלא שם מקום ההתמחות")
    if not street.strip():
        errors.append("יש למלא רחוב")
    if not internship_city.strip():
        errors.append("יש למלא עיר כתובת ההתמחות")
    if not city.strip():
        errors.append("יש למלא עיר")
    if not postal_code.strip():
        errors.append("יש למלא מיקוד")
    if num_students <= 0:
        errors.append("יש להזין מספר סטודנטים גדול מ-0")
    if not re.match(r"^0\d{1,2}-\d{6,7}$", phone.strip()):
        errors.append("מספר הטלפון אינו תקין (פורמט מומלץ: 050-1234567)")
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email.strip()):
        errors.append("כתובת האימייל אינה תקינה")

    if errors:
        for e in errors:
            st.error(e)
    else:
        data = {
            "תאריך": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            "שם משפחה": [last_name],
            "שם פרטי": [first_name],
            "מוסד/שירות ההכשרה": [institution],
            "תחום התמחות": [specialization_other if specialization == "אחר" else specialization],
            "שם מקום ההתמחות": [internship_place],   # ➕ שמירה בקובץ
            "עיר כתובת ההתמחות": [internship_city],   # ➕ שמירה בקובץ
            "רחוב": [street],
            "עיר": [city],
            "מיקוד": [postal_code],
            "מספר סטודנטים": [num_students],
            "המשך הדרכה": [continue_mentoring],
            "טלפון": [phone],
            "אימייל": [email]
        }

        df = pd.DataFrame(data)

        try:
            existing_df = pd.read_csv(CSV_FILE)
            updated_df = pd.concat([existing_df, df], ignore_index=True)
            updated_df.to_csv(CSV_FILE, index=False)
        except FileNotFoundError:
            df.to_csv(CSV_FILE, index=False)

        st.success("✅ הנתונים נשמרו בהצלחה!")
