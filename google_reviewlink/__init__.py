"""Turn any Google Maps link into a direct Google review link. https://github.com/Iverium/google-reviewlink"""
from .links import LinkError, feature_from_place_id, parse, place_id_from_feature, review_links

__version__ = "1.0.0"
__all__ = ["LinkError", "feature_from_place_id", "parse", "place_id_from_feature", "review_links"]
