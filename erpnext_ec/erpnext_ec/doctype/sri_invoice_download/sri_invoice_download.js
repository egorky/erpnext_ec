// Copyright (c) 2025, Jules and contributors
// For license information, please see license.txt

frappe.ui.form.on("SRI Invoice Download", {
	refresh(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Start Download"), () => {
                frappe.call({
                    method: "erpnext_ec.erpnext_ec.doctype.sri_invoice_download.sri_invoice_download.start_download",
                    args: {
                        docname: frm.doc.name
                    },
                    callback: (r) => {
                        if (r.message) {
                            frappe.show_alert({
                                message: r.message,
                                indicator: "green"
                            }, 5);
                            frm.reload_doc();
                        }
                    }
                });
            }).addClass("btn-primary");
        }
	},
});
