"""Indian Government & Statutory Investment Schemes Package."""

from app.services.schemes.catalog import SCHEMES, SCHEMES_MAP, get_all_schemes, get_scheme_by_id
from app.services.schemes.calculator import calculate_scheme_growth, evaluate_profile_fit

__all__ = [
    "SCHEMES",
    "SCHEMES_MAP",
    "get_all_schemes",
    "get_scheme_by_id",
    "calculate_scheme_growth",
    "evaluate_profile_fit",
]
