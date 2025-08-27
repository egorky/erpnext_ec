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

    # This query is a simplified version and will need to be expanded
    # to include all the fields from the example XML, especially withholding taxes (air).
    # This will require joining with the withholding doctype.

    # Using frappe.get_all for better maintainability for now
    compras = frappe.get_all("Purchase Invoice",
        filters={
            "company": company,
            "posting_date": ["between", [start_date, end_date]],
            "docstatus": ["in", [1, 2]]
        },
        fields=[
            "'Purchase Invoice' as tipo", "posting_date as fecha", "name as documento",
            "supplier_name as tercero", "grand_total as total", "docstatus as estado",
            "supplier", "estab", "ptoemi", "secuencial", "numeroautorizacion", "is_return", "return_against"
        ]
    )

    ventas = frappe.get_all("Sales Invoice",
        filters={
            "company": company,
            "posting_date": ["between", [start_date, end_date]],
            "docstatus": ["in", [1, 2]]
        },
        fields=[
            "'Sales Invoice' as tipo", "posting_date as fecha", "name as documento",
            "customer_name as tercero", "grand_total as total", "docstatus as estado",
            "customer", "estab", "ptoemi", "secuencial", "numeroautorizacion", "is_return", "return_against"
        ]
    )

    data = compras + ventas

    for row in data:
        # Add placeholder fields to match XML structure, these need to be populated with real data
        row.codSustento = "01" # Placeholder
        row.tpIdProv = "02" # Placeholder
        row.idProv = frappe.db.get_value("Supplier", row.supplier, "tax_id") if row.tipo == 'Purchase Invoice' else frappe.db.get_value("Customer", row.customer, "tax_id")
        row.tipoComprobante = "01" # Placeholder
        row.tipoProv = "01" # Placeholder
        row.denoProv = row.tercero
        row.parteRel = "NO"
        row.fechaRegistro = row.fecha
        row.fechaEmision = row.fecha
        row.autorizacion = row.numeroautorizacion
        row.baseNoGraIva = "0.00"
        row.baseImponible = "0.00"
        row.baseImpGrav = "0.00"
        row.baseImpExe = "0.00"
        row.montoIce = "0.00"
        row.montoIva = "0.00"
        row.valRetBien10 = "0.00"
        row.valRetServ20 = "0.00"
        row.valorRetBienes = "0.00"
        row.valRetServ50 = "0.00"
        row.valorRetServicios = "0.00"
        row.valRetServ100 = "0.00"
        row.valorRetencionNc = "0.00"
        row.totbasesImpReemb = "0.00"
        row.pagoLocExt = "01"

        # Placeholder for AIR details
        row.air_details = []

        if row.estado == 1:
            row.estado = "Emitido"
        elif row.estado == 2:
            row.estado = "Anulado"

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
        "file_content": pretty_xml_str.decode('utf-8')
    }
