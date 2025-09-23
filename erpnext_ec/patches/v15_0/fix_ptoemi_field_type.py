import frappe
from frappe.custom.doctype.custom_field.custom_field import add_custom_field

def execute():
    # --- Cleanup all previous versions of the custom fields ---
    if frappe.db.exists("Custom Field", "POS Profile-estab"):
        frappe.delete_doc("Custom Field", "POS Profile-estab", ignore_permissions=True, force=True)

    if frappe.db.exists("Custom Field", "POS Profile-ptoemi"):
        frappe.delete_doc("Custom Field", "POS Profile-ptoemi", ignore_permissions=True, force=True)

    if frappe.db.exists("Custom Field", "POS Profile-custom_estab"):
        frappe.delete_doc("Custom Field", "POS Profile-custom_estab", ignore_permissions=True, force=True)

    if frappe.db.exists("Custom Field", "POS Profile-custom_ptoemi"):
        frappe.delete_doc("Custom Field", "POS Profile-custom_ptoemi", ignore_permissions=True, force=True)

    # Commit the deletions to ensure they are gone before creation
    frappe.db.commit()

    # --- Create the new fields using the robust add_custom_field API ---
    add_custom_field("POS Profile", {
        "fieldname": "custom_estab",
        "label": "Establecimiento SRI",
        "fieldtype": "Link",
        "options": "Sri Establishment",
        "insert_after": "company",
        "no_copy": 1,
    })

    add_custom_field("POS Profile", {
        "fieldname": "custom_ptoemi",
        "label": "Punto de Emision SRI",
        "fieldtype": "Select",
        "insert_after": "custom_estab",
        "no_copy": 1,
    })
