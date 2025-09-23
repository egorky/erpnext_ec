import frappe

def execute():
    # --- Cleanup old/wrong custom fields ---
    if frappe.db.exists("Custom Field", "POS Profile-estab"):
        frappe.delete_doc("Custom Field", "POS Profile-estab", ignore_permissions=True)

    if frappe.db.exists("Custom Field", "POS Profile-ptoemi"):
        frappe.delete_doc("Custom Field", "POS Profile-ptoemi", ignore_permissions=True)

    # --- Create new, correctly named and typed custom fields ---

    # Create 'custom_estab' field
    if not frappe.db.exists("Custom Field", "POS Profile-custom_estab"):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "POS Profile",
            "fieldname": "custom_estab",
            "label": "Establecimiento SRI",
            "fieldtype": "Link",
            "options": "Sri Establishment",
            "insert_after": "company",
            "no_copy": 1,
        }).insert()

    # Create 'custom_ptoemi' field
    if not frappe.db.exists("Custom Field", "POS Profile-custom_ptoemi"):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "POS Profile",
            "fieldname": "custom_ptoemi",
            "label": "Punto de Emision SRI",
            "fieldtype": "Select",
            "insert_after": "custom_estab",
            "no_copy": 1,
        }).insert()
