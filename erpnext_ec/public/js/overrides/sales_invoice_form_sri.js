var doctype_customized = "Sales Invoice";

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
    },
	refresh(frm)
    {
        if (frm.doc.status == 'Cancelled' || frm.doc.status == 'Draft')
        {
            return false;
        }
        
        SetFormSriButtons(frm, doctype_customized);      
        //console.log(frm);
        //console.log(frm.doctype_customized);
    },
    estab: function(frm)
	{
        frm.set_value('ptoemi',  '');
        frm.refresh_field('ptoemi');
	},
})
