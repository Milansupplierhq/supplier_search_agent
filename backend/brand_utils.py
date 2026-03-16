def normalize_brand_name(name: str) -> str:
    if not name:
        return ""
    return name.strip().title()


def infer_supplier_name(brand_hint: str, domain: str) -> str:
    """
    Best-effort supplier name resolution.
    """
    if brand_hint:
        return normalize_brand_name(brand_hint)

    if domain:
        base = domain.split(".")[0]
        return base.replace("-", " ").title()

    return ""
