from typing import Dict, List


METRIC_CATALOG: Dict[str, Dict[str, str]] = {
    "gross_margin": {
        "metric_name": "Gross Margin",
        "benchmark_unit": "percentage",
        "why_it_matters": "Shows how much revenue remains after direct costs.",
    },
    "net_margin": {
        "metric_name": "Net Margin",
        "benchmark_unit": "percentage",
        "why_it_matters": "Measures overall profitability after all expenses.",
    },
    "ebitda_margin": {
        "metric_name": "EBITDA Margin",
        "benchmark_unit": "percentage",
        "why_it_matters": "Helps evaluate operating profitability before financing and accounting effects.",
    },
    "current_ratio": {
        "metric_name": "Current Ratio",
        "benchmark_unit": "ratio",
        "why_it_matters": "Indicates short-term liquidity and ability to cover current liabilities.",
    },
    "operating_expense_ratio": {
        "metric_name": "Operating Expense Ratio",
        "benchmark_unit": "percentage",
        "why_it_matters": "Shows how much revenue is consumed by operating expenses.",
    },
    "inventory_turnover": {
        "metric_name": "Inventory Turnover",
        "benchmark_unit": "turns_per_year",
        "why_it_matters": "Shows how efficiently inventory is sold and replaced.",
    },
    "days_inventory_outstanding": {
        "metric_name": "Days Inventory Outstanding",
        "benchmark_unit": "days",
        "why_it_matters": "Shows how long inventory sits before being sold.",
    },
    "cash_conversion_cycle": {
        "metric_name": "Cash Conversion Cycle",
        "benchmark_unit": "days",
        "why_it_matters": "Measures how quickly the business turns investments into cash.",
    },
    "churn_rate": {
        "metric_name": "Churn Rate",
        "benchmark_unit": "percentage",
        "why_it_matters": "Measures how quickly customers stop using the product.",
    },
    "customer_acquisition_cost": {
        "metric_name": "Customer Acquisition Cost",
        "benchmark_unit": "currency",
        "why_it_matters": "Measures the cost to acquire a new customer.",
    },
    "ltv_cac_ratio": {
        "metric_name": "LTV:CAC Ratio",
        "benchmark_unit": "ratio",
        "why_it_matters": "Shows whether customer value justifies acquisition cost.",
    },
    "mrr_growth": {
        "metric_name": "MRR Growth",
        "benchmark_unit": "percentage",
        "why_it_matters": "Tracks recurring revenue growth over time.",
    },
    "burn_multiple": {
        "metric_name": "Burn Multiple",
        "benchmark_unit": "multiple",
        "why_it_matters": "Measures capital efficiency relative to growth.",
    },
    "utilization_rate": {
        "metric_name": "Utilization Rate",
        "benchmark_unit": "percentage",
        "why_it_matters": "Shows how much billable capacity is being used.",
    },
    "revenue_per_employee": {
        "metric_name": "Revenue per Employee",
        "benchmark_unit": "currency",
        "why_it_matters": "Measures workforce productivity.",
    },
    "accounts_receivable_days": {
        "metric_name": "Accounts Receivable Days",
        "benchmark_unit": "days",
        "why_it_matters": "Shows how quickly customers pay invoices.",
    },
}

INDUSTRY_METRIC_MAP: Dict[str, List[str]] = {
    "b2b saas": [
        "gross_margin",
        "net_margin",
        "ebitda_margin",
        "churn_rate",
        "customer_acquisition_cost",
        "ltv_cac_ratio",
        "mrr_growth",
        "burn_multiple",
    ],
    "ai saas": [
        "gross_margin",
        "net_margin",
        "ebitda_margin",
        "churn_rate",
        "customer_acquisition_cost",
        "ltv_cac_ratio",
        "mrr_growth",
        "burn_multiple",
    ],
    "used furniture retail": [
        "gross_margin",
        "net_margin",
        "inventory_turnover",
        "days_inventory_outstanding",
        "cash_conversion_cycle",
        "current_ratio",
        "operating_expense_ratio",
    ],
    "construction": [
        "gross_margin",
        "net_margin",
        "ebitda_margin",
        "current_ratio",
        "accounts_receivable_days",
        "operating_expense_ratio",
    ],
    "accounting firm": [
        "gross_margin",
        "net_margin",
        "ebitda_margin",
        "utilization_rate",
        "revenue_per_employee",
        "accounts_receivable_days",
        "operating_expense_ratio",
    ],
    "distilleries": [
        "gross_margin",
        "net_margin",
        "ebitda_margin",
        "inventory_turnover",
        "days_inventory_outstanding",
        "cash_conversion_cycle",
        "current_ratio",
        "operating_expense_ratio",
    ],
}

INDUSTRY_CODE_MAP: Dict[str, str] = {
    "b2b saas": "b2b_saas",
    "ai saas": "ai_saas",
    "used furniture retail": "used_furniture_retail",
    "construction": "construction",
    "accounting firm": "accounting_firm",
    "distilleries": "distilleries",
}

INDUSTRY_ALIASES: Dict[str, str] = {
    "saas": "b2b saas",
    "software saas": "b2b saas",
    "b2b software": "b2b saas",
    "software startup": "b2b saas",
    "ai software": "ai saas",
    "ai platform": "ai saas",
    "artificial intelligence saas": "ai saas",
    "used furniture": "used furniture retail",
    "furniture resale": "used furniture retail",
    "used furniture store": "used furniture retail",
    "resale furniture": "used furniture retail",
    "retail furniture resale": "used furniture retail",
    "general construction": "construction",
    "contractor": "construction",
    "construction company": "construction",
    "accounting": "accounting firm",
    "accounting practice": "accounting firm",
    "cpa firm": "accounting firm",
    "distillery": "distilleries",
    "craft distillery": "distilleries",
    "spirits": "distilleries",
    "whisky": "distilleries",
    "whiskey": "distilleries",
}


DEFAULT_METRICS = ["gross_margin", "net_margin", "ebitda_margin", "current_ratio"]


def normalize_industry_name(industry_name: str) -> str:
    return industry_name.strip().lower()


def resolve_industry_name(industry_name: str) -> str:
    normalized = normalize_industry_name(industry_name)
    return INDUSTRY_ALIASES.get(normalized, normalized)


def get_industry_code(industry_name: str) -> str:
    resolved = resolve_industry_name(industry_name)
    return INDUSTRY_CODE_MAP.get(resolved, resolved.replace(" ", "_"))


def get_metrics_for_industry(industry_name: str) -> List[dict]:
    resolved = resolve_industry_name(industry_name)
    metric_codes = INDUSTRY_METRIC_MAP.get(resolved, DEFAULT_METRICS)

    metrics = []
    for metric_code in metric_codes:
        metric_data = METRIC_CATALOG[metric_code]
        metrics.append(
            {
                "metric_code": metric_code,
                "metric_name": metric_data["metric_name"],
                "benchmark_unit": metric_data["benchmark_unit"],
                "why_it_matters": metric_data["why_it_matters"],
            }
        )
    return metrics


def get_resolved_industry_name(industry_name: str) -> str:
    return resolve_industry_name(industry_name)


def is_supported_industry(industry_name: str) -> bool:
    resolved = resolve_industry_name(industry_name)
    return resolved in INDUSTRY_METRIC_MAP


def list_supported_industry_labels() -> List[str]:
    return sorted(INDUSTRY_METRIC_MAP.keys())