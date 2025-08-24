from frappe import __version__ as frappe_version

app_name = "erpnext_ec"
app_title = "ERPNext Ec"
app_publisher = "BeebTech"
app_description = "Erpnext Ecuador"
app_email = "ronald.chonillo@gmail.com"
app_license = "mit"
required_apps = [
    'erpnext'
]

app_include_js = [
    "/assets/erpnext_ec/js/sri_custom.js",
    "/assets/erpnext_ec/js/sales_invoice_tools.js",
    "/assets/erpnext_ec/js/delivery_note_tools.js",
    "/assets/erpnext_ec/js/withholding_tools.js",
    "/assets/erpnext_ec/js/frappe_sri_ui_tools.js",
    "/assets/erpnext_ec/js/purchase_receipt_tools.js",
    "/assets/erpnext_ec/js/libs/jsonTree/jsonTree.js",
    "/assets/erpnext_ec/js/libs/monthpicker/jquery.ui.monthpicker.min.js",
    "/assets/erpnext_ec/js/utils/desk.custom.js",
]

app_include_css = [
    "/assets/erpnext_ec/js/libs/jsonTree/jsonTree.css",
    "/assets/erpnext_ec/js/libs/monthpicker/qunit.min.css",
    "/assets/erpnext_ec/js/libs/monthpicker/jquery-ui.css",
]

doctype_js = {
    "Sales Invoice" : "public/js/overrides/sales_invoice_form_sri.js",
    "Delivery Note" : "public/js/overrides/delivery_note_form_sri.js",
    "Purchase Invoice" : "public/js/overrides/purchase_invoice_form_sri.js",
    "Company" : "public/js/overrides/company_form_sri.js",
    }
doctype_list_js = {
    "Sales Invoice" : "public/js/overrides/sales_invoice_list_sri.js",
    "Purchase Invoice" : "public/js/overrides/purchase_invoice_list_sri.js",
    "Delivery Note" : "public/js/overrides/delivery_note_list_sri.js",
    "Print Format" : "public/js/overrides/print_format_list_sri.js",
    "Account" : "public/js/overrides/account_list_sri.js",
    }

is_frappe_above_v14 = int(frappe_version.split('.')[0]) > 14
is_frappe_above_v13 = int(frappe_version.split('.')[0]) > 13
is_frappe_above_v12 = int(frappe_version.split('.')[0]) > 12
frappe_version_int = int(frappe_version.split('.')[0])

# Jinja hooks
if is_frappe_above_v13:
    # Use jinja for v14+
    jinja = {
        "methods": [
                    "erpnext_ec.utilities.doc_builder_fac",
                    "erpnext_ec.utilities.doc_builder_cre",
                    "erpnext_ec.utilities.doc_builder_grs",
                    "erpnext_ec.utilities.doc_builder_ncr",
                    "erpnext_ec.utilities.doc_builder_liq",
                    "erpnext_ec.utilities.tools",
                    ]
    }
else:
    # Use jenv for v13 and below
    jenv = {
        "methods": [
            "build_doc_fac:erpnext_ec.utilities.doc_builder_fac.build_doc_fac",
            "build_doc_fac_with_images:erpnext_ec.utilities.doc_builder_fac.build_doc_fac_with_images",
            "build_doc_cre:erpnext_ec.utilities.doc_builder_cre.build_doc_cre",
            "build_doc_cre_with_images:erpnext_ec.utilities.doc_builder_cre.build_doc_cre_with_images",
            "build_doc_grs:erpnext_ec.utilities.doc_builder_grs.build_doc_grs",
            "build_doc_grs_with_images:erpnext_ec.utilities.doc_builder_grs.build_doc_grs_with_images",
            "build_doc_ncr:erpnext_ec.utilities.doc_builder_ncr.build_doc_ncr",
            "build_doc_ncr_with_images:erpnext_ec.utilities.doc_builder_ncr.build_doc_ncr_with_images",
            "build_doc_liq:erpnext_ec.utilities.doc_builder_liq.build_doc_liq",
            "build_doc_liq_with_images:erpnext_ec.utilities.doc_builder_liq.build_doc_liq_with_images",
            "get_full_url:erpnext_ec.utilities.tools.get_full_url",
        ],
        "filters": [
        ]
    }

# Installation
before_install = "erpnext_ec.install.before_install"
after_install = ["erpnext_ec.install.after_install"]

# Document Events
doc_events = {
    "Xml Responses": {
        "validate": "erpnext_ec.erpnext_ec.doctype.xml_responses.events.validate",
	    "on_update": "erpnext_ec.erpnext_ec.doctype.xml_responses.events.on_update",
        "after_insert": "erpnext_ec.erpnext_ec.doctype.xml_responses.events.after_insert",
    }
}

on_session_creation = [
	"erpnext_ec.utilities.tools.on_login_auto",
]

get_translated_dict = {
	("doctype", "Global Defaults"): "frappe.geo.country_info.get_translated_dict"
}