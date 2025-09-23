import frappe

def execute():
    fields_to_delete = [
        "POS Profile-estab",
        "POS Profile-ptoemi",
        "POS Profile-custom_estab",
        "POS Profile-custom_ptoemi",
    ]

    for field in fields_to_delete:
        if frappe.db.exists("Custom Field", field):
            try:
                frappe.delete_doc("Custom Field", field, ignore_permissions=True, force=True)
                frappe.log_error(f"ERPNext EC Cleanup: Deleted Custom Field '{field}'", "Cleanup Patch")
            except Exception as e:
                frappe.log_error(f"ERPNext EC Cleanup: Failed to delete Custom Field '{field}'. Reason: {e}", "Cleanup Patch Error")

    frappe.db.commit()
