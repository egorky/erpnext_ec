# Copyright (c) 2025, Jules and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

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

    # Purchases Query
    # This query needs to be more complex because Purchase Invoice does not have summary fields
    # for tax bases. We must calculate them from the child table.
    compras_query = f"""
        SELECT
            'Purchase Invoice' as tipo,
            pi.posting_date as fecha,
            pi.name as documento,
            pi.supplier_name as tercero,
            SUM(CASE WHEN tax.rate = 0 THEN tax.base_tax_amount ELSE 0 END) as base_cero,
            SUM(CASE WHEN tax.rate > 0 THEN tax.base_tax_amount ELSE 0 END) as base_iva,
            SUM(CASE WHEN tax.rate > 0 THEN tax.tax_amount ELSE 0 END) as monto_iva,
            pi.grand_total as total,
            pi.docstatus as estado,
            sup.tax_id as ruc_tercero,
            pi.estab,
            pi.ptoemi,
            pi.secuencial,
            pi.numeroautorizacion,
            pi.is_return,
            pi.return_against
        FROM `tabPurchase Invoice` pi
        LEFT JOIN `tabSupplier` sup ON pi.supplier = sup.name
        LEFT JOIN `tabPurchase Taxes and Charges` tax ON tax.parent = pi.name
        WHERE pi.company = '{company}' AND pi.posting_date BETWEEN '{start_date}' AND '{end_date}'
        AND pi.docstatus IN (1, 2)
        GROUP BY pi.name
    """
    compras = frappe.db.sql(compras_query, as_dict=1)

    # Sales Query
    ventas = frappe.db.sql(f"""
        SELECT
            'Sales Invoice' as tipo,
            si.posting_date as fecha,
            si.name as documento,
            si.customer_name as tercero,
            si.total_base_cero as base_cero,
            si.total_base_iva as base_iva,
            si.total_iva as monto_iva,
            si.grand_total as total,
            si.docstatus as estado,
            cus.tax_id as ruc_tercero,
            si.estab,
            si.ptoemi,
            si.secuencial,
            si.numeroautorizacion,
            si.is_return,
            si.return_against
        FROM `tabSales Invoice` si
        LEFT JOIN `tabCustomer` cus ON si.customer = cus.name
        WHERE si.company = '{company}' AND si.posting_date BETWEEN '{start_date}' AND '{end_date}'
        AND si.docstatus IN (1, 2)
    """, as_dict=1)

    data = compras + ventas

    # Process status
    for row in data:
        if row.estado == 1:
            row.estado = "Emitido"
        elif row.estado == 2:
            row.estado = "Anulado"

    return data

@frappe.whitelist()
def get_regional_settings():
    try:
        settings = frappe.get_doc("Regional Settings Ec")
        return {
            "send_sri_manual": settings.send_sri_manual
        }
    except frappe.DoesNotExistError:
        return {
            "send_sri_manual": 0
        }

@frappe.whitelist()
def send_ats_to_sri(filters):
    # This function would contain the logic to send the generated ATS XML to the SRI.
    # Since the web service endpoint and request format for ATS are unknown without
    # the official technical specification, this is a placeholder.
    frappe.msgprint(_("La funcionalidad de envío al SRI para el ATS aún no está implementada."))
    return {"status": "not_implemented"}

@frappe.whitelist()
def generate_xml(data, filters):
    company = filters.get("company")
    year = filters.get("year")
    month = filters.get("month")

    company_doc = frappe.get_doc("Company", company)

    total_ventas = sum(d['total'] for d in data if d['tipo'] == 'Sales Invoice' and d['estado'] == 'Emitido')

    root = ET.Element("iva")
    ET.SubElement(root, "TipoIDInformante").text = "R" # RUC
    ET.SubElement(root, "IdInformante").text = company_doc.tax_id
    ET.SubElement(root, "razonSocial").text = company_doc.company_name
    ET.SubElement(root, "Anio").text = year
    ET.SubElement(root, "Mes").text = month
    ET.SubElement(root, "totalVentas").text = f"{total_ventas:.2f}"
    ET.SubElement(root, "codigoOperativo").text = "IVA"

    # Compras
    compras_xml = ET.SubElement(root, "compras")
    for row in data:
        if row['tipo'] == 'Purchase Invoice' and row['estado'] == 'Emitido':
            detalle = ET.SubElement(compras_xml, "detalleCompras")
            # NOTE: This is a simplified structure. The official ATS requires more specific tags.
            # This is based on the provided example and will need refinement based on the official spec.
            ET.SubElement(detalle, "tpIdProv").text = "01" # TODO: Map from data
            ET.SubElement(detalle, "idProv").text = row.get("ruc_tercero", "")
            ET.SubElement(detalle, "tipoComp").text = "01" # TODO: Map from data
            ET.SubElement(detalle, "aut").text = row.get("numeroautorizacion", "")
            ET.SubElement(detalle, "estab").text = row.get("estab", "")
            ET.SubElement(detalle, "ptoEmi").text = row.get("ptoemi", "")
            ET.SubElement(detalle, "sec").text = row.get("secuencial", "")
            ET.SubElement(detalle, "fechaEmision").text = row.get("fecha").strftime("%d/%m/%Y")
            ET.SubElement(detalle, "baseImponible").text = f"{row.get('base_cero', 0):.2f}"
            ET.SubElement(detalle, "baseImpGrav").text = f"{row.get('base_iva', 0):.2f}"
            ET.SubElement(detalle, "montoIva").text = f"{row.get('monto_iva', 0):.2f}"

    # Ventas
    ventas_xml = ET.SubElement(root, "ventas")
    for row in data:
        if row['tipo'] == 'Sales Invoice' and row['estado'] == 'Emitido':
            detalle = ET.SubElement(ventas_xml, "detalleVentas")
            ET.SubElement(detalle, "tipoEmision").text = "F" # Físico
            ET.SubElement(detalle, "tpIdCliente").text = "04" # TODO: Map from data
            ET.SubElement(detalle, "idCliente").text = row.get("ruc_tercero", "")
            ET.SubElement(detalle, "tipoComprobante").text = "18" # TODO: Map from data
            ET.SubElement(detalle, "nroComprobantes").text = "1" # Assuming 1 per row
            ET.SubElement(detalle, "baseImponible").text = f"{row.get('base_cero', 0):.2f}"
            ET.SubElement(detalle, "baseImpGrav").text = f"{row.get('base_iva', 0):.2f}"
            ET.SubElement(detalle, "montoIva").text = f"{row.get('monto_iva', 0):.2f}"
            ET.SubElement(detalle, "valorRetIva").text = "0.00" # TODO
            ET.SubElement(detalle, "valorRetRenta").text = "0.00" # TODO


    # Anulados
    anulados_xml = ET.SubElement(root, "anulados")
    for row in data:
        if row['estado'] == 'Anulado':
            detalle = ET.SubElement(anulados_xml, "detalleAnulados")
            ET.SubElement(detalle, "tipoComprobante").text = "01" # TODO: Map from data
            ET.SubElement(detalle, "establecimiento").text = row.get("estab", "")
            ET.SubElement(detalle, "puntoEmision").text = row.get("ptoemi", "")
            ET.SubElement(detalle, "secuencialInicio").text = row.get("secuencial", "")
            ET.SubElement(detalle, "secuencialFin").text = row.get("secuencial", "")
            ET.SubElement(detalle, "autorizacion").text = row.get("numeroautorizacion", "")

    # Pretty print
    xml_str = ET.tostring(root, 'utf-8')
    parsed_str = minidom.parseString(xml_str)
    pretty_xml_str = parsed_str.toprettyxml(indent="  ", encoding="utf-8")

    file_name = f"ATS-{year}-{month}.xml"

    return {
        "file_name": file_name,
        "file_content": pretty_xml_str
    }
