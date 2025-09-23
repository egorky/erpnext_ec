import frappe

def validate_pos_invoice(doc, method):
    if (doc.is_pos == 0 and doc.items and doc.items[0].get("pos_invoice") and not doc.get("estab")):
        try:
            original_pos_invoice = frappe.get_doc("Sales Invoice", doc.items[0].pos_invoice)
            if original_pos_invoice and original_pos_invoice.get("pos_profile"):
                pos_profile = frappe.get_doc("POS Profile", original_pos_invoice.pos_profile)
                if pos_profile.get("estab") and pos_profile.get("ptoemi"):
                    doc.set("estab", pos_profile.estab)
                    doc.set("ptoemi", pos_profile.ptoemi)
        except frappe.DoesNotExistError:
            # if the original invoice doesn't exist, do nothing
            pass
