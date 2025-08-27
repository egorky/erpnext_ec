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
    data = get_data(filters)

    return columns, data

def get_columns(filters):
    columns = [
        {"label": _("Tipo"), "fieldname": "tipo", "fieldtype": "Data", "width": 100},
        {"label": _("Fecha"), "fieldname": "fecha", "fieldtype": "Date", "width": 100},
        {"label": _("Documento"), "fieldname": "documento", "fieldtype": "Dynamic Link", "options": "tipo", "width": 150},
        {"label": _("Tercero"), "fieldname": "tercero", "fieldtype": "Data", "width": 200},
        {"label": _("Base Imponible 0%"), "fieldname": "base_cero", "fieldtype": "Currency", "width": 120},
        {"label": _("Base Imponible IVA"), "fieldname": "base_iva", "fieldtype": "Currency", "width": 120},
        {"label": _("Monto IVA"), "fieldname": "monto_iva", "fieldtype": "Currency", "width": 120},
        {"label": _("Total"), "fieldname": "total", "fieldtype": "Currency", "width": 120},
        {"label": _("Estado"), "fieldname": "estado", "fieldtype": "Data", "width": 100},
    ]
    return columns

def get_data(filters):
    year = filters.get("year")
    month = filters.get("month")
    company = filters.get("company")

    start_date = f"{year}-{month}-01"
    end_date = datetime.strptime(start_date, "%Y-%m-%d").replace(day=28) + frappe.utils.relativedelta(days=4)
    end_date = (end_date - frappe.utils.relativedelta(days=end_date.day - 1)).strftime("%Y-%m-%d")

    compras = frappe.get_all("Purchase Invoice",
        filters={"company": company, "posting_date": ["between", [start_date, end_date]], "docstatus": ["in", [1, 2]]},
        fields=["name as documento", "posting_date as fecha", "supplier_name as tercero", "grand_total as total", "docstatus"]
    )
    for c in compras: c['tipo'] = 'Purchase Invoice'

    ventas = frappe.get_all("Sales Invoice",
        filters={"company": company, "posting_date": ["between", [start_date, end_date]], "docstatus": ["in", [1, 2]]},
        fields=["name as documento", "posting_date as fecha", "customer_name as tercero", "grand_total as total", "docstatus"]
    )
    for v in ventas: v['tipo'] = 'Sales Invoice'

    data = compras + ventas

    for row in data:
        taxes = get_tax_details(row.tipo, row.documento)
        row.update(taxes)
        row["estado"] = "Anulado" if row.docstatus == 2 else "Emitido"

    return data

def get_tax_details(doctype, docname):
    child_table = "Purchase Taxes and Charges" if doctype == "Purchase Invoice" else "Sales Taxes and Charges"
    taxes = frappe.get_all(child_table, filters={"parent": docname}, fields=["rate", "tax_amount", "base_tax_amount"])

    base_cero = sum(t.base_tax_amount for t in taxes if t.rate == 0)
    base_iva = sum(t.base_tax_amount for t in taxes if t.rate > 0)
    monto_iva = sum(t.tax_amount for t in taxes if t.rate > 0)

    return {"base_cero": base_cero, "base_iva": base_iva, "monto_iva": monto_iva}

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
    if isinstance(data, str): data = json.loads(data)

    company = filters.get("company")
    year = filters.get("year")
    month = filters.get("month")

    processed_data = []
    for row in data:
        doc = frappe.get_doc(row.get("tipo"), row.get("documento"))
        taxes = get_tax_details(doc.doctype, doc.name)

        p_row = {
            "tipo": doc.doctype,
            "fecha": doc.posting_date,
            "estado": "Anulado" if doc.docstatus == 2 else "Emitido",
            "secuencial": doc.secuencial,
            "autorizacion": doc.numeroautorizacion,
            "baseNoGraIva": taxes.get("base_cero", 0),
            "baseImpGrav": taxes.get("base_iva", 0),
            "montoIva": taxes.get("monto_iva", 0),
        }

        if doc.doctype == 'Purchase Invoice':
            p_row["denoProv"] = doc.supplier_name
            p_row["idProv"] = frappe.db.get_value("Supplier", doc.supplier, "tax_id")
            p_row["tpIdProv"] = frappe.db.get_value("Supplier", doc.supplier, "typeidtax")
            p_row["codSustento"] = "01"
            p_row["tipoProv"] = "01"
            p_row["parteRel"] = "NO"
            p_row["pagoLocExt"] = "01"

            if doc.is_purchase_settlement:
                p_row["tipoComprobante"] = "03"
                p_row["estab"] = frappe.db.get_value("Sri Establishment", doc.estab_link, "record_name") if doc.estab_link else ""
                p_row["ptoEmi"] = frappe.db.get_value("Sri Ptoemi", doc.ptoemi_link, "record_name") if doc.ptoemi_link else ""
            else:
                p_row["tipoComprobante"] = "01"
                p_row["estab"] = doc.estab
                p_row["ptoEmi"] = doc.ptoemi

        elif doc.doctype == 'Sales Invoice':
            p_row["idCliente"] = frappe.db.get_value("Customer", doc.customer, "tax_id")
            p_row["tpIdCliente"] = frappe.db.get_value("Customer", doc.customer, "typeidtax")
            p_row["tipoComprobante"] = "04" if doc.is_return else "01"
            p_row["estab"] = doc.estab
            p_row["ptoEmi"] = doc.ptoemi

        processed_data.append(p_row)

    company_doc = frappe.get_doc("Company", company)
    num_estab_ruc = frappe.db.count("Sri Establishment", {"company_link": company})
    total_ventas = sum(float(d.get('total', 0) or 0) for d in data if d.get('tipo') == 'Sales Invoice' and d.get('estado') == 'Emitido')

    root = ET.Element("iva")
    ET.SubElement(root, "TipoIDInformante").text = "R"
    ET.SubElement(root, "IdInformante").text = str(company_doc.tax_id)
    ET.SubElement(root, "razonSocial").text = str(company_doc.company_name)
    ET.SubElement(root, "Anio").text = str(year)
    ET.SubElement(root, "Mes").text = str(month).zfill(2)
    ET.SubElement(root, "numEstabRuc").text = str(num_estab_ruc).zfill(3) if num_estab_ruc else "001"
    ET.SubElement(root, "totalVentas").text = f"{total_ventas:.2f}"
    ET.SubElement(root, "codigoOperativo").text = "IVA"

    compras_xml = ET.SubElement(root, "compras")
    for row in processed_data:
        if row.get('tipo') == 'Purchase Invoice' and row.get('estado') == 'Emitido':
            detalle = ET.SubElement(compras_xml, "detalleCompras")
            ET.SubElement(detalle, "codSustento").text = str(row.get("codSustento") or "")
            ET.SubElement(detalle, "tpIdProv").text = str(row.get("tpIdProv") or "")
            ET.SubElement(detalle, "idProv").text = str(row.get("idProv") or "")
            ET.SubElement(detalle, "tipoComprobante").text = str(row.get("tipoComprobante") or "")
            ET.SubElement(detalle, "fechaRegistro").text = row.get("fecha").strftime("%d/%m/%Y")
            ET.SubElement(detalle, "establecimiento").text = str(row.get("estab") or "")
            ET.SubElement(detalle, "puntoEmision").text = str(row.get("ptoEmi") or "")
            ET.SubElement(detalle, "secuencial").text = str(row.get("secuencial") or "")
            ET.SubElement(detalle, "fechaEmision").text = row.get("fecha").strftime("%d/%m/%Y")
            ET.SubElement(detalle, "autorizacion").text = str(row.get("autorizacion") or "")
            ET.SubElement(detalle, "baseNoGraIva").text = f"{row.get('baseNoGraIva', 0):.2f}"
            ET.SubElement(detalle, "baseImponible").text = f"{row.get('baseImpGrav', 0):.2f}"
            ET.SubElement(detalle, "montoIva").text = f"{row.get('montoIva', 0):.2f}"
            # ... add other placeholders ...

    ventas_xml = ET.SubElement(root, "ventas")
    for row in processed_data:
        if row.get('tipo') == 'Sales Invoice' and row.get('estado') == 'Emitido':
            detalle = ET.SubElement(ventas_xml, "detalleVentas")
            ET.SubElement(detalle, "tpIdCliente").text = str(row.get("tpIdCliente") or "")
            ET.SubElement(detalle, "idCliente").text = str(row.get("idCliente") or "")
            ET.SubElement(detalle, "tipoComprobante").text = str(row.get("tipoComprobante") or "")
            ET.SubElement(detalle, "nroComprobantes").text = "1"
            ET.SubElement(detalle, "baseNoGraIva").text = f"{row.get('baseNoGraIva', 0):.2f}"
            ET.SubElement(detalle, "baseImponible").text = "0.00"
            ET.SubElement(detalle, "baseImpGrav").text = f"{row.get('baseImpGrav', 0):.2f}"
            ET.SubElement(detalle, "montoIva").text = f"{row.get('montoIva', 0):.2f}"
            ET.SubElement(detalle, "valorRetIva").text = "0.00"
            ET.SubElement(detalle, "valorRetRenta").text = "0.00"

    anulados_xml = ET.SubElement(root, "anulados")
    for row in processed_data:
        if row.get('estado') == 'Anulado':
            detalle = ET.SubElement(anulados_xml, "detalleAnulados")
            ET.SubElement(detalle, "tipoComprobante").text = str(row.get("tipoComprobante") or "")
            ET.SubElement(detalle, "establecimiento").text = str(row.get("estab") or "")
            ET.SubElement(detalle, "puntoEmision").text = str(row.get("ptoEmi") or "")
            ET.SubElement(detalle, "secuencialInicio").text = str(row.get("secuencial") or "")
            ET.SubElement(detalle, "secuencialFin").text = str(row.get("secuencial") or "")
            ET.SubElement(detalle, "autorizacion").text = str(row.get("autorizacion") or "")

    xml_str = ET.tostring(root, 'utf-8', xml_declaration=True)
    parsed_str = minidom.parseString(xml_str)
    pretty_xml_str = parsed_str.toprettyxml(indent="  ")

    file_name = f"ATS-{year}-{month}.xml"
    return {"file_name": file_name, "file_content": pretty_xml_str}
