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

		if (frm.doc.einvoice_enabled) {
			frm.add_custom_button(__("Sync HS Codes"), () => {
				frappe.confirm(
					__("This will fetch all product HS codes from FIRS and may take a minute. Proceed?"),
					() => {
						frappe.show_alert({ message: __("Syncing HS codes from FIRS..."), indicator: "blue" });
						frappe.call({
							method: "zinye_ng.nigeria.firs.resources.sync_hs_codes",
							callback: r => {
								if (r.message) {
									frappe.show_alert({
										message: __("Synced {0} HS codes", [r.message.synced]),
										indicator: "green",
									});
								}
							},
						});
					}
				);
			}, __("FIRS Reference Data"));

			frm.add_custom_button(__("Sync Service Codes"), () => {
				frappe.confirm(
					__("This will fetch all service codes from FIRS. Proceed?"),
					() => {
						frappe.show_alert({ message: __("Syncing service codes from FIRS..."), indicator: "blue" });
						frappe.call({
							method: "zinye_ng.nigeria.firs.resources.sync_service_codes",
							callback: r => {
								if (r.message) {
									frappe.show_alert({
										message: __("Synced {0} service codes", [r.message.synced]),
										indicator: "green",
									});
								}
							},
						});
					}
				);
			}, __("FIRS Reference Data"));

			frm.add_custom_button(__("Refresh Resource Cache"), () => {
				frappe.call({
					method: "zinye_ng.nigeria.firs.resources.sync_firs_resources",
					args: { force: 1 },
					callback: () => {
						frappe.show_alert({
							message: __("FIRS resource cache refreshed (countries, currencies, LGAs, quantity codes)"),
							indicator: "green",
						});
					},
				});
			}, __("FIRS Reference Data"));
		}
	},

	payroll_settings_link(frm) {
		frappe.set_route("Form", "Nigeria Payroll Settings");
	},
});
