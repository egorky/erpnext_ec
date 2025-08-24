var doctype_customized = "Sales Invoice";

frappe.ui.form.on(doctype_customized, {
    refresh(frm) {
        if (frm.doc.status == 'Cancelled' || frm.doc.status == 'Draft') {
            return false;
        }
        SetFormSriButtons(frm, doctype_customized);
    },
    estab: function(frm) {
        frm.set_value('ptoemi', '');
        if (frm.doc.estab) {
            frappe.call({
                method: 'erpnext_ec.utilities.tools.get_ptoemi_list_for_establishment',
                args: {
                    establishment: frm.doc.estab
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_df_property('ptoemi', 'options', r.message);
                        frm.refresh_field('ptoemi');
                    }
                }
            });
        }
    },
})
