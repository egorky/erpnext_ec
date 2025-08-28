# Copyright (c) 2025, Jules and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class SRIInvoiceDownload(Document):
	pass

def _get_settings():
	return frappe.get_doc("SRI Downloader Settings")

def _perform_sri_download(docname):
	from playwright.sync_api import sync_playwright
	import os

	doc = frappe.get_doc("SRI Invoice Download", docname)
	settings = _get_settings()

	username = settings.sri_username
	password = settings.get_password("sri_password")
	timeout_ms = (settings.timeout or 60) * 1000

	if not username or not password:
		doc.status = "Failed"
		doc.save()
		frappe.db.commit()
		frappe.log_error(title="SRI Download Failed", message="SRI Username and Password must be set.")
		return

	doc_type_map = {
		"Factura": "1",
		"Liquidación de compra de bienes y prestación de servicios": "2",
		"Notas de Crédito": "3",
		"Notas de Débito": "4",
		"Comprobante de Retención": "6"
	}

	with sync_playwright() as p:
		browser = p.chromium.launch(headless=True)
		page = browser.new_page()

		try:
			# 1. Login and navigate
			page.goto(settings.sri_login_url, timeout=timeout_ms)
			page.locator("#usuario").fill(username)
			page.locator("#password").fill(password)
			page.locator("#kc-login").click()
			page.wait_for_load_state('networkidle', timeout=timeout_ms)
			page.goto(settings.sri_target_url, wait_until='networkidle', timeout=timeout_ms)

			# 2. Set download parameters
			page.select_option("#frmPrincipal\\:ano", label=str(doc.year))
			page.select_option("#frmPrincipal\\:mes", value=str(doc.month))
			page.select_option("#frmPrincipal\\:dia", value=str(doc.day))
			doc_type_value = doc_type_map.get(doc.document_type)
			if doc_type_value:
				page.select_option("#frmPrincipal\\:cmbTipoComprobante", value=doc_type_value)

			# 3. Click search (This is the reCAPTCHA-protected step)
			# Note: This step is likely to fail if reCAPTCHA is active.
			page.locator("#btnRecaptcha").click()

			# 4. Wait for download link and download the file
			page.wait_for_selector("#frmPrincipal\\:lnkTxtlistado", timeout=timeout_ms)

			with page.expect_download() as download_info:
				page.locator("#frmPrincipal\\:lnkTxtlistado").click()

			download = download_info.value

			# Save the file temporarily
			temp_path = os.path.join("/tmp", download.suggested_filename)
			download.save_as(temp_path)

			# 5. Attach file to DocType
			with open(temp_path, "rb") as f:
				file_content = f.read()

			new_file = frappe.get_doc({
				"doctype": "File",
				"file_name": download.suggested_filename,
				"attached_to_doctype": "SRI Invoice Download",
				"attached_to_name": doc.name,
				"content": file_content,
				"is_private": 1
			})
			new_file.insert()
			os.remove(temp_path) # Clean up temporary file

			doc.status = "Completed"
			doc.save()
			frappe.db.commit()

		except Exception as e:
			doc.status = "Failed"
			doc.save()
			frappe.db.commit()
			screenshot_path = frappe.get_site_path("public", "files", f"sri_error_{doc.name}.png")
			page.screenshot(path=screenshot_path, full_page=True)
			frappe.log_error(title=f"SRI Download Failed for {doc.name}", message=frappe.get_traceback())
		finally:
			browser.close()

@frappe.whitelist()
def start_download(docname):
	"""
	Enqueues a background job to download invoices from the SRI portal.
	"""
	frappe.enqueue(
        "erpnext_ec.erpnext_ec.doctype.sri_invoice_download.sri_invoice_download._perform_sri_download",
        queue="long",
        timeout=1500,
        docname=docname
    )

	doc = frappe.get_doc("SRI Invoice Download", docname)
	doc.status = "In Progress"
	doc.save()
	frappe.db.commit()

	return _("Download process has been enqueued and is running in the background.")
