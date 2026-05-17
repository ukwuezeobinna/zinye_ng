frappe.query_reports["Nigeria PAYE Schedule"] = {
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
            options: [
                {value: 1, label: __("January")},
                {value: 2, label: __("February")},
                {value: 3, label: __("March")},
                {value: 4, label: __("April")},
                {value: 5, label: __("May")},
                {value: 6, label: __("June")},
                {value: 7, label: __("July")},
                {value: 8, label: __("August")},
                {value: 9, label: __("September")},
                {value: 10, label: __("October")},
                {value: 11, label: __("November")},
                {value: 12, label: __("December")},
            ],
            reqd: 1,
            default: frappe.datetime.now_date().split("-")[1],
        },
        {
            fieldname: "year",
            label: __("Year"),
            fieldtype: "Select",
            reqd: 1,
            default: frappe.datetime.now_date().split("-")[0],
            get_query: () => frappe.call({
                method: "zinye_ng.nigeria.report.nigeria_paye_schedule.nigeria_paye_schedule.get_years",
            }),
        },
        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department",
        },
    ],
};
