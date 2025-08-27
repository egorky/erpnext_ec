from frappe import _

def get_data():
	return [
		{
			"module_name": "Erpnext Ec",
			"color": "#AABBCC",
			"icon": "octicon octicon-file-directory",
			"type": "module",
			"label": _("Erpnext Ec"),
			"description": "ERPNext Ecuador"
		},
		{
			"module_name": "Erpnext Ec",
			"label": _("Reportes"),
			"icon": "fa fa-list-alt",
			"type": "section",
			"items": [
				{
					"type": "report",
					"name": "Anexo Transaccional Simplificado",
					"doctype": "Sales Invoice",
					"is_query_report": True
				}
			]
		}
	]
