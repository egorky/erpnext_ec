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

async def _perform_sri_download_pydoll(docname):
	from pydoll.browser.chromium import Chrome
	from pydoll.browser.options import ChromiumOptions

	doc = frappe.get_doc("SRI Invoice Download", docname)
	settings = _get_settings()

	username = settings.sri_username
	password = settings.get_password("sri_password")
	timeout_s = settings.timeout or 60

	if not username or not password:
		raise ValueError("SRI Username and Password must be set.")

	doc_type_map = {
		"Factura": "1",
		"Liquidación de compra de bienes y prestación de services": "2",
		"Notas de Crédito": "3",
		"Notas de Débito": "4",
		"Comprobante de Retención": "6"
	}

	options = ChromiumOptions()
	options.add_argument('--headless=new')
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-dev-shm-usage')

	async with Chrome(options=options) as browser:
		tab = await browser.start()

		# 1. Login and navigate
		await tab.go_to(settings.sri_login_url, timeout=timeout_s)
		await (await tab.find("#usuario")).fill(username)
		await (await tab.find("#password")).fill(password)
		await (await tab.find("#kc-login")).click()

		await tab.wait_for_load_state('networkidle', timeout=timeout_s)
		await tab.go_to(settings.sri_target_url, wait_until='networkidle', timeout=timeout_s)

		# 2. Set download parameters
		await (await tab.find("#frmPrincipal\\:ano")).select(str(doc.year))
		await (await tab.find("#frmPrincipal\\:mes")).select(value=str(doc.month))
		await (await tab.find("#frmPrincipal\\:dia")).select(value=str(doc.day))
		doc_type_value = doc_type_map.get(doc.document_type)
		if doc_type_value:
			await (await tab.find("#frmPrincipal\\:cmbTipoComprobante")).select(value=doc_type_value)

		# 3. Click search (relying on Pydoll to handle the reCAPTCHA)
		await (await tab.find("#btnRecaptcha")).click()

		# 4. Intercept download
		await tab.wait_for_selector("#frmPrincipal\\:lnkTxtlistado", timeout=timeout_s)

		download_event = asyncio.Event()
		download_content = None
		file_name = "default_filename.txt" # Default filename

		async def on_request_paused(event):
			nonlocal download_content, file_name
			# A simple check to see if it's our file download request
			if "frmPrincipal:j_idt160" in event.request.url:
				response = await tab.get_response_body(event.request_id)
				download_content = base64.b64decode(response['body'])

				# Try to get filename from content-disposition header
				for header in event.response_headers:
					if header['name'].lower() == 'content-disposition':
						parts = header['value'].split(';')
						for part in parts:
							if part.strip().startswith('filename='):
								file_name = part.split('=')[1].strip('"')
								break

				await tab.continue_request(event.request_id)
				download_event.set()
			else:
				await tab.continue_request(event.request_id)

		tab.on('fetch.requestPaused', on_request_paused)
		await tab.enable_fetch_interception(handle_auth_requests=False)

		await (await tab.find("#frmPrincipal\\:lnkTxtlistado")).click()

		await asyncio.wait_for(download_event.wait(), timeout=timeout_s)
		await tab.disable_fetch_interception()

		if not download_content:
			raise Exception("Failed to download file.")

		# 5. Attach file to DocType
		temp_path = os.path.join("/tmp", file_name)
		with open(temp_path, "wb") as f:
			f.write(download_content)

		with open(temp_path, "rb") as f:
			file_content = f.read()

		new_file = frappe.get_doc({
			"doctype": "File",
			"file_name": file_name,
			"attached_to_doctype": "SRI Invoice Download",
			"attached_to_name": doc.name,
			"content": file_content,
			"is_private": 1
		})
		new_file.insert()
		os.remove(temp_path)


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
		finally:
			browser.close()


def _perform_sri_download(docname):
	doc = frappe.get_doc("SRI Invoice Download", docname)
	settings = _get_settings()

	try:
		if settings.downloader_library == "Pydoll":
			asyncio.run(_perform_sri_download_pydoll(docname))
		else: # Default to Playwright
			_perform_sri_download_playwright(docname)

		doc.status = "Completed"
		doc.save()
		frappe.db.commit()

	except Exception as e:
		doc.status = "Failed"
		doc.save()
		frappe.db.commit()
		# Pydoll doesn't have a direct screenshot method in the same way,
		# so we log the error without a screenshot for now.
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
