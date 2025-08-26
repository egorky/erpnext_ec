var doctype_customized = "Purchase Invoice";

frappe.ui.form.on(doctype_customized, {
    refresh(frm) {
        update_headline(frm);

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
        if (frm.doc.is_purchase_settlement) {
            frm.set_value('is_return', 0);

            // Use direct metadata manipulation for robust UI update
            let estab_df = frappe.meta.get_docfield(frm.doctype, 'estab', frm.doc.name);
            estab_df.fieldtype = 'Link';
            estab_df.options = 'SRI Establishment';

            let ptoemi_df = frappe.meta.get_docfield(frm.doctype, 'ptoemi', frm.doc.name);
            ptoemi_df.fieldtype = 'Link';
            ptoemi_df.options = 'SRI PtoEmi';

            // Refresh the fields to apply changes
            frm.refresh_field('estab');
            frm.refresh_field('ptoemi');

        } else {
            // Revert fields back to Data
            let estab_df = frappe.meta.get_docfield(frm.doctype, 'estab', frm.doc.name);
            estab_df.fieldtype = 'Data';
            estab_df.options = '';

            let ptoemi_df = frappe.meta.get_docfield(frm.doctype, 'ptoemi', frm.doc.name);
            ptoemi_df.fieldtype = 'Data';
            ptoemi_df.options = '';

            // Clear values
            frm.set_value('estab', '');
            frm.set_value('ptoemi', '');

            // Refresh the fields to apply changes
            frm.refresh_field('estab');
            frm.refresh_field('ptoemi');
        }
        update_headline(frm);
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