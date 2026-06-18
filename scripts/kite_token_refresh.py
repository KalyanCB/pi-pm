#!/usr/bin/env python3
"""Kite Connect daily access token refresh — headless login via Zerodha web API.

Simulates the Zerodha login flow (password + TOTP) to obtain a fresh
request_token, exchanges it for an access_token, and persists it to the
app_settings DB table so the API picks it up immediately.

Run daily at 06:15 IST (00:45 UTC) via cron — after Kite resets tokens at 06:00.

Required env vars (in .env):
    KITE_API_KEY        Kite Connect app API key
    KITE_API_SECRET     Kite Connect app API secret
    KITE_USER_ID        Zerodha client ID (e.g. PIPM)
    KITE_PASSWORD       Zerodha login password
    KITE_TOTP_SECRET    Base32 TOTP secret (from authenticator setup, not the 6-digit code)

Usage:
    uv run python scripts/kite_token_refresh.py
    uv run python scripts/kite_token_refresh.py --dry-run
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from urllib.parse import parse_qs, urlparse

import pyotp
import requests
from kiteconnect import KiteConnect
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [KITE-REFRESH] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("kite_refresh")

ZERODHA_LOGIN_URL = "https://kite.zerodha.com/api/login"
ZERODHA_TWOFA_URL = "https://kite.zerodha.com/api/twofa"


def load_settings():
    import os
    from pathlib import Path

    # Load .env from project root
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

    required = ["KITE_API_KEY", "KITE_API_SECRET", "KITE_USER_ID", "KITE_PASSWORD", "KITE_TOTP_SECRET"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        log.error("Missing required env vars: %s", ", ".join(missing))
        sys.exit(1)

    return {
        "api_key": os.environ["KITE_API_KEY"].strip(),
        "api_secret": os.environ["KITE_API_SECRET"].strip(),
        "user_id": os.environ["KITE_USER_ID"].strip(),
        "password": os.environ["KITE_PASSWORD"].strip(),
        "totp_secret": os.environ["KITE_TOTP_SECRET"].strip(),
        "database_url": os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://pipm:pipm@localhost:5432/pipm",
        ).strip(),
    }


def get_request_token(user_id: str, password: str, totp_secret: str, api_key: str) -> str:
    """Simulate Zerodha web login to obtain a Kite Connect request_token."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "X-Kite-Version": "3",
        "Content-Type": "application/x-www-form-urlencoded",
    })

    # Step 1: password login
    log.info("Step 1: password login for %s", user_id)
    resp = session.post(
        ZERODHA_LOGIN_URL,
        data={"user_id": user_id, "password": password},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "success":
        raise RuntimeError(f"Login failed: {data.get('message', data)}")

    request_id = data["data"]["request_id"]
    twofa_type = data["data"].get("twofa_type", "totp")
    log.info("Login OK — request_id: %s  twofa_type: %s", request_id, twofa_type)

    # Step 2: TOTP
    totp_code = pyotp.TOTP(totp_secret).now()
    log.info("Step 2: submitting TOTP %s", totp_code)
    resp = session.post(
        ZERODHA_TWOFA_URL,
        data={
            "user_id": user_id,
            "request_id": request_id,
            "twofa_value": totp_code,
            "twofa_type": twofa_type,
            "skip_session": "",
        },
        timeout=15,
        allow_redirects=False,
    )

    # Zerodha redirects to our redirect URL with ?request_token=...
    location = resp.headers.get("Location", "")
    if not location:
        # Some versions return 200 with redirect in body JSON
        body = resp.json() if resp.content else {}
        if body.get("status") != "success":
            raise RuntimeError(f"TOTP failed: {body.get('message', body)}")
        # Try to follow one more redirect
        resp2 = session.get(f"https://kite.zerodha.com/connect/login?api_key={api_key}&v=3",
                            allow_redirects=False, timeout=15)
        location = resp2.headers.get("Location", "")

    if not location:
        raise RuntimeError("No redirect location found after TOTP — check credentials or TOTP secret")

    log.info("Redirect URL: %s", location)

    # Zerodha may redirect to connect/finish?sess_id=... before the final callback.
    # Follow that hop to get the real request_token.
    if "connect/finish" in location:
        finish_url = location if location.startswith("http") else f"https://kite.zerodha.com{location}"
        resp3 = session.get(finish_url, allow_redirects=False, timeout=15)
        location = resp3.headers.get("Location", location)
        log.info("Final redirect URL: %s", location)

    parsed = urlparse(location)
    params = parse_qs(parsed.query)

    if params.get("status", [""])[0] != "success":
        raise RuntimeError(f"Kite login status not success: {params}")

    request_token = params.get("request_token", [None])[0]
    if not request_token:
        raise RuntimeError(f"No request_token in redirect: {location}")

    log.info("request_token obtained: %s…", request_token[:12])
    return request_token


def exchange_token(api_key: str, api_secret: str, request_token: str) -> str:
    kite = KiteConnect(api_key=api_key)
    session_data = kite.generate_session(request_token, api_secret=api_secret)
    access_token = session_data["access_token"]
    log.info("access_token obtained: %s… (user: %s)", access_token[:12], session_data.get("user_id"))
    return access_token


def save_token(database_url: str, access_token: str) -> None:
    engine = create_engine(database_url)
    with Session(engine) as db:
        db.execute(
            text("""
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ('kite_access_token', :token, now())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
            """),
            {"token": access_token},
        )
        db.commit()
    log.info("access_token saved to app_settings DB")


def main() -> int:
    parser = argparse.ArgumentParser(description="Kite daily token refresh")
    parser.add_argument("--dry-run", action="store_true", help="Login + exchange but don't save to DB")
    args = parser.parse_args()

    cfg = load_settings()

    log.info("=" * 50)
    log.info("Kite token refresh | user=%s | dry_run=%s", cfg["user_id"], args.dry_run)
    log.info("=" * 50)

    try:
        request_token = get_request_token(
            cfg["user_id"], cfg["password"], cfg["totp_secret"], cfg["api_key"]
        )
    except Exception as exc:
        log.error("Failed to obtain request_token: %s", exc)
        return 1

    try:
        access_token = exchange_token(cfg["api_key"], cfg["api_secret"], request_token)
    except Exception as exc:
        log.error("Failed to exchange request_token: %s", exc)
        return 1

    if args.dry_run:
        log.info("[dry-run] would save token: %s…", access_token[:16])
        return 0

    try:
        save_token(cfg["database_url"], access_token)
    except Exception as exc:
        log.error("Failed to save token to DB: %s", exc)
        return 1

    log.info("=" * 50)
    log.info("Token refresh complete.")
    log.info("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
