"""Tests for post-registration member fee / payment balance adjustments."""

from datetime import datetime
from types import SimpleNamespace

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.units.registration_cycle_service import (  # noqa: E402
    build_payment_summary,
    compute_total_paid_for_approved_payments,
    preview_payment_after_member_delta,
    recalculate_latest_approved_balance,
)


def _payment(
    payment_id: int,
    *,
    total: int,
    balance: int | None,
    submitted_at: datetime,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=payment_id,
        total_amount=total,
        balance_amount=balance,
        submitted_at=submitted_at,
    )


def test_compute_total_paid_single_full_payment():
    approved = [_payment(1, total=820, balance=0, submitted_at=datetime(2026, 6, 1))]
    assert compute_total_paid_for_approved_payments(approved) == 820


def test_compute_total_paid_partial_chain():
    approved = [
        _payment(1, total=820, balance=310, submitted_at=datetime(2026, 6, 1)),
        _payment(2, total=820, balance=0, submitted_at=datetime(2026, 6, 2)),
    ]
    assert compute_total_paid_for_approved_payments(approved) == 820


def test_remove_then_add_swap_keeps_zero_balance():
    """Fully paid unit: admin removes one member then approves one add — net zero owed."""
    cycle = SimpleNamespace(total_fee_at_submit=820)
    payment = _payment(1, total=820, balance=0, submitted_at=datetime(2026, 6, 1))
    approved = [payment]

    cycle.total_fee_at_submit = 810
    recalculate_latest_approved_balance(cycle, approved)
    assert payment.balance_amount == 0

    cycle.total_fee_at_submit = 820
    recalculate_latest_approved_balance(cycle, approved)
    assert payment.balance_amount == 0


def test_build_payment_summary_credit_after_removals():
    cycle = SimpleNamespace(total_fee_at_submit=800, member_count_at_submit=70)
    payment = _payment(1, total=850, balance=0, submitted_at=datetime(2026, 6, 1))
    summary = build_payment_summary(cycle, [payment])
    assert summary["total_paid"] == 850
    assert summary["payment_credit"] == 50
    assert summary["balance_due"] == 0


def test_preview_remove_five_from_seventy_five():
    cycle = SimpleNamespace(total_fee_at_submit=850, member_count_at_submit=75)
    payment = _payment(1, total=850, balance=0, submitted_at=datetime(2026, 6, 1))
    preview = preview_payment_after_member_delta(
        cycle, [payment], delta_members=-5, member_fee=10, unit_fee=100
    )
    assert preview["projected"]["member_count"] == 70
    assert preview["projected"]["fee_owed"] == 800
    assert preview["projected"]["payment_credit"] == 50
    assert preview["projected"]["balance_due"] == 0


def test_legit_member_add_increases_balance():
    """Fully paid for 71 members; one net add after payment leaves one member fee due."""
    cycle = SimpleNamespace(total_fee_at_submit=820)
    payment = _payment(1, total=810, balance=0, submitted_at=datetime(2026, 6, 1))
    approved = [payment]

    recalculate_latest_approved_balance(cycle, approved)
    assert payment.balance_amount == 10
