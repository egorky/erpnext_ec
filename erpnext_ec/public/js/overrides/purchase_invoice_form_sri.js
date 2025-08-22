var doctype_customized = "Purchase Invoice";

frappe.ui.form.on(doctype_customized, {
    onload: function(frm) {
        // Set query for ptoemi based on estab
        frm.set_query("ptoemi", function() {
            return {
                "query": "erpnext_ec.utilities.tools.get_ptoemi_for_establishment",
                "filters": {
                    "estab": frm.doc.estab
                }
            }
        });

        if (frappe.session.default_is_purchase_settlement == 1) {
            var default_is_purchase_settlement = frappe.session.default_is_purchase_settlement;
            frm.set_value('is_purchase_settlement', default_is_purchase_settlement);
            frappe.session.default_is_purchase_settlement = null;
        }

        if (frm.doc.is_purchase_settlement)
        {
            //frm.dashboard.clear_headline();
            //frm.dashboard.set_headline('MODO LIQUIDACIÓN DE COMPRA')
        }
    },
	refresh(frm)
    {
        if (frm.doc.status == 'Cancelled' || frm.doc.status == 'Draft')
        {
            return false;
        }        
        
        //SetFormSriButtons(frm, doctype_customized);      
        //console.log(frm);
        //console.log(frm.doctype_customized);
    },
    estab: function(frm)
	{
        frm.set_value('ptoemi',  '');
        frm.refresh_field('ptoemi');
	},
    is_purchase_settlement: function(frm)
    {
        if (frm.doc.is_purchase_settlement) {
            frm.set_value('is_return', 0);
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