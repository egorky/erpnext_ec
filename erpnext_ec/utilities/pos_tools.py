import frappe

def validate_pos_invoice(doc, method):
    # This hook runs on Sales Invoice validation.
    # It checks if the invoice is a consolidated POS invoice and, if so,
    # populates the 'estab' and 'ptoemi' fields from the POS Profile's custom fields.
    if (doc.is_pos == 1 and doc.is_consolidated == 1 and doc.items and doc.items[0].get("pos_invoice") and not doc.get("estab")):
        try:
            # Get the original POS invoice from the first item to find the POS Profile
            pos_invoice_name = doc.items[0].get("pos_invoice")
            pos_profile_name = frappe.db.get_value("Sales Invoice", pos_invoice_name, "pos_profile")

            if pos_profile_name:
                # Get the custom estab and ptoemi from the POS Profile
                custom_estab, custom_ptoemi = frappe.db.get_value("POS Profile", pos_profile_name, ["custom_estab", "custom_ptoemi"])

                if custom_estab and custom_ptoemi:
                    # Set the values on the standard fields of the consolidated invoice
                    doc.set("estab", custom_estab)
                    doc.set("ptoemi", custom_ptoemi)

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Error en validate_pos_invoice de ERPNext EC")
            # Do not throw an exception here, as it would prevent the user from seeing the original mandatory error.
            pass
