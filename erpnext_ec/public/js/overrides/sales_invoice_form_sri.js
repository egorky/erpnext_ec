var doctype_customized = "Sales Invoice";

frappe.ui.form.on(doctype_customized, {
    onload: function(frm) {
        // Set query for ptoemi based on estab
        frm.set_query('ptoemi', function() {
            console.log("Attempting to filter PtoEmi for Establishment: ", frm.doc.estab);
            if (!frm.doc.estab) {
                frappe.msgprint(__("Please select an Establishment first to get Point of Emission."));
                return;
            }
            return {
                filters: {
                    'parent': frm.doc.estab
                }
            };
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
