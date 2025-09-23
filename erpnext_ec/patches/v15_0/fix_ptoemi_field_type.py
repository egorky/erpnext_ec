import frappe

def execute():
    # Ensure 'estab' custom field exists and is correct
    if not frappe.db.exists("Custom Field", "POS Profile-estab"):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "POS Profile",
            "fieldname": "estab",
            "label": "Establecimiento SRI",
            "fieldtype": "Link",
            "options": "Sri Establishment",
            "insert_after": "company",
            "no_copy": 1,
        }).insert()

    # Handle 'ptoemi' field: delete if it's the wrong 'Link' type, then (re)create as 'Select'.
    if frappe.db.exists("Custom Field", "POS Profile-ptoemi"):
        # Check if the existing field is of the wrong type.
        field_type = frappe.db.get_value("Custom Field", "POS Profile-ptoemi", "fieldtype")
        if field_type == "Link":
            # If it's a Link, delete it. We'll recreate it correctly.
            frappe.delete_doc("Custom Field", "POS Profile-ptoemi", ignore_permissions=True)

    # Now, create the 'ptoemi' field if it doesn't exist (or was just deleted).
    if not frappe.db.exists("Custom Field", "POS Profile-ptoemi"):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "POS Profile",
            "fieldname": "ptoemi",
            "label": "Punto de Emision SRI",
            "fieldtype": "Select",
            "insert_after": "estab",
            "no_copy": 1,
        }).insert()
