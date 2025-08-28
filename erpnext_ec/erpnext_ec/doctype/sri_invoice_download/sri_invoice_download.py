# Copyright (c) 2025, Jules and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import asyncio
import os
import random

class SRIInvoiceDownload(Document):
	pass

def _get_settings():
	return frappe.get_doc("SRI Downloader Settings")

async def _perform_sri_download_async(docname):
	from pyvirtualdisplay import Display
	from pydoll.browser import Chrome
	from pydoll.browser.options import ChromiumOptions as Options
	from pydoll.exceptions import FailedToStartBrowser, ElementNotFound

	doc = frappe.get_doc("SRI Invoice Download", docname)
	settings = _get_settings()

	username = settings.sri_username
	password = settings.get_password("sri_password")
	timeout_seconds = settings.timeout or 60

	if not username or not password:
		raise ValueError("SRI Username and Password must be set.")

	doc_type_map = {
		"Factura": "1",
		"Liquidación de compra de bienes y prestación de servicios": "2",
		"Notas de Crédito": "3",
		"Notas de Débito": "4",
		"Comprobante de Retención": "6"
	}

	options = Options()
	options.binary_location = "/usr/bin/chromium"
	options.add_argument('--window-size=1920,1080')
	options.add_argument('--start-maximized')
	options.add_argument('--disable-infobars')
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-dev-shm-usage')
	options.add_argument('--disable-gpu')
	options.add_argument(f"--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")

	with Display():
		browser = None
		tab = None
		try:
			browser = Chrome(options=options)
			tab = await browser.start()
			await browser.set_window_bounds({'left': 0, 'top': 0, 'width': 1920, 'height': 1080})

			# 1. Login
			await tab.go_to(settings.sri_login_url, timeout=timeout_seconds)
			usuario_input = await tab.find(id='usuario', timeout=timeout_seconds)
			await usuario_input.type_text(username)
			password_input = await tab.find(id='password', timeout=timeout_seconds)
			await password_input.type_text(password)
			await (await tab.find(id='kc-login', timeout=timeout_seconds)).click()

			# 2. Navigate
			await tab.go_to(settings.sri_target_url, timeout=timeout_seconds)

			# 3. Set parameters
			await (await tab.query('[id="frmPrincipal:ano"]', timeout=timeout_seconds)).select(label=str(doc.year))
			await (await tab.query('[id="frmPrincipal:mes"]', timeout=timeout_seconds)).select(value=str(doc.month))
			await (await tab.query('[id="frmPrincipal:dia"]', timeout=timeout_seconds)).select(value=str(doc.day))
			doc_type_value = doc_type_map.get(doc.document_type)
			if doc_type_value:
				await (await tab.query('[id="frmPrincipal:cmbTipoComprobante"]', timeout=timeout_seconds)).select(value=doc_type_value)

			# 4. Click search (reCAPTCHA) and download
			async with tab.expect_download(timeout=timeout_seconds) as download:
				await (await tab.find(id='btnRecaptcha', timeout=timeout_seconds)).click()
				download_link = await tab.query('[id="frmPrincipal:lnkTxtlistado"]', timeout=timeout_seconds)
				await download_link.click()
				temp_path = await download.save_as('/tmp/')

			# 5. Attach file to DocType
			with open(temp_path, "rb") as f:
				file_content = f.read()
			new_file = frappe.get_doc({
				"doctype": "File", "file_name": os.path.basename(temp_path),
				"attached_to_doctype": "SRI Invoice Download", "attached_to_name": doc.name,
				"content": file_content, "is_private": 1
			})
			new_file.insert(ignore_permissions=True)
			os.remove(temp_path)

			doc.reload()
			doc.status = "Completed"
			doc.save(ignore_permissions=True)
			frappe.db.commit()

		except Exception as e:
			doc.reload()
			doc.status = "Failed"
			doc.save(ignore_permissions=True)
			frappe.db.commit()

			if isinstance(e, FailedToStartBrowser):
				frappe.log_error(title="Pydoll: Failed to Start Browser", message=f"pydoll could not launch the browser. Path: {options.binary_location}. Error: {e}")
			else:
				screenshot_path = frappe.get_site_path("public", "files", f"sri_error_{doc.name}.png")
				if tab:
					body = await tab.find(tag_name='body')
					if body:
						await body.take_screenshot(path=screenshot_path)
						frappe.log_error(f"Screenshot of error page saved to: {screenshot_path}")
				frappe.log_error(title=f"SRI Download Failed for {doc.name}", message=frappe.get_traceback())
			raise
		finally:
			if browser:
				await browser.stop()

def _perform_sri_download(docname):
    # The wrapper's only job is to run the async function.
    # All error handling and doc updates are now inside the async function.
    try:
        asyncio.run(_perform_sri_download_async(docname))
    except Exception:
        # The error is already logged by the async function.
        # We just catch it here to prevent the RQ worker from crashing.
        frappe.log_error(f"Async task for {docname} failed and was caught by sync wrapper.")

@frappe.whitelist()
def start_download(docname):
	"""
	Enqueues a background job to download invoices from the SRI portal.
	"""
	frappe.enqueue(
        "erpnext_ec.erpnext_ec.doctype.sri_invoice_download.sri_invoice_download._perform_sri_download",
        queue="long", timeout=1500, docname=docname
    )

	doc = frappe.get_doc("SRI Invoice Download", docname)
	doc.status = "In Progress"
	doc.save()
	frappe.db.commit()

	return _("Download process has been enqueued and is running in the background.")
