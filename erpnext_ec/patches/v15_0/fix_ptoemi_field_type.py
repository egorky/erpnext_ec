import frappe

def execute():
    if frappe.db.exists("Custom Field", "POS Profile-ptoemi"):
        custom_field = frappe.get_doc("Custom Field", "POS Profile-ptoemi")
        custom_field.fieldtype = "Select"
        custom_field.options = ""
        custom_field.save()
