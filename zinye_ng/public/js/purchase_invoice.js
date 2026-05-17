/**
 * Nigeria WHT auto-fill for Purchase Invoice.
 *
 * When a supplier is selected, fetches their WHT category and default rate,
 * then pre-populates ng_wht_applicable, ng_wht_rate on the form.
 * The user can override ng_wht_rate before saving.
 *
 * Server-side: zinye_ng.nigeria.tax.wht.on_purchase_invoice_submit creates the JE.
 */
frappe.ui.form.on("Purchase Invoice", {
	supplier: function (frm) {
		if (!frm.doc.supplier) return;

		frappe.call({
			method: "zinye_ng.nigeria.tax.wht.get_supplier_wht_info",
			args: { supplier: frm.doc.supplier },
			callback: function (r) {
				if (!r.message) return;
				const { category, rate } = r.message;

				if (category && rate > 0) {
					frm.set_value("ng_wht_applicable", 1);
					frm.set_value("ng_wht_rate", rate);
				} else {
					// Supplier has no WHT category — clear the section
					frm.set_value("ng_wht_applicable", 0);
					frm.set_value("ng_wht_rate", 0);
				}
			},
		});
	},

	ng_wht_applicable: function (frm) {
		if (!frm.doc.ng_wht_applicable) {
			frm.set_value("ng_wht_rate", 0);
		}
	},
});
