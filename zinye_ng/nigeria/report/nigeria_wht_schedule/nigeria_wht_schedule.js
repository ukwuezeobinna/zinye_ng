frappe.query_reports["Nigeria WHT Schedule"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1,
            default: frappe.defaults.get_user_default("Company"),
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start(),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end(),
        },
        {
            fieldname: "wht_category",
            label: __("WHT Category"),
            fieldtype: "Select",
            options: [
                "",
                "Professional / Consultancy Fees",
                "Management / Technical Fees",
                "Construction / Building",
                "Rent / Lease",
                "Royalties",
                "Dividends",
                "Interest (Financial Institution)",
                "Commission / Agency Fees",
                "Contracts (Supply of Goods)",
                "Directors Fees",
            ].join("\n"),
        },
    ],
};
