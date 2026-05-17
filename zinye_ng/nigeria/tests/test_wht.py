"""
Unit tests for Nigeria WHT computation and rate resolution.

Uses unittest.mock to isolate from DB — no Frappe site required.
"""
from unittest.mock import MagicMock, patch

from frappe.tests import UnitTestCase

from zinye_ng.nigeria.tax.wht import DEFAULT_WHT_RATES, _get_wht_rate, get_supplier_wht_info


def _make_invoice(supplier="TEST-SUP-001", ng_wht_rate=0.0, ng_wht_applicable=1):
    doc = MagicMock()
    doc.supplier = supplier
    doc.get.side_effect = lambda key, default=None: {
        "ng_wht_applicable": ng_wht_applicable,
        "ng_wht_rate": ng_wht_rate,
        "ng_wht_account": None,
    }.get(key, default)
    return doc


class TestGetWhtRate(UnitTestCase):
    def test_uses_explicit_invoice_rate_first(self):
        doc = _make_invoice(ng_wht_rate=7.5)
        rate = _get_wht_rate(doc)
        self.assertEqual(rate, 7.5)

    @patch("zinye_ng.nigeria.tax.wht.frappe.db.get_value")
    def test_falls_back_to_supplier_category(self, mock_get_value):
        mock_get_value.return_value = "Professional / Consultancy Fees"
        doc = _make_invoice(ng_wht_rate=0.0)
        rate = _get_wht_rate(doc)
        self.assertEqual(rate, DEFAULT_WHT_RATES["Professional / Consultancy Fees"])
        self.assertEqual(rate, 10.0)

    @patch("zinye_ng.nigeria.tax.wht.frappe.db.get_value")
    def test_returns_zero_when_no_category(self, mock_get_value):
        mock_get_value.return_value = None
        doc = _make_invoice(ng_wht_rate=0.0)
        rate = _get_wht_rate(doc)
        self.assertEqual(rate, 0.0)

    @patch("zinye_ng.nigeria.tax.wht.frappe.db.get_value")
    def test_returns_zero_for_unknown_category(self, mock_get_value):
        mock_get_value.return_value = "Some Unknown Category"
        doc = _make_invoice(ng_wht_rate=0.0)
        rate = _get_wht_rate(doc)
        self.assertEqual(rate, 0.0)

    def test_invoice_rate_zero_triggers_supplier_lookup(self):
        # rate=0.0 means not set → must try supplier lookup
        # If supplier has no category → 0.0 returned (not the 0.0 invoice rate shortcut)
        with patch("zinye_ng.nigeria.tax.wht.frappe.db.get_value") as mock_gv:
            mock_gv.return_value = "Construction / Building"
            doc = _make_invoice(ng_wht_rate=0.0)
            rate = _get_wht_rate(doc)
            self.assertEqual(rate, DEFAULT_WHT_RATES["Construction / Building"])
            self.assertEqual(rate, 5.0)


class TestDefaultWhtRates(UnitTestCase):
    """All categories in the schedule must have defined rates."""

    def test_all_categories_have_positive_rate(self):
        for category, rate in DEFAULT_WHT_RATES.items():
            self.assertGreater(rate, 0.0, f"Rate for '{category}' should be > 0")

    def test_professional_fees_rate(self):
        self.assertEqual(DEFAULT_WHT_RATES["Professional / Consultancy Fees"], 10.0)

    def test_construction_rate(self):
        self.assertEqual(DEFAULT_WHT_RATES["Construction / Building"], 5.0)

    def test_contracts_supply_goods_rate(self):
        self.assertEqual(DEFAULT_WHT_RATES["Contracts (Supply of Goods)"], 5.0)


class TestGetSupplierWhtInfo(UnitTestCase):
    @patch("zinye_ng.nigeria.tax.wht.frappe.db.get_value")
    def test_returns_category_and_rate(self, mock_get_value):
        mock_get_value.return_value = "Rent / Lease"
        result = get_supplier_wht_info("TEST-SUP-001")
        self.assertEqual(result["category"], "Rent / Lease")
        self.assertEqual(result["rate"], 10.0)

    @patch("zinye_ng.nigeria.tax.wht.frappe.db.get_value")
    def test_no_category_returns_zero_rate(self, mock_get_value):
        mock_get_value.return_value = None
        result = get_supplier_wht_info("TEST-SUP-001")
        self.assertEqual(result["category"], "")
        self.assertEqual(result["rate"], 0.0)

    @patch("zinye_ng.nigeria.tax.wht.frappe.db.get_value")
    def test_returns_dict_with_required_keys(self, mock_get_value):
        mock_get_value.return_value = "Dividends"
        result = get_supplier_wht_info("ANY-SUP")
        self.assertIn("category", result)
        self.assertIn("rate", result)
