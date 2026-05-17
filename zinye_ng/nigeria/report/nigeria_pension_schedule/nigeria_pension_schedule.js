frappe.query_reports["Nigeria Pension Schedule"] = {
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
            fieldname: "month",
            label: __("Month"),
            fieldtype: "Select",
            reqd: 1,
            options: [1,2,3,4,5,6,7,8,9,10,11,12].map(m => ({value: m, label: frappe.datetime.month_name(m)})),
            default: frappe.datetime.now_date().split("-")[1],
        },
        {
            fieldname: "year",
            label: __("Year"),
            fieldtype: "Select",
            reqd: 1,
            default: frappe.datetime.now_date().split("-")[0],
        },
    ],
};
