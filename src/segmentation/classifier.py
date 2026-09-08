import re
from typing import Optional, List, Dict, Tuple, Any
from src.ingestion.models import RawEvent


# Known transient noise application patterns
NOISE_APP_PATTERNS = [
    r"powershell",
    r"cmd\.exe",
    r"windows\s*terminal",
    r"windowsterminal",
    r"slack",
    r"teams",
    r"procmine-desktop-agent",
    r"openwith",
    r"explorer"
]

NOISE_TITLE_PATTERNS = [
    r"powershell",
    r"microsoft\s*teams",
    r"activity-inbox",
    r"openwith",
    r"settings",
    r"restore pages"
]


def is_noise_event(event: RawEvent) -> bool:
    app = (event.app_name or "").lower()
    title = (event.window_title or "").lower()

    for p in NOISE_APP_PATTERNS:
        if re.search(p, app):
            return True
    for p in NOISE_TITLE_PATTERNS:
        if re.search(p, title):
            return True
    return False


# Documented Japanese Dataset A ground-truth family name -> Canonical Process Label Mapping
JAPANESE_GT_TO_CANONICAL: Dict[str, str] = {
    # HR processes
    "住民税通知確認": "resident_tax_confirmation",
    "給与備考・控除整備": "payroll_deduction_adjustment",
    "育児・産休申請確認": "leave_application_processing",
    "社保・年金補正対応": "social_insurance_correction",
    "入社照合・手当確認": "onboarding_verification",
    # Finance processes
    "請求書承認": "invoice_approval",
    "経費精算承認": "expense_settlement_approval",
    "銀行勘定照合": "bank_reconciliation",
    "予算差異分析": "budget_variance_analysis",
    "支払処理": "payment_processing",
    # Operations processes
    "受注処理": "sales_order_processing",
    "在庫調整": "inventory_order_management",
    "仕入先連絡": "supplier_communication",
    "出荷追跡": "shipment_tracking",
    "返品処理": "returns_processing",
}

# Ground truth single-letter execution code -> Canonical Process Label Mapping
GT_CODE_TO_CANONICAL: Dict[str, str] = {
    "A": "resident_tax_confirmation",
    "B": "payroll_deduction_adjustment",
    "C": "leave_application_processing",
    "D": "social_insurance_correction",
    "E": "onboarding_verification",
    "F": "invoice_approval",
    "G": "expense_settlement_approval",
    "H": "bank_reconciliation",
    "I": "budget_variance_analysis",
    "J": "payment_processing",
    "K": "sales_order_processing",
    "L": "inventory_order_management",
    "M": "supplier_communication",
    "N": "shipment_tracking",
    "O": "returns_processing",
}


def canonicalize_label(name_or_code: str) -> str:
    """
    Normalizes any Japanese family name, single-letter code, or English process label
    into its canonical standardized identifier.
    """
    if not name_or_code:
        return "unknown_or_unclassified"
    
    if name_or_code in JAPANESE_GT_TO_CANONICAL:
        return JAPANESE_GT_TO_CANONICAL[name_or_code]
    
    code_up = name_or_code.strip().upper()
    if code_up in GT_CODE_TO_CANONICAL:
        return GT_CODE_TO_CANONICAL[code_up]
    
    if name_or_code in ["inventory_adjustment"]:
        return "inventory_order_management"
    if name_or_code in ["payroll"]:
        return "payroll_deduction_adjustment"
    
    return name_or_code


class ClassificationResult(str):
    """
    Subclasses str so that `result == 'unknown_or_unclassified'` evaluates to True,
    while supporting tuple unpacking: `label, conf, method, ev = result`.
    """
    def __new__(cls, label: str, confidence: float = 0.20, method: str = "unclassified_gap", evidence: Optional[List[str]] = None):
        obj = str.__new__(cls, label)
        obj.label = label
        obj.confidence = confidence
        obj.detection_method = method
        obj.evidence = evidence or []
        return obj

    def __iter__(self):
        return iter((str(self), self.confidence, self.detection_method, self.evidence))

    def __getitem__(self, index):
        tup = (str(self), self.confidence, self.detection_method, self.evidence)
        return tup[index]

    def __len__(self):
        return 4


class ProcessClassifier:
    """
    Deterministic Process Classifier with Signal Confidence Scoring.
    Enforces strict precedence:
    1. Action element buttons (exact DOM buttons) -> Confidence: 0.95
    2. Active browser URL route -> Confidence: 0.85
    3. Process-specific desktop documents (Word / Excel guidelines) -> Confidence: 0.75
    4. Main ERP window titles -> Confidence: 0.60
    Fallback -> unknown_or_unclassified (Confidence: 0.20)
    """

    LABEL_RULES = [
        # Payroll Items & Deductions
        {
            "label": "payroll_deduction_adjustment",
            "url_patterns": [r"/payroll-items"],
            "title_patterns": [r"給与", r"payroll"],
            "button_patterns": [r"btn-pi-ok", r"pi-note", r"btn-pi-cancel"],
            "doc_patterns": [r"gyomu_itaku_kyuuyo_kitei"]
        },
        # Leave & Maternity Applications
        {
            "label": "leave_application_processing",
            "url_patterns": [r"/leave-applications"],
            "title_patterns": [r"休暇", r"育児", r"産休", r"leave"],
            "button_patterns": [r"btn-la-ok", r"la-note", r"btn-la-cancel"],
            "doc_patterns": [r"keiyaku_kaijo_tetsuzuki"]
        },
        # Onboarding & Allowances
        {
            "label": "onboarding_verification",
            "url_patterns": [r"/onboarding"],
            "title_patterns": [r"入社", r"オンボーディング", r"onboarding"],
            "button_patterns": [r"btn-ob-ok", r"ob-note", r"btn-ob-cancel"],
            "doc_patterns": [r"nyusha_checklist", r"gyomu_itaku_ukeire"]
        },
        # Social Insurance & Pension
        {
            "label": "social_insurance_correction",
            "url_patterns": [r"/social-insurance"],
            "title_patterns": [r"社保", r"年金", r"保険", r"social-insurance"],
            "button_patterns": [r"btn-si-ok", r"si-note", r"btn-si-cancel"],
            "doc_patterns": []
        },
        # Resident Tax Notifications
        {
            "label": "resident_tax_confirmation",
            "url_patterns": [r"/resident-tax"],
            "title_patterns": [r"住民税", r"resident-tax"],
            "button_patterns": [r"btn-rt-ok", r"rt-note", r"rt-table"],
            "doc_patterns": []
        },
        # Expense Settlement
        {
            "label": "expense_settlement_approval",
            "url_patterns": [r"/expense"],
            "title_patterns": [r"expense_calc", r"精算確認メモ", r"経費"],
            "button_patterns": [r"btn-exp-ok", r"exp-note"],
            "doc_patterns": [r"settai_keihi_kitei", r"gyomu_itaku_keihi_kitei"]
        },
        # Budget Variance
        {
            "label": "budget_variance_analysis",
            "url_patterns": [r"/budget"],
            "title_patterns": [r"budget_analysis", r"予算"],
            "button_patterns": [],
            "doc_patterns": [r"getsujitsu_teigaku_torihikisaki_ichiran"]
        },
        # Inventory & Order Management
        {
            "label": "inventory_order_management",
            "url_patterns": [r"/inventory", r"/order"],
            "title_patterns": [r"受発注在庫管理システム", r"在庫調整メモ", r"在庫", r"受発注"],
            "button_patterns": [],
            "doc_patterns": [r"shinkui_keiyaku", r"shinkuitorihikisaki_touroku"]
        },
        # Invoice Approval (Finance)
        {
            "label": "invoice_approval",
            "url_patterns": [r"/invoice", r"/ap-invoice"],
            "title_patterns": [r"請求書", r"invoice", r"請求承認"],
            "button_patterns": [r"btn-inv-ok", r"inv-note", r"btn-inv-cancel"],
            "doc_patterns": [r"invoice_checklist", r"seikyusho_kitei"]
        },
        # Bank Reconciliation (Finance)
        {
            "label": "bank_reconciliation",
            "url_patterns": [r"/bank-recon", r"/reconciliation"],
            "title_patterns": [r"銀行勘定", r"bank.recon", r"照合", r"reconciliation"],
            "button_patterns": [r"btn-br-ok", r"br-note"],
            "doc_patterns": [r"ginko_kanjyo_kitei", r"m1_reference"]
        },
        # Payment Processing (Finance)
        {
            "label": "payment_processing",
            "url_patterns": [r"/payment", r"/ap-payment"],
            "title_patterns": [r"支払処理", r"payment", r"支払"],
            "button_patterns": [r"btn-pay-ok", r"pay-note", r"btn-pay-cancel"],
            "doc_patterns": []
        },
        # Supplier Communication (Logistics)
        {
            "label": "supplier_communication",
            "url_patterns": [r"/supplier", r"/vendor"],
            "title_patterns": [r"仕入先", r"supplier", r"vendor", r"取引先"],
            "button_patterns": [],
            "doc_patterns": [r"shinkuitorihikisaki_touroku"]
        },
        # Shipment Tracking (Logistics)
        {
            "label": "shipment_tracking",
            "url_patterns": [r"/shipment", r"/tracking", r"/delivery"],
            "title_patterns": [r"出荷追跡", r"shipment", r"tracking", r"配送"],
            "button_patterns": [],
            "doc_patterns": []
        },
        # Returns Processing (Logistics)
        {
            "label": "returns_processing",
            "url_patterns": [r"/returns", r"/return-order"],
            "title_patterns": [r"返品処理", r"returns", r"返品"],
            "button_patterns": [],
            "doc_patterns": []
        }
    ]

    def classify_event_with_evidence(self, event: RawEvent) -> Optional[Tuple[str, float, str]]:
        """
        Classifies an event, returning (label, confidence, evidence_source) or None.
        """
        url = (event.browser_url or "").lower()
        title = (event.window_title or "").lower()
        elem = event.payload.get("element") or {}
        btn = (elem.get("attributes") or {}).get("id") or elem.get("inner_text") or ""
        btn = str(btn).lower()

        # 1. Action Element / Button (Highest Precision) -> 0.95
        if btn:
            for rule in self.LABEL_RULES:
                for bp in rule["button_patterns"]:
                    if bp in btn:
                        return rule["label"], 0.95, f"button:{bp}"

        # 2. Browser Tab URL Route -> 0.85
        if url and url != "about:blank":
            for rule in self.LABEL_RULES:
                for up in rule["url_patterns"]:
                    if re.search(up, url):
                        return rule["label"], 0.85, f"url:{up}"

        # 3. Document Title -> 0.75
        if title:
            for rule in self.LABEL_RULES:
                for dp in rule["doc_patterns"]:
                    if re.search(dp, title):
                        return rule["label"], 0.75, f"doc:{dp}"

        # 4. Core Window Title -> 0.60
        if title and not url:
            for rule in self.LABEL_RULES:
                for tp in rule["title_patterns"]:
                    if re.search(tp, title):
                        return rule["label"], 0.60, f"title:{tp}"

        return None

    def classify_event(self, event: RawEvent) -> Optional[str]:
        res = self.classify_event_with_evidence(event)
        return res[0] if res else None
    def classify_segment_events(self, events: List[RawEvent]) -> ClassificationResult:
        """
        Classifies a cluster of events for a segment.
        Returns: ClassificationResult (subclasses str for label comparison, unpacks as 4-tuple)
        """
        label_scores: Dict[str, float] = {}
        label_counts: Dict[str, int] = {}
        evidence: List[str] = []

        for ev in events:
            ev_res = self.classify_event_with_evidence(ev)
            if ev_res:
                lbl, conf, ev_src = ev_res
                label_counts[lbl] = label_counts.get(lbl, 0) + 1
                label_scores[lbl] = label_scores.get(lbl, 0.0) + conf
                if ev_src not in evidence and len(evidence) < 5:
                    evidence.append(ev_src)

        if not label_counts:
            return ClassificationResult("unknown_or_unclassified", 0.20, "unclassified_gap", ["no_matching_rules"])

        # Pick label with highest aggregated score
        best_label = max(label_scores.items(), key=lambda x: x[1])[0]
        count = label_counts[best_label]
        avg_conf = label_scores[best_label] / count

        # Determine primary detection method
        method = "window_context"
        if any(e.startswith("button:") for e in evidence):
            method = "dom_action_anchor"
            avg_conf = max(avg_conf, 0.95)
        elif any(e.startswith("url:") for e in evidence):
            method = "url_route_anchor"
            avg_conf = max(avg_conf, 0.85)
        elif any(e.startswith("doc:") for e in evidence):
            method = "document_context"
            avg_conf = max(avg_conf, 0.75)

        return ClassificationResult(best_label, round(avg_conf, 2), method, evidence)

