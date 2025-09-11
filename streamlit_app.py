# =========================
# שיבוץ גרידי עמיד לסוגי קלט שונים
# =========================
import pandas as pd
from typing import List, Dict, Any

# שמות עמודות/שדות – אפשר לשנות כאן אם השמות אצלך שונים
SITE_NAME = "name"        # שם האתר/המוסד
SITE_CAP  = "capacity"    # קיבולת (מספר סטודנטים מקסימלי)
STU_ID    = "id"          # מזהה סטודנט
STU_NAME  = "name"        # שם הסטודנט
# עמודות ההעדפה: נזהה אוטומטית לפי דפוס (pref / העדפה / בחירה)
PREF_PATTERNS = ("pref", "העדפה", "בחירה")

def _safe_to_int(x, default=1) -> int:
    """המרה בטוחה ל-int, כולל None/NaN/מחרוזת ריקה."""
    try:
        v = pd.to_numeric(x, errors="coerce")
        if pd.isna(v):
            return int(default)
        return int(v)
    except Exception:
        return int(default)

def _normalize_sites(sites: Any) -> pd.DataFrame:
    """
    מקבל DataFrame / list[dict] / dict יחיד ומחזיר DataFrame עם העמודות:
    [SITE_NAME, SITE_CAP]
    """
    if isinstance(sites, pd.DataFrame):
        df = sites.copy()
    elif isinstance(sites, list) and all(isinstance(d, dict) for d in sites):
        df = pd.DataFrame(sites)
    elif isinstance(sites, dict):
        df = pd.DataFrame([sites])
    else:
        raise TypeError("sites חייב להיות DataFrame או רשימת מילונים או מילון יחיד")

    # בדיקת קיום עמודות בסיס
    if SITE_NAME not in df.columns:
        # נסיון למצוא שם אתר אפשרי
        candidates = [c for c in df.columns if c.strip().lower() in ("name", "site", "site_name", "מוסד", "שם")]
        if candidates:
            df.rename(columns={candidates[0]: SITE_NAME}, inplace=True)
        else:
            raise KeyError(f"לא נמצאה עמודת שם אתר ('{SITE_NAME}')")

    if SITE_CAP not in df.columns:
        # אם אין קיבולת, נייצר עם ברירת מחדל 1
        df[SITE_CAP] = 1

    # המרת קיבולת למספר שלם בטוח
    df[SITE_CAP] = df[SITE_CAP].apply(_safe_to_int)
    df[SITE_CAP] = df[SITE_CAP].clip(lower=0)  # לא לאפשר שליליים

    # הסרת אתרים בלי שם
    df = df[ df[SITE_NAME].astype(str).str.strip() != "" ].reset_index(drop=True)
    return df[[SITE_NAME, SITE_CAP]]

def _find_preference_columns(students_df: pd.DataFrame) -> List[str]:
    """מאתר עמודות העדפה לפי דפוסים נפוצים."""
    cols = []
    for col in students_df.columns:
        low = str(col).lower()
        if any(p in low for p in PREF_PATTERNS):
            cols.append(col)
    # אם לא מצאנו – ננסה pref1/pref_1/choice1 וכו'
    if not cols:
        guess = [c for c in students_df.columns if any(k in str(c).lower() for k in ("pref", "choice"))]
        cols = sorted(guess, key=lambda c: str(c).lower())
    return cols

def _normalize_students(students: Any) -> pd.DataFrame:
    """
    מקבל DataFrame / list[dict] / dict יחיד ומחזיר DataFrame מינימלי
    עם [STU_ID, STU_NAME] ועמודות ההעדפה (דינמי).
    """
    if isinstance(students, pd.DataFrame):
        df = students.copy()
    elif isinstance(students, list) and all(isinstance(d, dict) for d in students):
        df = pd.DataFrame(students)
    elif isinstance(students, dict):
        df = pd.DataFrame([students])
    else:
        raise TypeError("students חייב להיות DataFrame או רשימת מילונים או מילון יחיד")

    # זיהוי מזהה ושם
    if STU_ID not in df.columns:
        # אם אין ID – נייצר ID רץ
        df[STU_ID] = range(1, len(df) + 1)
    if STU_NAME not in df.columns:
        # נסיון לשמות חלופיים
        candidates = [c for c in df.columns if str(c).strip() in ("full_name", "student_name", "שם", "שם מלא")]
        if candidates:
            df.rename(columns={candidates[0]: STU_NAME}, inplace=True)
        else:
            df[STU_NAME] = df[STU_ID].apply(lambda x: f"סטודנט/ית {x}")

    # מציאת עמודות העדפה
    pref_cols = _find_preference_columns(df)
    # ננקה רווחים ונמיר ל־str כדי להשוות מול שמות אתרים
    for c in pref_cols:
        df[c] = df[c].astype(str).str.strip()

    return df[[STU_ID, STU_NAME] + pref_cols]

def greedy_match(students: Any, sites: Any) -> pd.DataFrame:
    """
    שיבוץ Greedy:
    - עובר על הסטודנטים לפי סדר הופעה.
    - לכל סטודנט בודק העדפות לפי סדר העמודות שנמצאו.
    - משבץ לאתר הראשון עם קיבולת פנויה.
    מחזיר DataFrame עם [student_id, student_name, assigned_site, assigned_rank].
    """
    stu_df  = _normalize_students(students)
    site_df = _normalize_sites(sites)

    # מילון קיבולות נוכחי
    capacity = {row[SITE_NAME]: int(row[SITE_CAP]) for _, row in site_df.iterrows()}

    pref_cols = [c for c in stu_df.columns if c not in (STU_ID, STU_NAME)]
    results: List[Dict[str, Any]] = []

    for _, row in stu_df.iterrows():
        assigned_site = None
        assigned_rank = None

        for rank, pref_col in enumerate(pref_cols, start=1):
            pref_site = str(row[pref_col]).strip()
            if not pref_site or pref_site.lower() in ("nan", "none"):
                continue
            # אם האתר קיים ויש בו מקום
            if capacity.get(pref_site, 0) > 0:
                assigned_site = pref_site
                assigned_rank = rank
                capacity[pref_site] -= 1
                break

        # אם לא נמצא אתר מועדף עם מקום – ננסה לשבץ לכל אתר פנוי
        if assigned_site is None:
            for s_name, cap in capacity.items():
                if cap > 0:
                    assigned_site = s_name
                    assigned_rank = None  # לא מהעדפות
                    capacity[s_name] -= 1
                    break

        results.append({
            "student_id": row[STU_ID],
            "student_name": row[STU_NAME],
            "assigned_site": assigned_site if assigned_site else "",
            "assigned_rank": assigned_rank
        })

    return pd.DataFrame(results)
