frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;

		const status = frm.doc.ng_firs_status;

		// Retry submission (Failed or Auto-Retry)
		if (status === "Failed" || status === "Auto-Retry") {
			frm.add_custom_button(__("Submit to FIRS"), () => {
				frm.call("generate_einvoice").then(() => frm.reload_doc());
			}, __("Nigeria"));
		}

		// View linked e-Invoice record
		if (status === "Submitted" || status === "Cleared") {
			frm.add_custom_button(__("View e-Invoice"), () => {
				frm.call("get_einvoice_status").then(r => {
					if (r.message && r.message.name) {
						frappe.set_route("Form", "Nigeria E-Invoice", r.message.name);
					} else {
						frappe.msgprint(__("No e-Invoice record found."));
					}
				});
			}, __("Nigeria"));
		}

		// Transmit to buyer (after signing)
		if (status === "Submitted" && frm.doc.ng_firs_irn) {
			frm.add_custom_button(__("Transmit to Buyer"), () => {
				frappe.confirm(
					__("Transmit invoice {0} to the buyer via FIRS network?", [frm.doc.ng_firs_irn]),
					() => {
						frappe.call({
							method: "zinye_ng.nigeria.firs.einvoice.transmit_invoice",
							args: { irn: frm.doc.ng_firs_irn },
							callback: r => {
								frappe.show_alert({
									message: __("Invoice transmitted to buyer."),
									indicator: "green",
								});
								frm.reload_doc();
							},
							error: () => frappe.show_alert({ message: __("Transmit failed. Check FIRS e-Invoice log."), indicator: "red" }),
						});
					}
				);
			}, __("Nigeria"));
		}

		// Update payment status at FIRS when invoice is paid
		if (frm.doc.ng_firs_irn && ["Submitted", "Cleared"].includes(status)) {
			frm.add_custom_button(__("Mark FIRS Paid"), () => {
				frappe.call({
					method: "zinye_ng.nigeria.firs.einvoice.update_payment_status",
					args: {
						irn: frm.doc.ng_firs_irn,
						payment_status: "PAID",
						reference: frm.doc.name,
					},
					callback: () => {
						frappe.show_alert({ message: __("Payment status updated at FIRS."), indicator: "green" });
					},
				});
			}, __("Nigeria"));
		}

		_add_einvoice_status_indicator(frm, status);
	},
});

function _add_einvoice_status_indicator(frm, status) {
	const color_map = {
		"Cleared":      "green",
		"Submitted":    "blue",
		"Auto-Retry":   "orange",
		"Pending":      "grey",
		"Failed":       "red",
		"Cancelled":    "grey",
		"Not Required": "grey",
	};
	if (!status || status === "Not Required") return;

	const color = color_map[status] || "grey";
	frm.dashboard.add_indicator(__("FIRS: {0}", [__(status)]), color);
}
