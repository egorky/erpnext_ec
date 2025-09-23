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

    # Ensure 'ptoemi' custom field exists and is of the correct type
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
    else:
        # If it exists, it might be the old buggy 'Link' type. Correct it.
        custom_field = frappe.get_doc("Custom Field", "POS Profile-ptoemi")
        if custom_field.fieldtype == "Link":
            custom_field.fieldtype = "Select"
            custom_field.options = ""
            custom_field.save()
