import frappe

def validate_pos_invoice(doc, method):
    if (doc.is_pos == 0 and doc.items and doc.items[0].get("pos_invoice") and not doc.get("estab")):
        try:
            pos_invoice_name = doc.items[0].get("pos_invoice")
            pos_profile = frappe.db.get_value("Sales Invoice", pos_invoice_name, "pos_profile")

            if pos_profile:
                estab, ptoemi = frappe.db.get_value("POS Profile", pos_profile, ["estab", "ptoemi"])
                if estab and ptoemi:
                    doc.set("estab", estab)
                    doc.set("ptoemi", ptoemi)

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Error en validate_pos_invoice de ERPNext EC")
            pass
