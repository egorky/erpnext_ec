function populate_ptoemi_options(frm) {
    const estab = frm.doc.custom_estab;
    if (estab) {
        // Preserve the currently selected value if it's valid
        const ptoemi_val = frm.doc.custom_ptoemi;

        frappe.call({
            method: 'erpnext_ec.utilities.tools.get_ptoemi_list_for_establishment',
            args: {
                establishment: estab
            },
            callback: function(r) {
                if (r.message) {
                    frm.set_df_property('custom_ptoemi', 'options', r.message);

                    // After setting options, restore the saved value if it's still valid
                    if (ptoemi_val && r.message.includes(ptoemi_val)) {
                        frm.set_value('custom_ptoemi', ptoemi_val);
                    }
                    frm.refresh_field('custom_ptoemi');
                }
            }
        });
    } else {
        // If no establishment, clear the options and the value
        frm.set_df_property('custom_ptoemi', 'options', []);
        frm.set_value('custom_ptoemi', '');
        frm.refresh_field('custom_ptoemi');
    }
}

frappe.ui.form.on("POS Profile", {
    refresh: function(frm) {
        // Populate options on form load/refresh
        populate_ptoemi_options(frm);
    },
    custom_estab: function(frm) {
        // Clear the ptoemi value and repopulate options when establishment changes
        frm.set_value('custom_ptoemi', '');
        populate_ptoemi_options(frm);
    },
});
