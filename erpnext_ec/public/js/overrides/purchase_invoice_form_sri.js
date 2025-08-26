var doctype_customized = "Purchase Invoice";

frappe.ui.form.on(doctype_customized, {
    refresh(frm) {
        update_headline(frm);
        toggle_settlement_fields(frm);

        if (frm.doc.docstatus === 1) { // 1 is for Submitted status
            frm.add_custom_button(__('Comprobante de Retención'), function() {
                const data_to_pass = {
                    supplier: frm.doc.supplier,
                    invoice_name: frm.doc.name
                };
                localStorage.setItem('new_withholding_data', JSON.stringify(data_to_pass));
                frappe.new_doc('Purchase Withholding Sri Ec');
            }, __('Crear'));
        }
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
    is_purchase_settlement: function(frm)
    {
        toggle_settlement_fields(frm);
    },
    estab_link: function(frm) {
        // Sync link field to data field for backend logic
        frm.set_value('estab', frm.doc.estab_link);

        // Clear dependent fields
        frm.set_value('ptoemi_link', '');
        frm.set_value('ptoemi', '');

        if (frm.doc.estab_link) {
            frappe.call({
                method: 'erpnext_ec.utilities.tools.get_ptoemi_list_for_establishment',
                args: {
                    establishment: frm.doc.estab_link
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_df_property('ptoemi_link', 'options', r.message);
                        frm.refresh_field('ptoemi_link');
                    }
                }
            });
        }
    },
    ptoemi_link: function(frm) {
        // Sync link field to data field
        frm.set_value('ptoemi', frm.doc.ptoemi_link);
    },
    is_return: function(frm)
    {
        if (frm.doc.is_return) {
            frm.set_value('is_purchase_settlement', 0);
        }
        update_headline(frm);
    }
})


function update_headline(frm) {
    frm.dashboard.clear_headline()
    if (frm.doc.is_purchase_settlement) {
        frm.dashboard.set_headline("LIQUIDACIÓN DE COMPRA");
    } else if (frm.doc.is_return) {
        frm.dashboard.set_headline("NOTA DE DÉBITO");
    } else {
        frm.dashboard.set_headline("FACTURA DE COMPRA");
    }
}

function toggle_settlement_fields(frm) {
    const is_settlement = frm.doc.is_purchase_settlement;

    // Toggle visibility
    frm.toggle_display('estab', !is_settlement);
    frm.toggle_display('ptoemi', !is_settlement);
    frm.toggle_display('estab_link', is_settlement);
    frm.toggle_display('ptoemi_link', is_settlement);

    // Set requirement rules
    frm.toggle_reqd('estab', !is_settlement);
    frm.toggle_reqd('ptoemi', !is_settlement);
    frm.toggle_reqd('estab_link', is_settlement);
    frm.toggle_reqd('ptoemi_link', is_settlement);

    if (is_settlement) {
        frm.set_value('is_return', 0);
        // Ensure data is in sync if it was loaded before toggling
        frm.set_value('estab_link', frm.doc.estab);
        frm.set_value('ptoemi_link', frm.doc.ptoemi);
    } else {
        // Clear link fields when not a settlement
        frm.set_value('estab_link', null);
        frm.set_value('ptoemi_link', null);
    }

    frm.refresh_field('estab');
    frm.refresh_field('ptoemi');
    frm.refresh_field('estab_link');
    frm.refresh_field('ptoemi_link');
    update_headline(frm);
}