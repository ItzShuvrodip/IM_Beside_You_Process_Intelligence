"""Imports and normalizes payroll claims CSVs across Japanese and English schemas."""

import csv
import io
import json
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("BatchImporter")

# Column alias dictionary for resilient ingestion
COLUMN_ALIASES = {
    "case_id": ["case_id", "case", "伝票番号", "申請番号", "case_no", "ticket_id"],
    "employee_id": ["employee_id", "emp_id", "employee", "社員番号", "従業員番号", "staff_id"],
    "employee_name": ["employee_name", "name", "emp_name", "氏名", "名前", "従業員名"],
    "contract_type": ["contract_type", "contract", "employment_type", "雇用形態", "契約形態"],
    "base_salary": ["base_salary", "salary", "base_wage", "基本給", "給与"],
    "claimed_commute": ["claimed_commute", "commute", "commute_allowance", "transit", "通勤費", "定期代", "通勤手当"],
    "telework_days": ["telework_days", "telework", "wfh_days", "remote_days", "テレワーク日数", "在宅日数", "在宅勤務手当"],
    "claimed_housing": ["claimed_housing", "housing", "rent_subsidy", "住宅手当", "家賃補助"],
    "custom_deduction": ["custom_deduction", "deduction", "other_deduction", "任意控除", "その他控除"],
    "deduction_reason": ["deduction_reason", "reason", "deduction_memo", "控除事由", "事由", "備考", "memo"]
}


def normalize_contract_type(val: Any) -> str:
    s = str(val or "").strip().lower()
    if any(k in s for k in ["regular", "seishain", "正社員", "標準"]):
        return "regular"
    if any(k in s for k in ["contract", "keiyaku", "契約社員"]):
        return "contract"
    if any(k in s for k in ["outsourcing", "gyomu", "itaku", "業務委託", "委託"]):
        return "outsourcing"
    if any(k in s for k in ["part", "arubaito", "part_time", "パート", "アルバイト"]):
        return "part_time"
    return "regular"


def parse_claims_csv(content: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parses CSV text into standard claims format.
    Returns: (parsed_records, parsing_warnings)
    """
    records: List[Dict[str, Any]] = []
    warnings: List[str] = []

    reader = csv.reader(io.StringIO(content.strip()))
    header = next(reader, None)
    if not header:
        return [], ["File is completely empty."]

    # Map header positions with two-pass resolution (Exact matches first, then token/fallback)
    col_map: Dict[str, int] = {}
    normalized_header = [h.strip().lower() for h in header]
    claimed_indices = set()

    # Pass 1: Exact matches
    for std_key, aliases in COLUMN_ALIASES.items():
        for idx, col_name in enumerate(normalized_header):
            if idx in claimed_indices:
                continue
            if col_name in aliases:
                col_map[std_key] = idx
                claimed_indices.add(idx)
                break

    # Pass 2: Token / Word-boundary matching for remaining unmapped keys
    for std_key, aliases in COLUMN_ALIASES.items():
        if std_key in col_map:
            continue
        for idx, col_name in enumerate(normalized_header):
            if idx in claimed_indices:
                continue
            tokens = [t for t in col_name.replace("-", "_").replace(" ", "_").split("_") if t]
            if any(a in tokens for a in aliases):
                col_map[std_key] = idx
                claimed_indices.add(idx)
                break
            # Match Japanese substring or long specific composite alias (min length 3)
            if any(a in col_name for a in aliases if len(a) >= 3 and a not in ["case", "type", "name", "base", "memo"]):
                col_map[std_key] = idx
                claimed_indices.add(idx)
                break

    row_num = 1
    for row in reader:
        row_num += 1
        if not row or all(not cell.strip() for cell in row):
            continue

        def get_val(std_key: str, default: Any = "") -> Any:
            idx = col_map.get(std_key)
            if idx is not None and idx < len(row):
                return row[idx].strip()
            return default

        emp_id = get_val("employee_id", f"EMP-{9400 + row_num}")
        emp_name = get_val("employee_name", f"Employee {row_num:02d}")
        case_id = get_val("case_id", f"PI-BATCH-{row_num:03d}")

        try:
            salary = int(float(str(get_val("base_salary", 300000)).replace(",", "")))
        except ValueError:
            salary = 300000
            warnings.append(f"Row {row_num}: Invalid base salary, defaulted to ¥300,000.")

        try:
            commute = int(float(str(get_val("claimed_commute", 0)).replace(",", "")))
        except ValueError:
            commute = 0

        try:
            telework = int(float(str(get_val("telework_days", 0)).replace(",", "")))
        except ValueError:
            telework = 0

        try:
            housing = int(float(str(get_val("claimed_housing", 0)).replace(",", "")))
        except ValueError:
            housing = 0

        try:
            custom_ded = int(float(str(get_val("custom_deduction", 0)).replace(",", "")))
        except ValueError:
            custom_ded = 0

        record = {
            "case_id": case_id,
            "employee_id": emp_id,
            "employee_name": emp_name,
            "contract_type": normalize_contract_type(get_val("contract_type", "regular")),
            "base_salary": salary,
            "claimed_commute": commute,
            "telework_days": telework,
            "claimed_housing": housing,
            "custom_deduction": custom_ded,
            "deduction_reason": str(get_val("deduction_reason", ""))
        }
        records.append(record)

    return records, warnings
