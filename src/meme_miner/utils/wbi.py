"""WBI signature implementation for Bilibili API.

WBI (Web Interface) is Bilibili's anti-crawling signature mechanism.
Based on: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/misc/sign/wbi.md
"""

import hashlib
import time
import urllib.parse
from typing import Dict


# WBI key table for character swapping
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52
]


def get_mixin_key(orig: str) -> str:
    """Generate mixin key from img_key and sub_key."""
    return ''.join([orig[i] for i in MIXIN_KEY_ENC_TAB])[:32]


def md5_hash(text: str) -> str:
    """Calculate MD5 hash."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def wbi_sign(params: Dict[str, str], img_key: str, sub_key: str) -> Dict[str, str]:
    """Sign parameters with WBI signature.
    
    Args:
        params: Request parameters
        img_key: WBI img_key (from nav API)
        sub_key: WBI sub_key (from nav API)
    
    Returns:
        Parameters with wts and w_rid added
    """
    # Add timestamp
    params['wts'] = str(int(time.time()))
    
    # Sort parameters by key
    sorted_params = dict(sorted(params.items()))
    
    # Build query string
    query = urllib.parse.urlencode(sorted_params)
    
    # Generate mixin key
    mixin_key = get_mixin_key(img_key + sub_key)
    
    # Calculate w_rid
    w_rid = md5_hash(query + mixin_key)
    
    # Add signature
    params['w_rid'] = w_rid
    
    return params


# Cached keys (will be refreshed if needed)
_cached_img_key: str = ""
_cached_sub_key: str = ""
_cached_time: float = 0


def refresh_wbi_keys() -> tuple[str, str]:
    """Fetch fresh WBI keys from Bilibili nav API.
    
    Note: This is a simplified version. In production, you should 
    actually call the nav API to get fresh keys.
    """
    # Fallback keys (these expire, so we need to implement proper fetching)
    # For now, return empty to force using the nav API
    return "", ""
