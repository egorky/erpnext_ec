# Copyright (c) 2025, Jules and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json

def execute(filters=None):
    columns = get_columns(filters)
    data = get_data_for_view(filters)
    return columns, data

def get_columns(filters):
    return [
        {"label": _("Tipo"), "fieldname": "tipo", "fieldtype": "Data", "width": 100},
        {"label": _("Documento"), "fieldname": "documento", "fieldtype": "Dynamic Link", "options": "tipo", "width": 180},
        {"label": _("Fecha"), "fieldname": "fecha", "fieldtype": "Date", "width": 100},
        {"label": _("Tercero"), "fieldname": "tercero", "fieldtype": "Data", "width": 250},
        {"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 120},
        {"label": _("Estado"), "fieldname": "estado", "fieldtype": "Data", "width": 100},
    ]

def get_data_for_view(filters):
    docs = get_raw_docs(filters)
    data = []
    for doc in docs:
        data.append({
            "tipo": doc.doctype,
            "documento": doc.name,
            "fecha": doc.posting_date,
            "tercero": doc.get("supplier_name") or doc.get("customer_name"),
            "total": doc.grand_total,
            "estado": "Anulado" if doc.docstatus == 2 else "Emitido"
        })
    return data

def get_raw_docs(filters):
    year = filters.get("year")
    month = filters.get("month")
    company = filters.get("company")

    start_date = f"{year}-{month}-01"
    end_date = datetime.strptime(start_date, "%Y-%m-%d").replace(day=28) + frappe.utils.relativedelta(days=4)
    end_date = (end_date - frappe.utils.relativedelta(days=end_date.day - 1)).strftime("%Y-%m-%d")

    # Get all fields needed for processing, DO NOT include 'doctype' in the fields list
    purchase_fields = ["name", "posting_date", "supplier", "supplier_name", "grand_total", "docstatus", "is_purchase_settlement", "estab", "ptoemi", "secuencial", "numeroautorizacion", "estab_link", "ptoemi_link"]
    sales_fields = ["name", "posting_date", "customer", "customer_name", "grand_total", "docstatus", "is_return", "estab", "ptoemi", "secuencial", "numeroautorizacion"]

    compras = frappe.get_all("Purchase Invoice",
        filters=[
            ["company", "=", company],
            ["posting_date", "between", [start_date, end_date]],
            ["docstatus", "in", [1, 2]],
            ["numeroautorizacion", "is", "set"],
            ["numeroautorizacion", "!=", ""]
        ],
        fields=purchase_fields
    )
    for c in compras:
        c.doctype = "Purchase Invoice"

    ventas = frappe.get_all("Sales Invoice",
        filters={"company": company, "posting_date": ["between", [start_date, end_date]], "docstatus": ["in", [1, 2]]},
        fields=sales_fields
    )
    for v in ventas:
        v.doctype = "Sales Invoice"

    return compras + ventas

def get_tax_details(doctype, docname):
    child_table = "Purchase Taxes and Charges" if doctype == "Purchase Invoice" else "Sales Taxes and Charges"
    taxes = frappe.get_all(child_table, filters={"parent": docname}, fields=["rate", "tax_amount", "base_tax_amount"])

    base_cero = sum(t.base_tax_amount for t in taxes if t.rate == 0)
    base_iva = sum(t.base_tax_amount for t in taxes if t.rate > 0)
    monto_iva = sum(t.tax_amount for t in taxes if t.rate > 0)

    return {"baseNoGraIva": base_cero, "baseImpGrav": base_iva, "montoIva": monto_iva}

@frappe.whitelist()
def get_regional_settings(company):
    if not company: return {"send_sri_manual": 0}
    try:
        settings_doc_name = frappe.db.get_value("Company", company, "regional_settings_ec")
        if not settings_doc_name: return {"send_sri_manual": 0}
        settings = frappe.get_doc("Regional Settings Ec", settings_doc_name)
        return {"send_sri_manual": settings.send_sri_manual}
    except Exception as e:
        frappe.log_error(f"Error fetching regional settings for {company}: {e}")
        return {"send_sri_manual": 0}

@frappe.whitelist()
def send_ats_to_sri(filters):
    frappe.msgprint(_("La funcionalidad de envío al SRI para el ATS aún no está implementada."))
    return {"status": "not_implemented"}

@frappe.whitelist()
def generate_xml(data, filters):
    if isinstance(filters, str): filters = json.loads(filters)

    docs = get_raw_docs(filters)

    company = filters.get("company")
    year = filters.get("year")
    month = filters.get("month")

    company_doc = frappe.get_doc("Company", company)
    num_estab_ruc = frappe.db.count("Sri Establishment", {"company_link": company})
    total_ventas = sum(d.grand_total for d in docs if d.doctype == 'Sales Invoice' and d.docstatus == 1)

    root = ET.Element("iva")
    ET.SubElement(root, "TipoIDInformante").text = "R"
    ET.SubElement(root, "IdInformante").text = str(company_doc.tax_id)
    ET.SubElement(root, "razonSocial").text = str(company_doc.company_name)
    ET.SubElement(root, "Anio").text = str(year)
    ET.SubElement(root, "Mes").text = str(month).zfill(2)
    ET.SubElement(root, "numEstabRuc").text = str(num_estab_ruc or "1").zfill(3)
    ET.SubElement(root, "totalVentas").text = f"{total_ventas:.2f}"
    ET.SubElement(root, "codigoOperativo").text = "IVA"

    compras_xml = ET.SubElement(root, "compras")
    ventas_xml = ET.SubElement(root, "ventas")
    anulados_xml = ET.SubElement(root, "anulados")

    for doc in docs:
        taxes = get_tax_details(doc.doctype, doc.name)

        # --- Data Enrichment ---
        if doc.doctype == 'Purchase Invoice':
            doc.tpIdProv = frappe.db.get_value("Supplier", doc.supplier, "typeidtax")
            doc.idProv = frappe.db.get_value("Supplier", doc.supplier, "tax_id")
            if doc.is_purchase_settlement:
                doc.tipoComprobante = "03"
                doc.estab = frappe.db.get_value("Sri Establishment", doc.estab_link, "record_name")
                doc.ptoEmi = frappe.db.get_value("Sri Ptoemi", doc.ptoemi_link, "record_name")
            else:
                doc.tipoComprobante = "01"
        elif doc.doctype == 'Sales Invoice':
            doc.tpIdCliente = frappe.db.get_value("Customer", doc.customer, "typeidtax")
            doc.idCliente = frappe.db.get_value("Customer", doc.customer, "tax_id")
            doc.tipoComprobante = "04" if doc.is_return else "01"

        # --- XML Building ---
        if doc.docstatus == 1: # EMITIDO
            if doc.doctype == 'Purchase Invoice':
                detalle = ET.SubElement(compras_xml, "detalleCompras")
                ET.SubElement(detalle, "codSustento").text = "01"
                ET.SubElement(detalle, "tpIdProv").text = str(doc.tpIdProv or "")
                ET.SubElement(detalle, "idProv").text = str(doc.idProv or "")
                ET.SubElement(detalle, "tipoComprobante").text = str(doc.tipoComprobante or "")
                ET.SubElement(detalle, "fechaRegistro").text = doc.posting_date.strftime("%d/%m/%Y")
                ET.SubElement(detalle, "establecimiento").text = str(doc.estab or "").zfill(3)
                ET.SubElement(detalle, "puntoEmision").text = str(doc.ptoEmi or "").zfill(3)
                ET.SubElement(detalle, "secuencial").text = str(doc.secuencial or "")
                ET.SubElement(detalle, "fechaEmision").text = doc.posting_date.strftime("%d/%m/%Y")
                ET.SubElement(detalle, "autorizacion").text = str(doc.numeroautorizacion or "")
                ET.SubElement(detalle, "baseNoGraIva").text = f"{taxes.get('baseNoGraIva', 0):.2f}"
                ET.SubElement(detalle, "baseImponible").text = "0.00"
                ET.SubElement(detalle, "baseImpGrav").text = f"{taxes.get('baseImpGrav', 0):.2f}"
                ET.SubElement(detalle, "montoIva").text = f"{taxes.get('montoIva', 0):.2f}"
                # ... add other purchase placeholders ...
            elif doc.doctype == 'Sales Invoice':
                detalle = ET.SubElement(ventas_xml, "detalleVentas")
                ET.SubElement(detalle, "tpIdCliente").text = str(doc.tpIdCliente or "")
                ET.SubElement(detalle, "idCliente").text = str(doc.idCliente or "")
                ET.SubElement(detalle, "tipoComprobante").text = str(doc.tipoComprobante or "")
                ET.SubElement(detalle, "nroComprobantes").text = "1"
                ET.SubElement(detalle, "baseNoGraIva").text = f"{taxes.get('baseNoGraIva', 0):.2f}"
                ET.SubElement(detalle, "baseImponible").text = "0.00"
                ET.SubElement(detalle, "baseImpGrav").text = f"{taxes.get('baseImpGrav', 0):.2f}"
                ET.SubElement(detalle, "montoIva").text = f"{taxes.get('montoIva', 0):.2f}"
                ET.SubElement(detalle, "valorRetIva").text = "0.00"
                ET.SubElement(detalle, "valorRetRenta").text = "0.00"

        elif doc.docstatus == 2: # ANULADO
            detalle = ET.SubElement(anulados_xml, "detalleAnulados")
            ET.SubElement(detalle, "tipoComprobante").text = str(doc.tipoComprobante or "")
            ET.SubElement(detalle, "establecimiento").text = str(doc.estab or "").zfill(3)
            ET.SubElement(detalle, "puntoEmision").text = str(doc.ptoEmi or "").zfill(3)
            ET.SubElement(detalle, "secuencialInicio").text = str(doc.secuencial or "")
            ET.SubElement(detalle, "secuencialFin").text = str(doc.secuencial or "")
            ET.SubElement(detalle, "autorizacion").text = str(doc.numeroautorizacion or "")

    xml_str = ET.tostring(root, 'utf-8', xml_declaration=True)
    parsed_str = minidom.parseString(xml_str)
    pretty_xml_str = parsed_str.toprettyxml(indent="  ")

    file_name = f"ATS-{year}-{month}.xml"
    return {"file_name": file_name, "file_content": pretty_xml_str}
