"""API benchmark script — measures response time for every key endpoint."""

import time
import json
import statistics
import sys
from typing import Optional
import urllib.request
import urllib.error

BASE = "http://localhost:7000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"
UNIT_USER = "MKDYM/ELA/0013"
UNIT_PASS = "test@123#"

RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"


def color_ms(ms: float) -> str:
    if ms < 300:
        return f"{GREEN}{ms:.0f}ms{RESET}"
    elif ms < 700:
        return f"{YELLOW}{ms:.0f}ms{RESET}"
    return f"{RED}{ms:.0f}ms{RESET}"


def request(method: str, path: str, token: Optional[str] = None,
            body: Optional[dict] = None, repeat: int = 1) -> dict:
    url = BASE + path
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = json.dumps(body).encode() if body else None
    timings = []
    status = 0
    resp_body = b""

    for _ in range(repeat):
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=30) as r:
                status = r.status
                resp_body = r.read()
        except urllib.error.HTTPError as e:
            status = e.code
            resp_body = e.read()
        except Exception as e:
            return {"error": str(e), "timings": [], "status": 0}
        elapsed = (time.perf_counter() - t0) * 1000
        timings.append(elapsed)

    try:
        parsed = json.loads(resp_body)
    except Exception:
        parsed = {}

    return {"status": status, "timings": timings, "body": parsed}


def login(username: str, password: str) -> Optional[str]:
    r = request("POST", "/api/auth/login",
                body={"username": username, "password": password})
    if r["status"] == 200:
        return r["body"].get("access_token")
    return None


def fmt_row(label: str, timings: list, status: int, note: str = "") -> None:
    if not timings:
        print(f"  {label:<55} {RED}FAILED (status {status}){RESET}")
        return
    first = timings[0]
    if len(timings) > 1:
        cached = timings[-1]
        speedup = first / cached if cached > 0 else 0
        extra = f"  {DIM}1st={first:.0f}ms  cached={color_ms(cached)}"
        if speedup > 1.5:
            extra += f"  {GREEN}({speedup:.1f}x faster){RESET}"
        else:
            extra += RESET
    else:
        extra = ""
    badge = f"[{status}]"
    print(f"  {label:<55} {color_ms(first)}{extra}  {DIM}{badge} {note}{RESET}")


SECTIONS: list[tuple[str, list]] = []


def section(title: str):
    SECTIONS.append((title, []))

def bench(label: str, method: str, path: str, token: str = None,
          body: dict = None, repeat: int = 2, note: str = ""):
    r = request(method, path, token=token, body=body, repeat=repeat)
    SECTIONS[-1][1].append((label, r["timings"], r.get("status", 0), note))


# ─── Run benchmarks ──────────────────────────────────────────────────────────

print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
print(f"{BOLD}{CYAN}  CSI API Benchmark  —  {BASE}{RESET}")
print(f"{BOLD}{CYAN}{'='*70}{RESET}\n")

print(f"{DIM}Authenticating...{RESET}")
admin_token = login(ADMIN_USER, ADMIN_PASS)
unit_token = login(UNIT_USER, UNIT_PASS)

if not admin_token:
    print(f"{RED}Admin login failed — check credentials{RESET}")
if not unit_token:
    print(f"{YELLOW}Unit login failed — unit-only endpoints skipped{RESET}")
print()

# ── Health ────────────────────────────────────────────────────────────────────
section("System")
bench("GET /api/health", "GET", "/api/health", repeat=3)

# ── Auth ──────────────────────────────────────────────────────────────────────
section("Auth")
bench("POST /api/auth/login (admin)", "POST", "/api/auth/login",
      body={"username": ADMIN_USER, "password": ADMIN_PASS}, repeat=1)
bench("POST /api/auth/login (unit)", "POST", "/api/auth/login",
      body={"username": UNIT_USER, "password": UNIT_PASS}, repeat=1)
bench("GET  /api/auth/districts  (1st, no cache)", "GET", "/api/auth/districts",
      token=admin_token, repeat=3, note="cached after 1st")
bench("GET  /api/auth/unit-names  (1st, no cache)", "GET", "/api/auth/unit-names",
      token=admin_token, repeat=3, note="cached after 1st")
if admin_token:
    bench("GET  /api/auth/me", "GET", "/api/auth/me",
          token=admin_token, repeat=2)

# ── Master data ───────────────────────────────────────────────────────────────
section("Master Data (cached 1 hour)")
bench("GET /api/master/countries  (1st hit)", "GET", "/api/master/countries",
      token=admin_token, repeat=3, note="TTL=3600s")
bench("GET /api/master/states?country_id=1 (1st hit)", "GET",
      "/api/master/states?country_id=1", token=admin_token, repeat=3)
bench("GET /api/master/cities?state_id=1", "GET",
      "/api/master/cities?state_id=1", token=admin_token, repeat=3)

# ── Admin dashboard ───────────────────────────────────────────────────────────
section("Admin Dashboard (cached 5 min)")
if admin_token:
    bench("GET /api/admin/units/home  (1st = DB)", "GET",
          "/api/admin/units/home?refresh=true", token=admin_token, repeat=1,
          note="UNION ALL pending query")
    bench("GET /api/admin/units/home  (cached)", "GET",
          "/api/admin/units/home", token=admin_token, repeat=2)

# ── Admin unit list ───────────────────────────────────────────────────────────
section("Admin Unit List (cached 5 min)")
if admin_token:
    bench("GET /api/admin/units/all  (1st = DB)", "GET",
          "/api/admin/units/all?refresh=true", token=admin_token, repeat=1)
    bench("GET /api/admin/units/all  (cached)", "GET",
          "/api/admin/units/all", token=admin_token, repeat=2)

# ── Admin users (now paginated) ───────────────────────────────────────────────
section("Admin Users (paginated)")
if admin_token:
    bench("GET /api/admin/users  (p1, all types)", "GET",
          "/api/admin/users?page=1&page_size=50", token=admin_token, repeat=2)
    bench("GET /api/admin/users  (UNIT only)", "GET",
          "/api/admin/users?user_type=UNIT&page=1&page_size=50",
          token=admin_token, repeat=2)

# ── Request lists (now filtered PENDING by default) ───────────────────────────
section("Admin Request Lists (status=PENDING default)")
if admin_token:
    bench("GET /api/admin/units/transfer-requests", "GET",
          "/api/admin/units/transfer-requests", token=admin_token, repeat=2)
    bench("GET /api/admin/units/member-change-requests", "GET",
          "/api/admin/units/member-change-requests", token=admin_token, repeat=2)
    bench("GET /api/admin/units/officials-change-requests", "GET",
          "/api/admin/units/officials-change-requests", token=admin_token, repeat=2)
    bench("GET /api/admin/units/councilor-change-requests", "GET",
          "/api/admin/units/councilor-change-requests", token=admin_token, repeat=2)
    bench("GET /api/admin/units/member-add-requests", "GET",
          "/api/admin/units/member-add-requests", token=admin_token, repeat=2)
    bench("GET /api/admin/units/archived-member-concern-requests", "GET",
          "/api/admin/units/archived-member-concern-requests",
          token=admin_token, repeat=2)

# ── Admin member/official/councilor pagination ────────────────────────────────
section("Admin Paginated Lists")
if admin_token:
    bench("GET /api/admin/units/members  (p1)", "GET",
          "/api/admin/units/members?page=1&page_size=50",
          token=admin_token, repeat=2)
    bench("GET /api/admin/units/officials  (p1)", "GET",
          "/api/admin/units/officials?page=1&page_size=50",
          token=admin_token, repeat=2)
    bench("GET /api/admin/units/councilors  (p1)", "GET",
          "/api/admin/units/councilors?page=1&page_size=50",
          token=admin_token, repeat=2)
    bench("GET /api/admin/units/archived-members  (p1)", "GET",
          "/api/admin/units/archived-members?page=1&page_size=50",
          token=admin_token, repeat=2)

# ── Blood donor search ────────────────────────────────────────────────────────
section("Blood Donor Search (indexed blood_group)")
if admin_token:
    bench("GET /api/admin/units/blood-donor-search  (no filter)", "GET",
          "/api/admin/units/blood-donor-search", token=admin_token, repeat=2)
    bench("GET /api/admin/units/blood-donor-search  (blood_group=O+)", "GET",
          "/api/admin/units/blood-donor-search?blood_group=O%2B",
          token=admin_token, repeat=2)

# ── Admin district/system ────────────────────────────────────────────────────
section("Admin System (cached)")
if admin_token:
    bench("GET /api/admin/system/districts  (1st)", "GET",
          "/api/admin/system/districts", token=admin_token, repeat=3,
          note="cached 1h")
    bench("GET /api/admin/system/unit-names  (1st)", "GET",
          "/api/admin/system/unit-names", token=admin_token, repeat=3,
          note="single JOIN, cached 1h")
    bench("GET /api/admin/system/district-wise-data (cached 5m)", "GET",
          "/api/admin/system/district-wise-data", token=admin_token, repeat=2)

# ── Registration payments ─────────────────────────────────────────────────────
section("Registration Payments (cached 2 min)")
if admin_token:
    bench("GET /api/admin/units/registration-payments (1st)", "GET",
          "/api/admin/units/registration-payments?refresh=true",
          token=admin_token, repeat=1)
    bench("GET /api/admin/units/registration-payments (cached)", "GET",
          "/api/admin/units/registration-payments",
          token=admin_token, repeat=2)

# ── Unit endpoints ────────────────────────────────────────────────────────────
section("Unit User Endpoints")
if unit_token:
    bench("GET /api/auth/me  (unit user)", "GET", "/api/auth/me",
          token=unit_token, repeat=2)
    bench("GET /api/units/application-form", "GET",
          "/api/units/application-form", token=unit_token, repeat=2)
    bench("GET /api/units/my-requests", "GET",
          "/api/units/my-requests", token=unit_token, repeat=2)
    bench("GET /api/units/payment", "GET",
          "/api/units/payment", token=unit_token, repeat=2)

# ── Conference public ─────────────────────────────────────────────────────────
section("Conference Public")
bench("GET /api/conference/public/list", "GET",
      "/api/conference/public/list", token=admin_token, repeat=2)

# ─── Print results ────────────────────────────────────────────────────────────
all_first_times = []

for title, rows in SECTIONS:
    print(f"\n{BOLD}── {title} {'─'*(55-len(title))}{RESET}")
    for label, timings, status, note in rows:
        fmt_row(label, timings, status, note)
        if timings:
            all_first_times.append(timings[0])

# ── Summary ───────────────────────────────────────────────────────────────────
if all_first_times:
    p50 = statistics.median(all_first_times)
    p95 = sorted(all_first_times)[int(len(all_first_times) * 0.95)]
    mean = statistics.mean(all_first_times)
    slowest = max(all_first_times)
    fastest = min(all_first_times)

    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}  Summary ({len(all_first_times)} endpoints measured){RESET}")
    print(f"  Mean    : {color_ms(mean)}")
    print(f"  Median  : {color_ms(p50)}")
    print(f"  P95     : {color_ms(p95)}")
    print(f"  Fastest : {color_ms(fastest)}")
    print(f"  Slowest : {color_ms(slowest)}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}\n")
