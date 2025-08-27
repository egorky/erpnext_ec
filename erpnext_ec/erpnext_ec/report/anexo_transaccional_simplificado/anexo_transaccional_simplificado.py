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

    # Purchases Query
    compras_query = f"""
        SELECT
            'Purchase Invoice' as tipo,
            pi.posting_date as fecha,
            pi.name as documento,
            pi.supplier_name as tercero,
            IFNULL(SUM(CASE WHEN tax.rate = 0 THEN tax.base_tax_amount ELSE 0 END), 0) as base_cero,
            IFNULL(SUM(CASE WHEN tax.rate > 0 THEN tax.base_tax_amount ELSE 0 END), 0) as base_iva,
            IFNULL(SUM(CASE WHEN tax.rate > 0 THEN tax.tax_amount ELSE 0 END), 0) as monto_iva,
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
    ventas_query = f"""
        SELECT
            'Sales Invoice' as tipo,
            si.posting_date as fecha,
            si.name as documento,
            si.customer_name as tercero,
            IFNULL(SUM(CASE WHEN tax.rate = 0 THEN tax.base_tax_amount ELSE 0 END), 0) as base_cero,
            IFNULL(SUM(CASE WHEN tax.rate > 0 THEN tax.base_tax_amount ELSE 0 END), 0) as base_iva,
            IFNULL(SUM(CASE WHEN tax.rate > 0 THEN tax.tax_amount ELSE 0 END), 0) as monto_iva,
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
        LEFT JOIN `tabSales Taxes and Charges` tax ON tax.parent = si.name
        WHERE si.company = '{company}' AND si.posting_date BETWEEN '{start_date}' AND '{end_date}'
        AND si.docstatus IN (1, 2)
        GROUP BY si.name
    """
    ventas = frappe.db.sql(ventas_query, as_dict=1)

    data = compras + ventas

    # Process status and add placeholders
    for row in data:
        if row.estado == 1:
            row.estado = "Emitido"
        elif row.estado == 2:
            row.estado = "Anulado"

        # Add other placeholder fields needed for XML
        row.codSustento = "01"
        row.tpIdProv = "02"
        row.idProv = row.ruc_tercero
        row.tipoComprobante = "01"
        # ... etc.

    return data

@frappe.whitelist()
def get_regional_settings(company):
    if not company:
        return {"send_sri_manual": 0}

    try:
        settings_doc_name = frappe.db.get_value("Company", company, "regional_settings_ec")
        if not settings_doc_name:
            return {"send_sri_manual": 0}

        settings = frappe.get_doc("Regional Settings Ec", settings_doc_name)
        return {
            "send_sri_manual": settings.send_sri_manual
        }
    except Exception as e:
        frappe.log_error(f"Error fetching regional settings for {company}: {e}")
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
    if isinstance(filters, str):
        filters = json.loads(filters)

    if isinstance(data, str):
        data = json.loads(data)

    company = filters.get("company")
    year = filters.get("year")
    month = filters.get("month")

    for row in data:
        if isinstance(row.get("fecha"), str):
            row["fecha"] = datetime.strptime(row["fecha"], "%Y-%m-%d")
        if isinstance(row.get("fechaRegistro"), str):
            row["fechaRegistro"] = datetime.strptime(row["fechaRegistro"], "%Y-%m-%d")
        if isinstance(row.get("fechaEmision"), str):
            row["fechaEmision"] = datetime.strptime(row["fechaEmision"], "%Y-%m-%d")

    company_doc = frappe.get_doc("Company", company)
    num_estab_ruc = frappe.db.count("Sri Establishment", {"company_link": company})

    total_ventas = sum(d.get('total', 0) for d in data if d.get('tipo') == 'Sales Invoice' and d.get('estado') == 'Emitido')

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
    for row in data:
        if row.get('tipo') == 'Purchase Invoice' and row.get('estado') == 'Emitido':
            detalle = ET.SubElement(compras_xml, "detalleCompras")
            ET.SubElement(detalle, "codSustento").text = str(row.get("codSustento", ""))
            ET.SubElement(detalle, "tpIdProv").text = str(row.get("tpIdProv", ""))
            ET.SubElement(detalle, "idProv").text = str(row.get("idProv", ""))
            ET.SubElement(detalle, "tipoComprobante").text = str(row.get("tipoComprobante", ""))
            ET.SubElement(detalle, "tipoProv").text = str(row.get("tipoProv", ""))
            ET.SubElement(detalle, "denoProv").text = str(row.get("denoProv", ""))
            ET.SubElement(detalle, "parteRel").text = str(row.get("parteRel", "NO"))
            ET.SubElement(detalle, "fechaRegistro").text = row.get("fechaRegistro").strftime("%d/%m/%Y")
            ET.SubElement(detalle, "establecimiento").text = str(row.get("estab", ""))
            ET.SubElement(detalle, "puntoEmision").text = str(row.get("ptoemi", ""))
            ET.SubElement(detalle, "secuencial").text = str(row.get("secuencial", ""))
            ET.SubElement(detalle, "fechaEmision").text = row.get("fechaEmision").strftime("%d/%m/%Y")
            ET.SubElement(detalle, "autorizacion").text = str(row.get("autorizacion", ""))
            ET.SubElement(detalle, "baseNoGraIva").text = str(row.get("baseNoGraIva", "0.00"))
            ET.SubElement(detalle, "baseImponible").text = str(row.get("baseImponible", "0.00"))
            ET.SubElement(detalle, "baseImpGrav").text = str(row.get("baseImpGrav", "0.00"))
            ET.SubElement(detalle, "baseImpExe").text = str(row.get("baseImpExe", "0.00"))
            ET.SubElement(detalle, "montoIce").text = str(row.get("montoIce", "0.00"))
            ET.SubElement(detalle, "montoIva").text = str(row.get("montoIva", "0.00"))
            ET.SubElement(detalle, "valRetBien10").text = str(row.get("valRetBien10", "0.00"))
            ET.SubElement(detalle, "valRetServ20").text = str(row.get("valRetServ20", "0.00"))
            ET.SubElement(detalle, "valorRetBienes").text = str(row.get("valorRetBienes", "0.00"))
            ET.SubElement(detalle, "valRetServ50").text = str(row.get("valRetServ50", "0.00"))
            ET.SubElement(detalle, "valorRetServicios").text = str(row.get("valorRetServicios", "0.00"))
            ET.SubElement(detalle, "valRetServ100").text = str(row.get("valRetServ100", "0.00"))
            ET.SubElement(detalle, "valorRetencionNc").text = str(row.get("valorRetencionNc", "0.00"))
            ET.SubElement(detalle, "totbasesImpReemb").text = str(row.get("totbasesImpReemb", "0.00"))
            pago_exterior = ET.SubElement(detalle, "pagoExterior")
            ET.SubElement(pago_exterior, "pagoLocExt").text = str(row.get("pagoLocExt", "01"))
            ET.SubElement(pago_exterior, "paisEfecPago").text = "NA"
            ET.SubElement(pago_exterior, "aplicConvDobTrib").text = "NA"
            ET.SubElement(pago_exterior, "pagExtSujRetNorLeg").text = "NA"

            if row.get("air_details"):
                air = ET.SubElement(detalle, "air")
                for air_row in row.get("air_details"):
                    detalle_air = ET.SubElement(air, "detalleAir")
                    ET.SubElement(detalle_air, "codRetAir").text = str(air_row.get("codRetAir", ""))
                    ET.SubElement(detalle_air, "baseImpAir").text = f"{air_row.get('baseImpAir', 0):.2f}"
                    ET.SubElement(detalle_air, "porcentajeAir").text = f"{air_row.get('porcentajeAir', 0):.2f}"
                    ET.SubElement(detalle_air, "valRetAir").text = f"{air_row.get('valRetAir', 0):.2f}"

    ventas_xml = ET.SubElement(root, "ventas")
    ventas_est_xml = ET.SubElement(root, "ventasEstablecimiento")
    venta_est = ET.SubElement(ventas_est_xml, "ventaEst")
    ET.SubElement(venta_est, "codEstab").text = "001"
    ET.SubElement(venta_est, "ventasEstab").text = "0.00"
    ET.SubElement(venta_est, "ivaComp").text = "0.00"

    anulados_xml = ET.SubElement(root, "anulados")
    for row in data:
        if row.get('estado') == 'Anulado':
            detalle = ET.SubElement(anulados_xml, "detalleAnulados")
            ET.SubElement(detalle, "tipoComprobante").text = str(row.get("tipoComprobante", ""))
            ET.SubElement(detalle, "establecimiento").text = str(row.get("estab", ""))
            ET.SubElement(detalle, "puntoEmision").text = str(row.get("ptoemi", ""))
            ET.SubElement(detalle, "secuencialInicio").text = str(row.get("secuencial", ""))
            ET.SubElement(detalle, "secuencialFin").text = str(row.get("secuencial", ""))
            ET.SubElement(detalle, "autorizacion").text = str(row.get("autorizacion", ""))

    xml_str = ET.tostring(root, 'utf-8')
    parsed_str = minidom.parseString(xml_str)
    pretty_xml_str = parsed_str.toprettyxml(indent="  ")

    file_name = f"ATS-{year}-{month}.xml"

    return {
        "file_name": file_name,
        "file_content": pretty_xml_str
    }
