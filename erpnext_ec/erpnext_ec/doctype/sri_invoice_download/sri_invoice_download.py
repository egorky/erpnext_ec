# Copyright (c) 2025, Jules and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import asyncio
import os
import base64

class SRIInvoiceDownload(Document):
	pass

def _get_settings():
	return frappe.get_doc("SRI Downloader Settings")

def _get_chrome_executable_path():
	"""
	Dynamically finds the path to the Playwright-installed Chromium executable.
	"""
	try:
		home_dir = os.path.expanduser('~')
		playwright_cache_path = os.path.join(home_dir, '.cache', 'ms-playwright')

		if not os.path.isdir(playwright_cache_path):
			return None

		for item in os.listdir(playwright_cache_path):
			if item.startswith('chromium-') and os.path.isdir(os.path.join(playwright_cache_path, item)):
				executable_path = os.path.join(playwright_cache_path, item, 'chrome-linux', 'chrome')
				if os.path.exists(executable_path):
					return executable_path
		return None
	except Exception:
		# If any error occurs during path finding, return None safely.
		return None

async def _perform_sri_download_pydoll(docname):
	from pydoll.browser.chromium import Chrome
	from pydoll.browser.options import ChromiumOptions
	from pydoll.constants import By

	def log_debug(message):
		frappe.log_error(title="Pydoll Debug", message=message)

	log_debug("Starting Pydoll download process...")
	doc = frappe.get_doc("SRI Invoice Download", docname)
	settings = _get_settings()
	log_debug("Settings loaded.")

	username = settings.sri_username
	password = settings.get_password("sri_password")
	timeout_s = settings.timeout or 60

	if not username or not password:
		log_debug("Error: SRI Username or Password not set.")
		raise ValueError("SRI Username and Password must be set.")

	doc_type_map = {
		"Factura": "1",
		"Liquidación de compra de bienes y prestación de services": "2",
		"Notas de Crédito": "3",
		"Notas de Débito": "4",
		"Comprobante de Retención": "6"
	}

	log_debug("Setting Chromium options...")
	options = ChromiumOptions()

	chrome_path = _get_chrome_executable_path()
	if not chrome_path:
		log_debug("Chromium executable not found in Playwright cache.")
		raise FileNotFoundError("Could not find Playwright's Chromium executable. Please ensure Playwright is installed correctly (`playwright install chromium`).")

	options.binary_location = chrome_path
	options.add_argument('--headless=new')
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-dev-shm-usage')
	log_debug(f"Chromium options set with binary location: {options.binary_location}")

	async with Chrome(options=options) as browser:
		page = None
		try:
			log_debug("Chrome launched. Starting browser...")
			await browser.start()
			page = await browser.get_page()
			log_debug("Browser started and page object acquired.")

			# 1. Login and navigate
			log_debug(f"Navigating to login URL: {settings.sri_login_url}")
			await page.go_to(settings.sri_login_url, timeout=timeout_s)
			log_debug("Login page loaded. Waiting for stability...")
			await asyncio.sleep(3)

			# Retry logic for filling credentials
			last_exception = None
			for attempt in range(3):
				try:
					log_debug(f"Attempt {attempt + 1} to fill credentials.")
					user_field = await page.find_element(By.CSS_SELECTOR, "#usuario")
					await user_field.fill(username)

					pass_field = await page.find_element(By.CSS_SELECTOR, "#password")
					await pass_field.fill(password)

					log_debug("Credentials filled successfully.")
					last_exception = None
					break
				except KeyError as e:
					log_debug(f"Attempt {attempt + 1} failed with KeyError. Retrying in 3 seconds...")
					last_exception = e
					await asyncio.sleep(3)

			if last_exception:
				raise last_exception

			log_debug("Clicking login button.")
			await (await page.find_element(By.CSS_SELECTOR, "#kc-login")).click()

			log_debug("Waiting for network idle after login.")
			await page.wait_for_load_state('networkidle', timeout=timeout_s)
			log_debug(f"Navigating to target URL: {settings.sri_target_url}")
			await page.go_to(settings.sri_target_url, wait_until='networkidle', timeout=timeout_s)
			log_debug("Target page loaded.")

			# 2. Set download parameters
			log_debug("Setting download parameters...")
			await (await page.find_element(By.CSS_SELECTOR, "#frmPrincipal\\:ano")).select(str(doc.year))
			await (await page.find_element(By.CSS_SELECTOR, "#frmPrincipal\\:mes")).select(value=str(doc.month))
			await (await page.find_element(By.CSS_SELECTOR, "#frmPrincipal\\:dia")).select(value=str(doc.day))
			doc_type_value = doc_type_map.get(doc.document_type)
			if doc_type_value:
				await (await page.find_element(By.CSS_SELECTOR, "#frmPrincipal\\:cmbTipoComprobante")).select(value=doc_type_value)
			log_debug("Download parameters set.")

			# 3. Click search
			log_debug("Clicking search button (btnRecaptcha)...")
			await (await page.find_element(By.CSS_SELECTOR, "#btnRecaptcha")).click()
			log_debug("Search button clicked.")

			# 4. Intercept download
			log_debug("Waiting for download link selector...")
			await page.wait_for_selector("#frmPrincipal\\:lnkTxtlistado", timeout=timeout_s)
			log_debug("Download link found.")

			download_event = asyncio.Event()
			download_content = None
			file_name = "default_filename.txt"

			async def on_request_paused(event):
				nonlocal download_content, file_name
				log_debug(f"Request paused: {event.request.url}")
				if "frmPrincipal:j_idt160" in event.request.url:
					log_debug("Download request intercepted. Getting response body.")
					response = await page.get_response_body(event.request_id)
					download_content = base64.b64decode(response['body'])
					for header in event.response_headers:
						if header['name'].lower() == 'content-disposition':
							parts = header['value'].split(';')
							for part in parts:
								if part.strip().startswith('filename='):
									file_name = part.split('=')[1].strip('"')
									break
					await page.continue_request(event.request_id)
					download_event.set()
				else:
					await page.continue_request(event.request_id)

			page.on('fetch.requestPaused', on_request_paused)
			log_debug("Enabling fetch interception.")
			await page.enable_fetch_interception(handle_auth_requests=False)
			log_debug("Clicking final download link.")
			await (await page.find_element(By.CSS_SELECTOR, "#frmPrincipal\\:lnkTxtlistado")).click()
			log_debug("Waiting for download event...")
			await asyncio.wait_for(download_event.wait(), timeout=timeout_s)
			log_debug("Download event received. Disabling interception.")
			await page.disable_fetch_interception()

			if not download_content:
				raise Exception("Failed to download file.")

			# 5. Attach file to DocType
			log_debug(f"Attaching file {file_name} to document {doc.name}")
			temp_path = os.path.join("/tmp", file_name)
			with open(temp_path, "wb") as f:
				f.write(download_content)
			with open(temp_path, "rb") as f:
				file_content = f.read()
			new_file = frappe.get_doc({
				"doctype": "File", "file_name": file_name,
				"attached_to_doctype": "SRI Invoice Download", "attached_to_name": doc.name,
				"content": file_content, "is_private": 1
			})
			new_file.insert()
			os.remove(temp_path)
			log_debug("File attached successfully. Pydoll process complete.")

		except Exception as e:
			if page:
				screenshot_path = frappe.get_site_path("public", "files", f"sri_error_{doc.name}.png")
				log_debug(f"Pydoll process failed. Taking screenshot to {screenshot_path}")
				await page.get_screenshot(path=screenshot_path)
			raise e


def _perform_sri_download_playwright(docname):
	from playwright.sync_api import sync_playwright

	doc = frappe.get_doc("SRI Invoice Download", docname)
	settings = _get_settings()
	username = settings.sri_username
	password = settings.get_password("sri_password")
	timeout_ms = (settings.timeout or 60) * 1000

	if not username or not password:
		raise ValueError("SRI Username and Password must be set.")

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
			page.goto(settings.sri_login_url, timeout=timeout_ms)
			page.locator("#usuario").fill(username)
			page.locator("#password").fill(password)
			page.locator("#kc-login").click()
			page.wait_for_load_state('networkidle', timeout=timeout_ms)
			page.goto(settings.sri_target_url, wait_until='networkidle', timeout=timeout_ms)
			page.select_option("#frmPrincipal\\:ano", label=str(doc.year))
			page.select_option("#frmPrincipal\\:mes", value=str(doc.month))
			page.select_option("#frmPrincipal\\:dia", value=str(doc.day))
			doc_type_value = doc_type_map.get(doc.document_type)
			if doc_type_value:
				page.select_option("#frmPrincipal\\:cmbTipoComprobante", value=doc_type_value)
			page.locator("#btnRecaptcha").click()
			page.wait_for_selector("#frmPrincipal\\:lnkTxtlistado", timeout=timeout_ms)
			with page.expect_download() as download_info:
				page.locator("#frmPrincipal\\:lnkTxtlistado").click()
			download = download_info.value
			temp_path = os.path.join("/tmp", download.suggested_filename)
			download.save_as(temp_path)
			with open(temp_path, "rb") as f:
				file_content = f.read()
			new_file = frappe.get_doc({
				"doctype": "File", "file_name": download.suggested_filename,
				"attached_to_doctype": "SRI Invoice Download", "attached_to_name": doc.name,
				"content": file_content, "is_private": 1
			})
			new_file.insert()
			os.remove(temp_path)

			doc.status = "Completed"
			doc.save()
			frappe.db.commit()

		except Exception as e:
			screenshot_path = frappe.get_site_path("public", "files", f"sri_error_{doc.name}.png")
			page.screenshot(path=screenshot_path, full_page=True)
			frappe.log_error(title=f"SRI Download Failed for {doc.name}", message=frappe.get_traceback())
			raise e # Re-raise the exception to be caught by the main dispatcher
		finally:
			browser.close()


def _perform_sri_download(docname):
	doc = frappe.get_doc("SRI Invoice Download", docname)
	settings = _get_settings()

	try:
		if settings.downloader_library == "Pydoll":
			asyncio.run(_perform_sri_download_pydoll(docname))
			doc.status = "Completed"
			doc.save(ignore_version=True)
			frappe.db.commit()
		else: # Default to Playwright
			_perform_sri_download_playwright(docname)

	except Exception as e:
		# Use ignore_version=True to prevent TimestampMismatchError if the doc was
		# modified while the background job was running.
		doc_to_fail = frappe.get_doc("SRI Invoice Download", docname)
		doc_to_fail.status = "Failed"
		doc_to_fail.save(ignore_version=True)
		frappe.db.commit()
		# Log any exception that was not caught and logged by the specific downloaders.
		# This is crucial for debugging failures during the initialization phase (e.g., browser not found).
		frappe.log_error(title=f"SRI Download Failed for {doc.name}", message=frappe.get_traceback())


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
