"""Unit and integration tests for the real authentication system in ui/auth.py.

Tests:
 1. Register a new account — returns success.
 2. Duplicate registration — rejected.
 3. _find_user finds the registered account.
 4. Password is stored as a bcrypt hash, not plaintext.
 5. Correct password verifies successfully.
 6. Incorrect password is rejected.
 7. Short password (<8 chars) is rejected at registration.
 8. Invalid email format is rejected at registration.
 9. Empty display name is rejected at registration.
10. is_authenticated() returns False when session state not set.
11. get_current_user() returns None when not authenticated.
12. Auth source code: no Demo Login text.
13. Auth source code: uses bcrypt.
14. Auth source code: no session_state.authenticated = True pattern.
15. Auth source code: no hardcoded passwords or user IDs.
16. _do_signin sets all required session state keys on success.
17. User isolation: two different users stored separately, retrieved independently.

Run with:
    python tests/test_auth.py
"""

import os
import sys
import tempfile
import sqlite3

# Ensure project root is on path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

failures = []


def check(name, condition, detail=""):
    if condition:
        print(f"[PASS]  {name}" + (f"  -- {detail}" if detail else ""))
    else:
        print(f"[FAIL]  {name}" + (f"  -- {detail}" if detail else ""))
        failures.append(name)


# ---------------------------------------------------------------------------
# Redirect auth module to a temp database so tests never touch production data
# ---------------------------------------------------------------------------
import ui.auth as auth_mod

_tmpdir = tempfile.mkdtemp()
_test_db = os.path.join(_tmpdir, "test_auth.db")
auth_mod._DB_PATH = _test_db  # override module-level path


# ---------------------------------------------------------------------------
# Test 1: Register a new account
# ---------------------------------------------------------------------------
ok, msg = auth_mod._create_user("alice@example.com", "Alice Smith", "securepass123")
check("Register new account succeeds", ok is True, msg)

# ---------------------------------------------------------------------------
# Test 2: Duplicate registration is rejected
# ---------------------------------------------------------------------------
ok2, msg2 = auth_mod._create_user("alice@example.com", "Alice Again", "anotherpass456")
check("Duplicate email registration rejected", ok2 is False, msg2)
check("Duplicate rejection message mentions 'already exists'", "already" in msg2.lower(), msg2)

# ---------------------------------------------------------------------------
# Test 3: _find_user returns the registered account
# ---------------------------------------------------------------------------
user = auth_mod._find_user("alice@example.com")
check("_find_user finds registered user", user is not None)
check("_find_user returns correct email", user and user["email"] == "alice@example.com", str(user))
check("_find_user returns correct display_name", user and user["display_name"] == "Alice Smith", str(user))

# ---------------------------------------------------------------------------
# Test 4: Password is stored as bcrypt hash, NOT plaintext
# ---------------------------------------------------------------------------
import bcrypt as _bcrypt
if user:
    stored = user["password_hash"]
    check(
        "Password stored as bcrypt hash (not plaintext)",
        stored.startswith("$2b$") or stored.startswith("$2a$"),
        stored[:20],
    )
    check("Stored hash is not the plaintext password", stored != "securepass123")

# ---------------------------------------------------------------------------
# Test 5: Correct password verifies
# ---------------------------------------------------------------------------
if user:
    check(
        "Correct password verifies against stored hash",
        auth_mod._verify_password("securepass123", user["password_hash"]),
    )

# ---------------------------------------------------------------------------
# Test 6: Wrong password is rejected
# ---------------------------------------------------------------------------
if user:
    check(
        "Wrong password fails verification",
        not auth_mod._verify_password("wrongpassword!", user["password_hash"]),
    )

# ---------------------------------------------------------------------------
# Test 7: Short password rejected at registration
# ---------------------------------------------------------------------------
ok_short, msg_short = auth_mod._create_user("bob@example.com", "Bob", "short")
check("Short password (<8 chars) rejected", ok_short is False, msg_short)
check("Short password error message mentions 8 characters", "8" in msg_short, msg_short)

# ---------------------------------------------------------------------------
# Test 8: Invalid email format rejected
# ---------------------------------------------------------------------------
ok_email, msg_email = auth_mod._create_user("not-an-email", "Charlie", "validpass123")
check("Invalid email format rejected", ok_email is False, msg_email)

# ---------------------------------------------------------------------------
# Test 9: Empty display name rejected
# ---------------------------------------------------------------------------
ok_name, msg_name = auth_mod._create_user("dave@example.com", "  ", "validpass123")
check("Empty display name rejected", ok_name is False, msg_name)

# ---------------------------------------------------------------------------
# Test 10: is_authenticated() returns False when session state not set
# ---------------------------------------------------------------------------
# We simulate streamlit session_state with a plain dict for unit tests.
import unittest.mock as mock


class _FakeSessionState(dict):
    def get(self, key, default=None):
        return super().get(key, default)


with mock.patch("streamlit.session_state", _FakeSessionState()) as fake_ss:
    result = auth_mod.is_authenticated()
    check("is_authenticated() False when session_state empty", result is False, str(result))

# ---------------------------------------------------------------------------
# Test 11: get_current_user() returns None when not authenticated
# ---------------------------------------------------------------------------
with mock.patch("streamlit.session_state", _FakeSessionState()) as fake_ss:
    user_info = auth_mod.get_current_user()
    check("get_current_user() None when not authenticated", user_info is None, str(user_info))

# ---------------------------------------------------------------------------
# Test 12: Auth source code has NO Demo Login
# ---------------------------------------------------------------------------
import inspect
src = inspect.getsource(auth_mod)
check("Auth source: NO Demo Login button", "Demo Login" not in src)
check("Auth source: NO play-button Demo Login", "\u25b6 Demo Login" not in src)

# ---------------------------------------------------------------------------
# Test 13: Auth source code uses bcrypt
# ---------------------------------------------------------------------------
check("Auth source: uses bcrypt", "bcrypt" in src)
check("Auth source: uses bcrypt.hashpw or bcrypt.checkpw", "bcrypt.hashpw" in src or "bcrypt.checkpw" in src)

# ---------------------------------------------------------------------------
# Test 14: No fake session_state.authenticated = True bypass
# ---------------------------------------------------------------------------
check(
    "Auth source: no 'session_state.authenticated = True' bypass",
    "session_state.authenticated = True" not in src and
    "session_state['authenticated'] = True" not in src,
)

# ---------------------------------------------------------------------------
# Test 15: No hardcoded passwords or user IDs in source
# ---------------------------------------------------------------------------
hardcoded_patterns = [
    "password123", "admin@", "demo.user@", "aegis.ai",
    "user_id = 1", "user_id=1", "\"anonymous\"",
]
for pat in hardcoded_patterns:
    check(f"Auth source: no hardcoded value '{pat}'", pat not in src.lower())

# ---------------------------------------------------------------------------
# Test 16: _do_signin sets required session state keys
# ---------------------------------------------------------------------------
# Register a second user and sign in.
auth_mod._create_user("signin_test@example.com", "Sign In Tester", "testpass99!")

_fake_ss2 = _FakeSessionState()
with mock.patch("streamlit.session_state", _fake_ss2):
    ok_si, msg_si = auth_mod._do_signin("signin_test@example.com", "testpass99!")
    check("_do_signin returns True for valid credentials", ok_si is True, msg_si)
    check("_do_signin sets _auth_verified=True", _fake_ss2.get("_auth_verified") is True)
    check("_do_signin sets _auth_user_id (non-empty string)", bool(_fake_ss2.get("_auth_user_id")))
    check("_do_signin sets _auth_email", _fake_ss2.get("_auth_email") == "signin_test@example.com",
          _fake_ss2.get("_auth_email"))
    check("_do_signin sets _auth_role", bool(_fake_ss2.get("_auth_role")))

# Test wrong credentials
_fake_ss3 = _FakeSessionState()
with mock.patch("streamlit.session_state", _fake_ss3):
    ok_bad, msg_bad = auth_mod._do_signin("signin_test@example.com", "wrongpassword!")
    check("_do_signin returns False for bad password", ok_bad is False, msg_bad)
    check("_do_signin does NOT set _auth_verified on bad password",
          _fake_ss3.get("_auth_verified") is not True)

# Test non-existent user
_fake_ss4 = _FakeSessionState()
with mock.patch("streamlit.session_state", _fake_ss4):
    ok_nouser, msg_nouser = auth_mod._do_signin("nobody@nowhere.com", "anypassword!")
    check("_do_signin returns False for non-existent user", ok_nouser is False, msg_nouser)

# ---------------------------------------------------------------------------
# Test 17: User isolation — two users stored and retrieved independently
# ---------------------------------------------------------------------------
auth_mod._create_user("user_a@corp.com", "User A", "passwordA123")
auth_mod._create_user("user_b@corp.com", "User B", "passwordB456")

ua = auth_mod._find_user("user_a@corp.com")
ub = auth_mod._find_user("user_b@corp.com")
check("User A exists and has correct display name", ua and ua["display_name"] == "User A")
check("User B exists and has correct display name", ub and ub["display_name"] == "User B")
check("User A and B have different IDs", ua and ub and ua["id"] != ub["id"])
check("User A password does not verify against User B hash",
      ua and ub and not auth_mod._verify_password("passwordA123", ub["password_hash"]))
check("User B password does not verify against User A hash",
      ua and ub and not auth_mod._verify_password("passwordB456", ua["password_hash"]))

# ---------------------------------------------------------------------------
# Cleanup temp database
# ---------------------------------------------------------------------------
try:
    import shutil
    shutil.rmtree(_tmpdir, ignore_errors=True)
except Exception:
    pass

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
total = sum(1 for line in open(__file__) if line.strip().startswith("check("))
passed = total - len(failures)
if failures:
    print(f"RESULT: {len(failures)} test(s) FAILED: {failures}")
    sys.exit(1)
else:
    print(f"RESULT: All {total} tests passed")
    sys.exit(0)
