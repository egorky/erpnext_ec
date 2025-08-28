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

	options = Options()
	options.binary_location = "/usr/bin/chromium"
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-dev-shm-usage')
	options.add_argument('--disable-gpu')

	browser = None
	tab = None
	try:
		browser = Chrome(options=options)
		tab = await browser.start()

		await tab.go_to(settings.sri_login_url)

		usuario_input = await tab.find(id='usuario', timeout=10)
		await usuario_input.type_text(username)
		hidden_username_input = await tab.find(id='username', raise_exc=False)
		if hidden_username_input:
			await tab.execute_script(f"document.getElementById('username').value = '{username}';")

		password_input = await tab.find(id='password', timeout=10)
		await password_input.type_text(password)

		login_button = await tab.find(id='kc-login', timeout=10)
		await login_button.click()

		# Generous wait to see what page we land on after login attempt
		await asyncio.sleep(10)

		# This part of the code will now likely fail, which is intended.
		# The goal is to capture the HTML of the page we are on after the 10-second wait.
		await tab.go_to(settings.sri_target_url)

		# If it gets here, it means login was successful
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
    try:
        asyncio.run(_perform_sri_download_async(docname))
    except Exception:
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
