import frappe

def execute():
    # --- Cleanup old/wrong custom fields ---
    # Use a try/except block to avoid errors if the fields don't exist
    try:
        if frappe.db.exists("Custom Field", "POS Profile-estab"):
            frappe.delete_doc("Custom Field", "POS Profile-estab", ignore_permissions=True, force=True)
    except frappe.DoesNotExistError:
        pass

    try:
        if frappe.db.exists("Custom Field", "POS Profile-ptoemi"):
            frappe.delete_doc("Custom Field", "POS Profile-ptoemi", ignore_permissions=True, force=True)
    except frappe.DoesNotExistError:
        pass

    # Explicitly commit the deletions to the database
    frappe.db.commit()

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
        }).insert(ignore_permissions=True)

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
        }).insert(ignore_permissions=True)

    # Explicitly commit the creations to the database
    frappe.db.commit()
