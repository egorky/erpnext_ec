import frappe

def execute():
    # Add custom fields to POS Profile
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

    if not frappe.db.exists("Custom Field", "POS Profile-ptoemi"):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "POS Profile",
            "fieldname": "ptoemi",
            "label": "Punto de Emision SRI",
            "fieldtype": "Link",
            "options": "Sri Ptoemi",
            "insert_after": "estab",
            "no_copy": 1,
        }).insert()
