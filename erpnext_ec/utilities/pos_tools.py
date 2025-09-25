import frappe
import json

def validate_pos_invoice(doc, method):
    # This hook runs on Sales Invoice validation for consolidated POS invoices.
    # It populates 'estab' and 'ptoemi' fields from the POS Profile.
    if doc.is_pos and doc.is_consolidated and not doc.get("estab"):
        try:
            # The consolidated invoice is created during the submission of a POS Closing Entry.
            # The context of that submission is in frappe.form_dict, which contains the triggering document.
            if frappe.form_dict and frappe.form_dict.get('doc'):

                # frappe.form_dict.doc is a JSON string that needs to be parsed.
                trigger_doc_data = json.loads(frappe.form_dict.get('doc'))

                # Ensure the trigger is the POS Closing Entry submission.
                if trigger_doc_data.get('doctype') == 'POS Closing Entry':
                    closing_entry_name = trigger_doc_data.get("name")

                    if not closing_entry_name:
                        return

                    # The doc might be unsaved (__unsaved=1), so get pos_opening_entry from payload first.
                    pos_opening_entry = trigger_doc_data.get("pos_opening_entry")

                    # If not in payload (e.g., during a background job), get from DB.
                    if not pos_opening_entry:
                        pos_opening_entry = frappe.db.get_value("POS Closing Entry", closing_entry_name, "pos_opening_entry")

                    if not pos_opening_entry:
                        return

                    pos_profile_name = frappe.db.get_value("POS Opening Entry", pos_opening_entry, "pos_profile")

                    if pos_profile_name:
                        custom_estab, custom_ptoemi = frappe.db.get_value("POS Profile", pos_profile_name, ["custom_estab", "custom_ptoemi"])

                        if custom_estab and custom_ptoemi:
                            doc.set("estab", custom_estab)
                            doc.set("ptoemi", custom_ptoemi)
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Error en validate_pos_invoice de ERPNext EC")
            # Do not throw an exception, as it would prevent the user from seeing the original mandatory error.
            pass
