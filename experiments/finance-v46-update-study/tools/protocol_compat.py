"""Versioned wire compatibility is distinct from the study's sealed identity."""
FINANCIAL_PROTOCOL='financial_product_v45'
STUDY_VERSION='v4.6-update'
AUTHORIZED_SPLITS=frozenset({'devsmoke','pilot'})
def is_financial_protocol(value):
    return value==FINANCIAL_PROTOCOL
