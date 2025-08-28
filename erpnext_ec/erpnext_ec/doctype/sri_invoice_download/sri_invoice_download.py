# Copyright (c) 2025, Jules and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class SRIInvoiceDownload(Document):
	pass

def _get_settings():
	return frappe.get_doc("SRI Downloader Settings")

def _perform_sri_download(doc, settings):
	from playwright.sync_api import sync_playwright
	"""
	This function contains the Playwright web scraping logic.
	It logs in, navigates, selects options, and takes a screenshot.
	"""
	username = settings.sri_username
	password = settings.get_password("sri_password")
	timeout_ms = (settings.timeout or 60) * 1000

	if not username or not password:
		frappe.throw(_("SRI Username and Password must be set in SRI Downloader Settings."))

	# Mapping from DocType options to SRI form values
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
			# 1. Login
			frappe.log_error("Navigating to SRI login page...")
			page.goto(settings.sri_login_url, timeout=timeout_ms)
			page.locator("#usuario").fill(username)
			page.locator("#password").fill(password)
			page.locator("#kc-login").click()
			page.wait_for_load_state('networkidle', timeout=timeout_ms)
			frappe.log_error("Login successful.")

			# 2. Navigate to download page
			frappe.log_error(f"Navigating to target URL: {settings.sri_target_url}")
			page.goto(settings.sri_target_url, wait_until='networkidle', timeout=timeout_ms)
			frappe.log_error("Navigation to download page successful.")

			# 3. Select download options
			frappe.log_error("Selecting download parameters...")
			page.select_option("#frmPrincipal\\:ano", label=str(doc.year))
			page.select_option("#frmPrincipal\\:mes", value=str(doc.month))
			page.select_option("#frmPrincipal\\:dia", value=str(doc.day))

			doc_type_value = doc_type_map.get(doc.document_type)
			if doc_type_value:
				page.select_option("#frmPrincipal\\:cmbTipoComprobante", value=doc_type_value)

			frappe.log_error(f"Parameters set: {doc.year}/{doc.month}/{doc.day}, Type: {doc.document_type}")

			# 4. Take a screenshot to verify
			screenshot_path = frappe.get_site_path("public", "files", "sri_download_page_with_options.png")
			page.screenshot(path=screenshot_path, full_page=True)
			frappe.log_error(f"Screenshot of download page saved to: {screenshot_path}")

		except Exception as e:
			screenshot_path = frappe.get_site_path("public", "files", "sri_error.png")
			page.screenshot(path=screenshot_path, full_page=True)
			frappe.log_error(f"An error occurred during web scraping. Screenshot saved to: {screenshot_path}")
			raise
		finally:
			browser.close()

@frappe.whitelist()
def start_download(docname):
	"""
	Starts the process of downloading invoices from the SRI portal.
	"""
	doc = frappe.get_doc("SRI Invoice Download", docname)
	settings = _get_settings()

	try:
		doc.status = "In Progress"
		doc.save()
		frappe.db.commit()

		# Call the actual scraping function
		_perform_sri_download(doc, settings)

		doc.status = "Completed"
		doc.save()
		frappe.db.commit()

		return _("Download process finished.")

	except Exception as e:
		doc.status = "Failed"
		doc.save()
		frappe.db.commit()
		frappe.log_error(title="SRI Download Failed", message=frappe.get_traceback())
		frappe.throw(_("An error occurred during the download process. Please check the Error Log for details."))
