frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1) return;

		const status = frm.doc.ng_firs_status;

		if (status === "Failed" || status === "Auto-Retry") {
			frm.add_custom_button(__("Submit to FIRS"), () => {
				frm.call("generate_einvoice").then(() => frm.reload_doc());
			}, __("Nigeria"));
		}

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

		_add_einvoice_status_indicator(frm, status);
	},
});

function _add_einvoice_status_indicator(frm, status) {
	const color_map = {
		"Cleared":     "green",
		"Submitted":   "blue",
		"Auto-Retry":  "orange",
		"Pending":     "grey",
		"Failed":      "red",
		"Not Required": "grey",
	};
	if (!status || status === "Not Required") return;

	const color = color_map[status] || "grey";
	frm.dashboard.add_indicator(__("FIRS: {0}", [__(status)]), color);
}
