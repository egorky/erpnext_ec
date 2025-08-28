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
	from pydoll.browser import Chrome
	from pydoll.browser.options import ChromiumOptions as Options
	from pydoll.exceptions import FailedToStartBrowser

	doc = frappe.get_doc("SRI Invoice Download", docname)
	settings = _get_settings()

	username = settings.sri_username
	password = settings.get_password("sri_password")

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

	browser = None
	try:
		frappe.log_error(f"Attempting to launch browser with path: {options.binary_location}")
		browser = await Chrome(options=options)
		tab = await browser.start()
		frappe.log_error("Browser started successfully.")

		# 1. Login
		await tab.go_to(settings.sri_login_url)
		await asyncio.sleep(random.uniform(1, 3))
		await (await tab.find(id='usuario')).type_text(username, delay=random.uniform(50, 150))
		await (await tab.find(id='password')).type_text(password, delay=random.uniform(50, 150))
		await asyncio.sleep(random.uniform(0.5, 1.5))
		await (await tab.find(id='kc-login')).click()

		# 2. Navigate
		await tab.wait_for(timeout=random.uniform(3, 5))
		await tab.go_to(settings.sri_target_url)
		await tab.wait_for(timeout=random.uniform(2, 4))

		# 3. Set parameters
		await (await tab.find(id='frmPrincipal:ano')).select(label=str(doc.year))
		await (await tab.find(id='frmPrincipal:mes')).select(value=str(doc.month))
		await (await tab.find(id='frmPrincipal:dia')).select(value=str(doc.day))

		doc_type_value = doc_type_map.get(doc.document_type)
		if doc_type_value:
			await (await tab.find(id='frmPrincipal:cmbTipoComprobante')).select(value=doc_type_value)

		await asyncio.sleep(random.uniform(1, 2))

		# 4. Click search (reCAPTCHA) and download
		async with tab.expect_download(timeout=settings.timeout or 60) as download:
			await (await tab.find(id='btnRecaptcha')).click()
			await tab.wait_for(5)
			await (await tab.find(id='frmPrincipal:lnkTxtlistado')).click()
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

		doc.status = "Completed"
		doc.save(ignore_permissions=True)
		frappe.db.commit()

	except FailedToStartBrowser as e:
		frappe.log_error(title="Pydoll: Failed to Start Browser", message=f"pydoll could not launch the browser. Path: {options.binary_location}. Error: {e}")
		raise
	except Exception as e:
		screenshot_path = frappe.get_site_path("public", "files", f"sri_error_{doc.name}.png")
		if tab:
			await tab.screenshot(path=screenshot_path, full_page=True)
		frappe.log_error(title=f"SRI Download Failed for {doc.name}", message=frappe.get_traceback())
		raise
	finally:
		if browser:
			await browser.stop()

def _perform_sri_download(docname):
    doc = frappe.get_doc("SRI Invoice Download", docname)
    try:
        asyncio.run(_perform_sri_download_async(docname))
    except Exception as e:
        doc.status = "Failed"
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        # The exception is already logged inside the async function,
        # but we log a general failure message here for the background job log.
        frappe.log_error(title=f"SRI Download Job Failed for {docname}", message="See previous log for detailed traceback.")

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
