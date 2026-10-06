"""Session cookie authentication."""
import hashlib
import hmac
import time
from http import cookies

from .config import SESSION_SECRET

def sign_session(ts_str):
    return hmac.new(SESSION_SECRET.encode(), ts_str.encode(), hashlib.sha256).hexdigest()

def verify_session(cookie_header):
    if not cookie_header:
        return False
    c = cookies.SimpleCookie()
    try:
        c.load(cookie_header)
        if "ops_token" not in c:
            return False
        token = c["ops_token"].value
        parts = token.split(".")
        if len(parts) != 2:
            return False
        ts, sig = parts[0], parts[1]
        expected = sign_session(ts)
        if not hmac.compare_digest(sig, expected):
            return False
        if time.time() - float(ts) > 86400 * 30:
            return False
        return True
    except Exception:
        return False

