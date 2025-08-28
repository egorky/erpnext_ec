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
                            frappe.msgprint(r.message);
                            frm.reload_doc();
                        }
                    }
                }).then(() => {
                    frappe.show_alert({
                        message: __("Download process started in the background."),
                        indicator: "green"
                    });
                });
            }).addClass("btn-primary");
        }
	},
});
