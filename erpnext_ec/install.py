from __future__ import unicode_literals
from frappe import __version__ as frappe_version
import frappe
import json
import os
#from frappe.utils import validate_email_address, split_emails
from erpnext_ec.patches.v15_0.custom_fields import *

import click
# from ec_extend.setup import after_install as setup

def before_install():
	print('before_install')
	#print('Eliminando columnas de datos del modo antiguo')
	#remove_old_columns()

def after_install():
	import subprocess
	import sys
	try:
		print("Setting ErpNext Ecuador...")

		click.secho("Installing Playwright browsers...", fg="yellow")
		try:
			subprocess.run(
				[sys.executable, "-m", "playwright", "install", "--with-deps"],
				check=True,
				capture_output=True,
				text=True
			)
			click.secho("Playwright browsers installed successfully.", fg="green")
		except subprocess.CalledProcessError as e:
			click.secho(f"Playwright browser installation failed: {e.stderr}", fg="bright_red")
			frappe.log_error(title="Playwright Install Failed", message=e.stderr)
		except FileNotFoundError:
			click.secho("Playwright command not found. Please ensure 'playwright' is in requirements.txt.", fg="bright_red")

		click.secho("Thank you for installing ErpNext Ecuador!", fg="green")

	except Exception as e:
		#BUG_REPORT_URL = "https://github.com/frappe/hrms/issues/new"
		#click.secho(
	#		"Installation for ErpNext Ecuador app failed due to an error."
	#		" Please try re-installing the app or"
#			f" report the issue on {BUG_REPORT_URL} if not resolved.",
#			fg="bright_red",
		#)

		click.secho(
			"Installation for ErpNext Ecuador app failed due to an error."
			" Please try re-installing the app.",
			fg="bright_red",
		)

		raise e	
	