#!/usr/bin/env python3
"""Smoke-test all OpenAPI routes against a running local server."""

import json
import os
import sys
import time

import httpx

BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:7000")
ADMIN_USER = os.getenv("API_TEST_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("API_TEST_ADMIN_PASS", "#Admin@c$i&")

PATH_PARAM_DEFAULTS = {
    "conference_id": "1",
    "district_id": "1",
    "official_id": "1",
    "request_id": "1",
    "member_id": "1",
    "user_id": "1",
    "unit_id": "1",
    "payment_id": "1",
    "appeal_id": "1",
    "category_id": "1",
    "event_id": "1",
    "candidate_id": "1",
    "registration_id": "1",
    "file_path": "test.jpg",
    "export_type": "members",
}

MUTATING = {"post", "put", "patch", "delete"}


def fill_path(path: str) -> str:
    out = path
    for key, val in PATH_PARAM_DEFAULTS.items():
        out = out.replace("{" + key + "}", val)
    return out


def classify(status: int) -> str:
    if status in (200, 201, 204) or 200 <= status < 300:
        return "ok"
    if status in (401, 403):
        return "auth"
    if status in (404, 405):
        return "not_found"
    if status in (422, 400):
        return "client_error"
    if status >= 500:
        return "server_error"
    return "other"


def needs_auth(path: str) -> bool:
    if path.startswith("/api/admin"):
        return True
    if path.startswith("/api/kalamela/admin") or path.startswith("/api/yuvalokham/admin"):
        return True
    if path in ("/api/auth/me",):
        return True
    if "/official/" in path and not path.startswith("/api/conference/public"):
        return True
    if path.startswith("/api/units/") and not path.startswith("/api/units/public"):
        return True
    return False


def skip_mutating(path: str, summary: str) -> bool:
    lowered = path.lower()
    if any(
        x in lowered
        for x in (
            "approve",
            "reject",
            "delete",
            "remove",
            "reset-password",
            "bulk-",
            "complete-registration",
            "restore-member",
            "revert",
        )
    ):
        return True
    if "upload" in summary.lower() or "export" in summary.lower():
        return True
    return False


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=120.0, follow_redirects=True)

    spec = client.get("/openapi.json")
    if spec.status_code != 200:
        print(f"FATAL: openapi.json -> {spec.status_code}")
        return 1
    paths = spec.json().get("paths", {})

    login_r = client.post("/api/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    if login_r.status_code != 200:
        print(f"FATAL: admin login -> {login_r.status_code}: {login_r.text[:300]}")
        return 1
    token = login_r.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    results: dict[str, list] = {
        "ok": [],
        "auth": [],
        "not_found": [],
        "client_error": [],
        "server_error": [],
        "other": [],
        "skipped_mutating": [],
    }
    timings: list[tuple[float, str, int]] = []

    for path, methods in sorted(paths.items()):
        if not path.startswith("/api/"):
            continue
        filled = fill_path(path)
        for method, op in methods.items():
            m = method.lower()
            if m not in ("get", "post", "put", "patch", "delete"):
                continue

            summary = op.get("summary") or ""
            if m in MUTATING and skip_mutating(filled, summary):
                results["skipped_mutating"].append(f"{m.upper()} {filled}")
                continue

            headers = auth_headers if needs_auth(filled) else {}

            t0 = time.perf_counter()
            try:
                if m == "get":
                    r = client.get(filled, headers=headers)
                elif m == "post":
                    r = client.post(filled, headers=headers, json={})
                elif m == "put":
                    r = client.put(filled, headers=headers, json={})
                elif m == "patch":
                    r = client.patch(filled, headers=headers, json={})
                else:
                    r = client.delete(filled, headers=headers)
            except Exception as exc:
                elapsed = time.perf_counter() - t0
                results["server_error"].append((f"{m.upper()} {filled}", str(exc), round(elapsed, 2)))
                continue

            elapsed = time.perf_counter() - t0
            timings.append((elapsed, f"{m.upper()} {filled}", r.status_code))
            bucket = classify(r.status_code)
            results[bucket].append((f"{m.upper()} {filled}", r.status_code, round(elapsed, 2)))

    timings.sort(reverse=True)

    print("=" * 60)
    print("API SMOKE TEST SUMMARY")
    print("=" * 60)
    print(f"Base URL: {BASE}")
    print("Admin login: OK")
    for key in results:
        print(f"{key}: {len(results[key])}")

    print("\n--- SERVER ERRORS (5xx or exceptions) ---")
    if results["server_error"]:
        for item in results["server_error"]:
            print(f"  {item[0]} -> {item[1]} ({item[2]}s)")
    else:
        print("  None")

    print("\n--- AUTH FAILURES (401/403) ---")
    for item in results["auth"][:25]:
        print(f"  {item[0]} -> {item[1]} ({item[2]}s)")
    if len(results["auth"]) > 25:
        print(f"  ... and {len(results['auth']) - 25} more")

    print("\n--- NOT FOUND (404) ---")
    for item in results["not_found"][:20]:
        print(f"  {item[0]} -> {item[1]} ({item[2]}s)")
    if len(results["not_found"]) > 20:
        print(f"  ... and {len(results['not_found']) - 20} more")

    print("\n--- OTHER (unexpected status) ---")
    for item in results["other"][:20]:
        print(f"  {item[0]} -> {item[1]} ({item[2]}s)")

    print("\n--- SLOWEST 15 ENDPOINTS ---")
    for elapsed, route, status in timings[:15]:
        print(f"  {elapsed:.2f}s  {status}  {route}")

    print("\n--- KEY ENDPOINTS (cold vs cached) ---")
    key_paths = [
        "/api/health",
        "/api/admin/units",
        "/api/admin/units/dashboard",
        "/api/admin/units/registration-payments",
        "/api/admin/units/member-add-requests",
        "/api/admin/district-wise-data",
    ]
    for path in key_paths:
        headers = {} if path == "/api/health" else auth_headers
        t0 = time.perf_counter()
        r = client.get(path, headers=headers)
        e1 = time.perf_counter() - t0
        t0 = time.perf_counter()
        r2 = client.get(path, headers=headers)
        e2 = time.perf_counter() - t0
        print(f"  GET {path}: {r.status_code} ({e1:.2f}s) -> cached {r2.status_code} ({e2:.2f}s)")

    report_path = "/tmp/api_test_report.json"
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "summary": {k: len(v) for k, v in results.items()},
                "results": results,
                "slowest": [{"seconds": e, "route": r, "status": s} for e, r, s in timings[:50]],
            },
            fh,
            indent=2,
        )
    print(f"\nFull report written to {report_path}")

    return 1 if results["server_error"] else 0


if __name__ == "__main__":
    sys.exit(main())
