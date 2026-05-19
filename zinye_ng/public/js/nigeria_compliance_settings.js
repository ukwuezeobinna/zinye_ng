frappe.ui.form.on("Nigeria Compliance Settings", {
	refresh(frm) {
		if (frm.doc.einvoice_client_id) {
			frm.add_custom_button(__("Test FIRSMBS Connection"), () => {
				frappe.show_alert({ message: __("Testing FIRSMBS connection..."), indicator: "blue" });
				frm.call("test_einvoice_connection").then(r => {
					if (r.message && r.message.status === "success") {
						frappe.show_alert({ message: r.message.message, indicator: "green" });
					}
				});
			}, __("Actions"));
		}

		if (frm.doc.atrs_client_id) {
			frm.add_custom_button(__("Test ATRS Connection"), () => {
				frappe.show_alert({ message: __("Testing ATRS connection..."), indicator: "blue" });
				frm.call("test_atrs_connection").then(r => {
					if (r.message && r.message.status === "success") {
						frappe.show_alert({ message: r.message.message, indicator: "green" });
					}
				});
			}, __("Actions"));
		}
	},

	payroll_settings_link(frm) {
		frappe.set_route("Form", "Nigeria Payroll Settings");
	},
});
