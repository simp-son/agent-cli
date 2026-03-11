"""Tests for Phase 5a: Multi-Strategy Wallets."""
import os
import sys
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

_root = str(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from modules.wallet_manager import WalletConfig, WalletManager
from modules.apex_config import ApexConfig
from modules.apex_state import ApexSlot, ApexState
from parent.position_tracker import PositionTracker
from parent.risk_manager import RiskManager, RiskLimits


# ---------------------------------------------------------------------------
# WalletConfig
# ---------------------------------------------------------------------------

class TestWalletConfig:
    def test_defaults(self):
        wc = WalletConfig()
        assert wc.wallet_id == "default"
        assert wc.budget == 10_000.0
        assert wc.leverage == 10.0
        assert wc.guard_preset == "tight"

    def test_roundtrip(self):
        wc = WalletConfig(wallet_id="eth_agg", address="0xABC", budget=5000)
        d = wc.to_dict()
        wc2 = WalletConfig.from_dict(d)
        assert wc2.wallet_id == "eth_agg"
        assert wc2.address == "0xABC"
        assert wc2.budget == 5000


# ---------------------------------------------------------------------------
# WalletManager
# ---------------------------------------------------------------------------

class TestWalletManager:
    def test_single_wallet_default(self):
        wm = WalletManager.from_single(address="0x123", budget=5000)
        assert not wm.is_multi_wallet
        assert wm.wallet_ids == ["default"]
        assert wm.get_default().address == "0x123"
        assert wm.total_budget() == 5000

    def test_multi_wallet(self):
        wm = WalletManager()
        wm.register("eth_agg", WalletConfig(address="0xAAA", budget=5000))
        wm.register("btc_con", WalletConfig(address="0xBBB", budget=10000))
        assert wm.is_multi_wallet
        assert len(wm.wallet_ids) == 2
        assert wm.total_budget() == 15000
        assert wm.total_daily_loss_limit() == 1000  # 500 * 2

    def test_get_by_address(self):
        wm = WalletManager()
        wm.register("w1", WalletConfig(address="0xABC"))
        assert wm.get_by_address("0xabc") is not None
        assert wm.get_by_address("0xABC").wallet_id == "w1"
        assert wm.get_by_address("0xDEF") is None

    def test_roundtrip(self):
        wm = WalletManager()
        wm.register("w1", WalletConfig(address="0xA", budget=1000))
        wm.register("w2", WalletConfig(address="0xB", budget=2000))
        d = wm.to_dict()
        wm2 = WalletManager.from_dict(d)
        assert wm2.is_multi_wallet
        assert wm2.get("w1").address == "0xA"
        assert wm2.get("w2").budget == 2000

    def test_from_yaml_section_empty(self):
        wm = WalletManager.from_yaml_section({})
        assert not wm.is_multi_wallet
        assert wm.get_default() is not None

    def test_from_yaml_section_populated(self):
        data = {
            "aggressive": {
                "wallet_id": "aggressive",
                "address": "0xAGG",
                "budget": 5000,
                "leverage": 15.0,
            },
            "conservative": {
                "wallet_id": "conservative",
                "address": "0xCON",
                "budget": 10000,
                "leverage": 5.0,
            },
        }
        wm = WalletManager.from_yaml_section(data)
        assert wm.is_multi_wallet
        assert wm.get("aggressive").leverage == 15.0


# ---------------------------------------------------------------------------
# ApexConfig wallet_config field
# ---------------------------------------------------------------------------

class TestApexConfigWallet:
    def test_wallet_config_default_empty(self):
        cfg = ApexConfig()
        assert cfg.wallet_config == {}

    def test_wallet_config_roundtrip(self):
        cfg = ApexConfig(wallet_config={
            "w1": {"address": "0xA", "budget": 5000},
            "w2": {"address": "0xB", "budget": 10000},
        })
        d = cfg.to_dict()
        cfg2 = ApexConfig.from_dict(d)
        assert "w1" in cfg2.wallet_config
        assert cfg2.wallet_config["w1"]["address"] == "0xA"


# ---------------------------------------------------------------------------
# ApexSlot wallet_id
# ---------------------------------------------------------------------------

class TestApexSlotWallet:
    def test_default_wallet_id(self):
        slot = ApexSlot(slot_id=0)
        assert slot.wallet_id == "default"

    def test_wallet_id_roundtrip(self):
        slot = ApexSlot(slot_id=1, wallet_id="eth_agg")
        d = slot.to_dict()
        slot2 = ApexSlot.from_dict(d)
        assert slot2.wallet_id == "eth_agg"


# ---------------------------------------------------------------------------
# PositionTracker per-wallet helpers
# ---------------------------------------------------------------------------

class TestPositionTrackerWallet:
    def test_get_wallet_positions(self):
        pt = PositionTracker()
        pt.apply_fill("wallet_a", "ETH-PERP", "buy", Decimal("1"), Decimal("2000"))
        pt.apply_fill("wallet_b", "BTC-PERP", "sell", Decimal("0.5"), Decimal("50000"))
        pt.apply_fill("wallet_a", "BTC-PERP", "buy", Decimal("0.1"), Decimal("49000"))

        a_pos = pt.get_wallet_positions("wallet_a")
        assert "ETH-PERP" in a_pos
        assert "BTC-PERP" in a_pos
        assert len(a_pos) == 2

        b_pos = pt.get_wallet_positions("wallet_b")
        assert "BTC-PERP" in b_pos
        assert len(b_pos) == 1

    def test_get_wallet_pnl(self):
        pt = PositionTracker()
        pt.apply_fill("w1", "ETH-PERP", "buy", Decimal("1"), Decimal("2000"))
        # ETH went up to 2100 → unrealized PnL = 100
        pnl = pt.get_wallet_pnl("w1", {"ETH-PERP": Decimal("2100")})
        assert pnl == Decimal("100")

    def test_empty_wallet(self):
        pt = PositionTracker()
        assert pt.get_wallet_positions("nonexistent") == {}
        assert pt.get_wallet_pnl("nonexistent", {}) == Decimal("0")


# ---------------------------------------------------------------------------
# RiskManager per-wallet daily loss
# ---------------------------------------------------------------------------

class TestRiskManagerWallet:
    def test_check_wallet_daily_loss_under_limit(self):
        rm = RiskManager()
        assert not rm.check_wallet_daily_loss("w1", -200, 500)

    def test_check_wallet_daily_loss_at_limit(self):
        rm = RiskManager()
        assert rm.check_wallet_daily_loss("w1", -500, 500)

    def test_check_wallet_daily_loss_over_limit(self):
        rm = RiskManager()
        assert rm.check_wallet_daily_loss("w1", -600, 500)

    def test_check_wallet_daily_loss_no_limit(self):
        rm = RiskManager()
        assert not rm.check_wallet_daily_loss("w1", -9999, 0)


# ---------------------------------------------------------------------------
# Keystore address lookup
# ---------------------------------------------------------------------------

class TestKeystoreForAddress:
    def test_get_keystore_key_for_address_empty(self):
        from cli.keystore import get_keystore_key_for_address
        assert get_keystore_key_for_address("") is None

    def test_get_keystore_key_for_address_no_password(self):
        from cli.keystore import get_keystore_key_for_address
        with patch.dict(os.environ, {}, clear=True):
            with patch("cli.keystore._load_env_password", return_value=""):
                assert get_keystore_key_for_address("0xABC") is None
