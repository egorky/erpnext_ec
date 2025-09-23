frappe.ui.form.on("POS Profile", {
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
});
