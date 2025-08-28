# Copyright (c) 2025, Jules and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_password

class SRIInvoiceDownload(Document):
	pass

def _get_settings():
	return frappe.get_doc("SRI Downloader Settings")

from playwright.sync_api import sync_playwright

def _perform_sri_download(settings, from_date, to_date):
	"""
	This function contains the Playwright web scraping logic.
	It logs in, navigates to the download page, and takes a screenshot.
	"""
	# Get credentials securely
	username = settings.sri_username
	password = get_password("SRI Downloader Settings", "sri_password")

	with sync_playwright() as p:
		browser = p.chromium.launch(headless=True)
		page = browser.new_page()

		try:
			# 1. Navigate to login page
			frappe.log_error("Navigating to SRI login page...")
			page.goto(settings.sri_login_url, wait_until='networkidle')

			# 2. Fill credentials and login
			frappe.log_error("Filling login credentials...")
			page.locator("#usuario").fill(username)
			page.locator("#password").fill(password)
			page.locator("#kc-login").click()

			# Wait for successful login navigation
			page.wait_for_url("**/tuportal-internet/**", timeout=30000)
			frappe.log_error("Login successful.")

			# 3. Navigate to the target download application
			frappe.log_error(f"Navigating to target URL: {settings.sri_target_url}")
			page.goto(settings.sri_target_url, wait_until='networkidle')

			# 4. Take a screenshot to verify we reached the page
			screenshot_path = frappe.get_site_path("public", "files", "sri_download_page.png")
			page.screenshot(path=screenshot_path, full_page=True)
			frappe.log_error(f"Screenshot of download page saved to: {screenshot_path}")

			# At this point, the user would need to solve reCAPTCHA and select dates.
			# The logic to do that would be implemented here.

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

	# Get credentials securely
	username = settings.sri_username
	password = get_password("SRI Downloader Settings", "sri_password")

	if not username or not password:
		frappe.throw(_("SRI Username and Password must be set in SRI Downloader Settings."))

	try:
		doc.status = "In Progress"
		doc.save()
		frappe.db.commit()

		# Call the actual scraping function
		_perform_sri_download(settings, doc.from_date, doc.to_date)

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
