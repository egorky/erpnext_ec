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
    end_date = (datetime.strptime(start_date, "%Y-%m-%d").replace(day=28) + frappe.utils.relativedelta(days=4))
    end_date = (end_date - frappe.utils.relativedelta(days=end_date.day)).strftime("%Y-%m-%d")

    # Fields needed for processing
    purchase_fields = [
        "name", "posting_date", "supplier", "supplier_name", "grand_total", "docstatus",
        "is_purchase_settlement", "estab", "ptoemi", "secuencial", "numeroautorizacion",
        "estab_link", "ptoemi_link", "bill_date", "coddocmodificado", "mode_of_payment"
    ]
    sales_fields = [
        "name", "posting_date", "customer", "customer_name", "grand_total", "net_total", "docstatus",
        "is_return", "estab", "ptoemi", "secuencial", "numeroautorizacion",
        "coddocmodificado"
    ]

    # Fetch Purchase Invoices
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

    # Fetch Sales Invoices
    ventas = frappe.get_all("Sales Invoice",
        filters={
            "company": company,
            "posting_date": ["between", [start_date, end_date]],
            "docstatus": ["in", [1, 2]]
        },
        fields=sales_fields
    )
    for v in ventas:
        v.doctype = "Sales Invoice"

    return compras + ventas

def _enrich_data(docs):
    """
    Enriches the raw document list with details from related doctypes
    to avoid making database calls inside the main loop.
    """
    doc_map = {"Purchase Invoice": {}, "Sales Invoice": {}}
    party_ids = {"Supplier": set(), "Customer": set()}

    for doc in docs:
        doc_map[doc.doctype][doc.name] = doc
        if doc.doctype == "Purchase Invoice" and doc.supplier:
            party_ids["Supplier"].add(doc.supplier)
        elif doc.doctype == "Sales Invoice" and doc.customer:
            party_ids["Customer"].add(doc.customer)

    party_details = _get_party_details(party_ids)
    tax_details = _get_tax_details(doc_map)
    payment_details = _get_payment_details_for_sales(list(doc_map["Sales Invoice"].keys()))

    for doc in docs:
        doc.party_info = party_details.get(doc.doctype, {}).get(doc.supplier or doc.customer, {})
        doc.tax_info = tax_details.get(doc.name, {})
        if doc.doctype == 'Sales Invoice':
            doc.payment_info = payment_details.get(doc.name, {})

    return docs

def _get_party_details(party_ids):
    details = {"Purchase Invoice": {}, "Sales Invoice": {}}

    # Fetch Supplier details
    if party_ids["Supplier"]:
        supplier_fields = ["name", "tax_id", "typeidtax", "supplier_type"]
        suppliers = frappe.get_all("Supplier", filters={"name": ["in", list(party_ids["Supplier"])]}, fields=supplier_fields)
        for s in suppliers:
            supplier_type = s.get("supplier_type")
            # SRI Code: 01 -> Persona Natural, 02 -> Sociedad
            tipo_prov_code = "01" if supplier_type == "Individual" else "02"

            details["Purchase Invoice"][s.name] = {
                "idProv": s.tax_id,
                "tpIdProv": s.get("typeidtax"),
                "tipoProv": tipo_prov_code,
                "parteRel": "NO" # No field found in schema for this
            }

    # Fetch Customer details
    if party_ids["Customer"]:
        # Assuming 'parterel' does not exist on Customer either
        customer_fields = ["name", "tax_id", "typeidtax"]
        customers = frappe.get_all("Customer", filters={"name": ["in", list(party_ids["Customer"])]}, fields=customer_fields)
        for c in customers:
            details["Sales Invoice"][c.name] = {
                "idCliente": c.tax_id,
                "tpIdCliente": c.get("typeidtax"),
                "parteRelVtas": "NO" # No field found in schema for this
            }

    return details

def _get_tax_details(doc_map):
    pi_names = list(doc_map["Purchase Invoice"].keys())
    si_names = list(doc_map["Sales Invoice"].keys())

    tax_details = {}

    # --- Process Purchase Invoices ---
    if pi_names:
        # 1. Fetch all related tax documents
        purchase_taxes = frappe.get_all("Purchase Taxes and Charges",
            filters={"parent": ["in", pi_names]},
            fields=["parent", "account_head", "rate", "tax_amount", "base_tax_amount"])

        purchase_taxes_ec = frappe.get_all("Purchase Taxes and Charges Ec",
            filters={"parent": ["in", pi_names]},
            fields=["parent", "codigoRetencion", "baseImponible", "porcentajeRetener", "valorRetenido", "codDocSustento"])

        # 2. Get details for all involved accounts
        account_heads = {t.account_head for t in purchase_taxes}
        account_details = {}
        if account_heads:
            accounts = frappe.get_all("Account", filters={"name": ["in", list(account_heads)]}, fields=["name", "sricode", "is_withhold_account"])
            account_details = {a.name: a for a in accounts}

        # 3. Initialize tax details for each parent document
        for name in pi_names:
            tax_details[name] = {
                "baseNoGraIva": 0, "baseImpGrav": 0, "montoIva": 0, "baseImponible": 0,
                "baseImpExe": 0, "montoIce": 0, "air": [], "retIva": {}, "codSustento": "01"
            }

        # 4. Process standard taxes
        for t in purchase_taxes:
            parent_tax = tax_details[t.parent]
            acc = account_details.get(t.account_head)
            sri_code = acc.sricode if acc else None

            if sri_code == '3': # IVA
                parent_tax["baseImpGrav"] += t.base_tax_amount
                parent_tax["montoIva"] += t.tax_amount
            elif sri_code == '2': # IVA 0%
                parent_tax["baseImponible"] += t.base_tax_amount
            elif sri_code == '0': # No Objeto de Impuesto
                parent_tax["baseNoGraIva"] += t.base_tax_amount
            elif sri_code == '6': # Exento de IVA
                parent_tax["baseImpExe"] += t.base_tax_amount
            elif sri_code == '5': # ICE
                parent_tax["montoIce"] += t.tax_amount
            else: # Default fallback
                if t.rate > 0:
                    parent_tax["baseImpGrav"] += t.base_tax_amount
                    parent_tax["montoIva"] += t.tax_amount
                else:
                    parent_tax["baseNoGraIva"] += t.base_tax_amount

        # 5. Process withholding taxes (Taxes EC)
        for t_ec in purchase_taxes_ec:
            parent_tax = tax_details[t_ec.parent]
            parent_tax["codSustento"] = t_ec.codDocSustento or "01"

            if len(str(t_ec.codigoRetencion)) < 3:
                parent_tax["retIva"][t_ec.codigoRetencion] = parent_tax["retIva"].get(t_ec.codigoRetencion, 0) + t_ec.valorRetenido
            else:
                parent_tax["air"].append({
                    "codRetAir": t_ec.codigoRetencion,
                    "baseImpAir": t_ec.baseImponible,
                    "porcentajeAir": t_ec.porcentajeRetener,
                    "valRetAir": t_ec.valorRetenido
                })

    # --- Process Sales Invoices ---
    if si_names:
        sales_taxes = frappe.get_all("Sales Taxes and Charges",
            filters={"parent": ["in", si_names]},
            fields=["parent", "account_head", "rate", "tax_amount", "base_tax_amount"])

        account_heads = {t.account_head for t in sales_taxes}
        account_details = {}
        if account_heads:
            accounts = frappe.get_all("Account", filters={"name": ["in", list(account_heads)]}, fields=["name", "sricode"])
            account_details = {a.name: a for a in accounts}

        for name in si_names:
            tax_details[name] = {"baseNoGraIva": 0, "baseImpGrav": 0, "montoIva": 0, "baseImponible": 0, "baseImpExe": 0, "montoIce": 0}

        for t in sales_taxes:
            parent_tax = tax_details[t.parent]
            acc = account_details.get(t.account_head)
            sri_code = acc.sricode if acc else None

            if sri_code == '3':
                parent_tax["baseImpGrav"] += t.base_tax_amount
                parent_tax["montoIva"] += t.tax_amount
            elif sri_code == '2':
                parent_tax["baseImponible"] += t.base_tax_amount
            elif sri_code == '0':
                parent_tax["baseNoGraIva"] += t.base_tax_amount
            elif sri_code == '6':
                parent_tax["baseImpExe"] += t.base_tax_amount
            elif sri_code == '5':
                parent_tax["montoIce"] += t.tax_amount
            else: # Fallback
                if t.rate > 0:
                    parent_tax["baseImpGrav"] += t.base_tax_amount
                    parent_tax["montoIva"] += t.tax_amount
                else:
                    parent_tax["baseNoGraIva"] += t.base_tax_amount

    return tax_details

def _get_payment_details_for_sales(si_names):
    """
    Fetches payment method details for a list of Sales Invoices.
    Returns a dict mapping {sales_invoice_name: {'sri_codes': {'code1', 'code2'}}}.
    """
    if not si_names:
        return {}

    # 1. Find all payment entries linked to the given sales invoices
    pe_references = frappe.get_all("Payment Entry Reference",
        filters={
            "reference_doctype": "Sales Invoice",
            "reference_name": ["in", si_names]
        },
        fields=["parent", "reference_name"] # parent is the Payment Entry name
    )

    if not pe_references:
        return {}

    # 2. Get the mode of payment from the parent Payment Entry documents
    payment_entry_names = list({ref.parent for ref in pe_references})
    payment_entries = frappe.get_all("Payment Entry",
        filters={"name": ["in", payment_entry_names]},
        fields=["name", "mode_of_payment"]
    )

    pe_to_mop_map = {pe.name: pe.mode_of_payment for pe in payment_entries}

    # 3. Get the SRI code for each mode of payment
    mop_names = list({pe.mode_of_payment for pe in payment_entries if pe.mode_of_payment})
    mop_sri_codes = {}
    if mop_names:
        # Assuming 'sri_code' is a custom field on Mode of Payment
        mops = frappe.get_all("Mode of Payment",
            filters={"name": ["in", mop_names]},
            fields=["name", "sri_code"]
        )
        mop_sri_codes = {mop.name: mop.sri_code for mop in mops}

    # 4. Map the SRI codes back to the original sales invoices
    payment_details = {}
    for ref in pe_references:
        si_name = ref.reference_name
        pe_name = ref.parent

        mode_of_payment = pe_to_mop_map.get(pe_name)
        sri_code = mop_sri_codes.get(mode_of_payment)

        if sri_code:
            if si_name not in payment_details:
                payment_details[si_name] = {'sri_codes': set()}
            payment_details[si_name]['sri_codes'].add(sri_code)

    return payment_details

def _get_tipo_comprobante(doc):
    # Expanded logic for sales will be handled by grouping
    if doc.doctype == 'Purchase Invoice':
        if doc.is_return: return "04"
        if doc.get("is_debit_note"): return "05"
        if doc.is_purchase_settlement: return "03"
        return "01"
    elif doc.doctype == 'Sales Invoice':
        if doc.is_return: return "04"
        if doc.get("is_debit_note") or doc.coddocmodificado == '01': return "05"
        # Defaulting to 18 for standard invoices, can be overridden by other logic
        return "18"
    return ""

def _build_purchase_xml(parent_xml, doc):
    """Builds a <detalleCompras> element and appends it to parent_xml."""
    tax_info = doc.tax_info
    party_info = doc.party_info

    detalle = ET.SubElement(parent_xml, "detalleCompras")

    ET.SubElement(detalle, "codSustento").text = tax_info.get("codSustento", "01")
    ET.SubElement(detalle, "tpIdProv").text = party_info.get("tpIdProv", "")
    ET.SubElement(detalle, "idProv").text = party_info.get("idProv", "")
    ET.SubElement(detalle, "tipoComprobante").text = _get_tipo_comprobante(doc)
    ET.SubElement(detalle, "tipoProv").text = party_info.get("tipoProv", "")
    ET.SubElement(detalle, "denoProv").text = doc.supplier_name
    ET.SubElement(detalle, "parteRel").text = party_info.get("parteRel", "NO")
    ET.SubElement(detalle, "fechaRegistro").text = doc.posting_date.strftime("%d/%m/%Y")
    ET.SubElement(detalle, "establecimiento").text = str(doc.estab or "").zfill(3)
    ET.SubElement(detalle, "puntoEmision").text = str(doc.ptoEmi or "").zfill(3)
    ET.SubElement(detalle, "secuencial").text = str(doc.secuencial or "")
    ET.SubElement(detalle, "fechaEmision").text = (doc.bill_date or doc.posting_date).strftime("%d/%m/%Y")
    ET.SubElement(detalle, "autorizacion").text = str(doc.numeroautorizacion or "")

    ET.SubElement(detalle, "baseNoGraIva").text = f"{tax_info.get('baseNoGraIva', 0):.2f}"
    ET.SubElement(detalle, "baseImponible").text = f"{tax_info.get('baseImponible', 0):.2f}"
    ET.SubElement(detalle, "baseImpGrav").text = f"{tax_info.get('baseImpGrav', 0):.2f}"
    ET.SubElement(detalle, "baseImpExe").text = f"{tax_info.get('baseImpExe', 0):.2f}"
    ET.SubElement(detalle, "montoIce").text = f"{tax_info.get('montoIce', 0):.2f}"
    ET.SubElement(detalle, "montoIva").text = f"{tax_info.get('montoIva', 0):.2f}"

    ET.SubElement(detalle, "valRetBien10").text = f"{tax_info.get('retIva', {}).get('9', 0):.2f}"
    ET.SubElement(detalle, "valRetServ20").text = f"{tax_info.get('retIva', {}).get('10', 0):.2f}"
    ET.SubElement(detalle, "valorRetBienes").text = f"{tax_info.get('retIva', {}).get('1', 0):.2f}"
    ET.SubElement(detalle, "valRetServ50").text = f"{tax_info.get('retIva', {}).get('11', 0):.2f}"
    ET.SubElement(detalle, "valorRetServicios").text = f"{tax_info.get('retIva', {}).get('2', 0):.2f}"
    ET.SubElement(detalle, "valRetServ100").text = f"{tax_info.get('retIva', {}).get('3', 0):.2f}"

    pago_exterior = ET.SubElement(detalle, "pagoExterior")
    ET.SubElement(pago_exterior, "pagoLocExt").text = "01"
    ET.SubElement(pago_exterior, "paisEfecPago").text = "NA"
    ET.SubElement(pago_exterior, "aplicConvDobTrib").text = "NA"
    ET.SubElement(pago_exterior, "pagExtSujRetNorLeg").text = "NA"

    if tax_info.get("air"):
        air = ET.SubElement(detalle, "air")
        for ret in tax_info["air"]:
            detalle_air = ET.SubElement(air, "detalleAir")
            ET.SubElement(detalle_air, "codRetAir").text = ret.get("codRetAir", "")
            ET.SubElement(detalle_air, "baseImpAir").text = f"{ret.get('baseImpAir', 0):.2f}"
            ET.SubElement(detalle_air, "porcentajeAir").text = f"{ret.get('porcentajeAir', 0):.2f}"
            ET.SubElement(detalle_air, "valRetAir").text = f"{ret.get('valRetAir', 0):.2f}"

def _group_sales(sales_docs):
    grouped = {}
    for doc in sales_docs:
        # Assuming 'tipoEmision' is a custom field on Sales Invoice, defaulting to 'E'
        key = (
            doc.party_info.get("tpIdCliente", "07"),
            doc.party_info.get("idCliente", "9999999999999"),
            doc.party_info.get("parteRelVtas", "NO"),
            _get_tipo_comprobante(doc),
            doc.get("tipoEmision", "E")
        )

        if key not in grouped:
            grouped[key] = {
                "numeroComprobantes": 0, "baseNoGraIva": 0, "baseImponible": 0,
                "baseImpGrav": 0, "montoIva": 0, "montoIce": 0,
                "valorRetIva": 0, "valorRetRenta": 0, "formasDePago": set()
            }

        g = grouped[key]
        tax_info = doc.tax_info
        g["numeroComprobantes"] += 1
        g["baseNoGraIva"] += tax_info.get("baseNoGraIva", 0)
        g["baseImponible"] += tax_info.get("baseImponible", 0)
        g["baseImpGrav"] += tax_info.get("baseImpGrav", 0)
        g["montoIva"] += tax_info.get("montoIva", 0)
        g["montoIce"] += tax_info.get("montoIce", 0)
        # Assuming custom fields for sales withholdings
        g["valorRetIva"] += doc.get("custom_valor_ret_iva", 0)
        g["valorRetRenta"] += doc.get("custom_valor_ret_renta", 0)

        if doc.get("payment_info") and doc.payment_info.get("sri_codes"):
            g["formasDePago"].update(doc.payment_info["sri_codes"])

    return grouped

def _build_sales_xml(parent_xml, grouped_sales):
    """Builds <detalleVentas> elements from grouped sales data."""
    for key, g in grouped_sales.items():
        tpIdCliente, idCliente, parteRel, tipoComprobante, tipoEmision = key

        detalle = ET.SubElement(parent_xml, "detalleVentas")
        ET.SubElement(detalle, "tpIdCliente").text = tpIdCliente
        ET.SubElement(detalle, "idCliente").text = idCliente
        ET.SubElement(detalle, "parteRelVtas").text = parteRel
        ET.SubElement(detalle, "tipoComprobante").text = tipoComprobante
        ET.SubElement(detalle, "tipoEmision").text = tipoEmision
        ET.SubElement(detalle, "numeroComprobantes").text = str(g["numeroComprobantes"])
        ET.SubElement(detalle, "baseNoGraIva").text = f"{g['baseNoGraIva']:.2f}"
        ET.SubElement(detalle, "baseImponible").text = f"{g['baseImponible']:.2f}"
        ET.SubElement(detalle, "baseImpGrav").text = f"{g['baseImpGrav']:.2f}"
        ET.SubElement(detalle, "montoIva").text = f"{g['montoIva']:.2f}"
        ET.SubElement(detalle, "montoIce").text = f"{g['montoIce']:.2f}"
        ET.SubElement(detalle, "valorRetIva").text = f"{g['valorRetIva']:.2f}"
        ET.SubElement(detalle, "valorRetRenta").text = f"{g['valorRetRenta']:.2f}"

        if g["formasDePago"]:
            formas_pago_xml = ET.SubElement(detalle, "formasDePago")
            for fp_code in g["formasDePago"]:
                if fp_code:
                    ET.SubElement(formas_pago_xml, "formaPago").text = fp_code

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

def _build_annulled_xml(parent_xml, doc):
    """Builds a <detalleAnulados> element."""
    detalle = ET.SubElement(parent_xml, "detalleAnulados")
    ET.SubElement(detalle, "tipoComprobante").text = _get_tipo_comprobante(doc)
    ET.SubElement(detalle, "establecimiento").text = str(doc.estab or "").zfill(3)
    ET.SubElement(detalle, "puntoEmision").text = str(doc.ptoEmi or "").zfill(3)
    ET.SubElement(detalle, "secuencialInicio").text = str(doc.secuencial or "")
    ET.SubElement(detalle, "secuencialFin").text = str(doc.secuencial or "")
    ET.SubElement(detalle, "autorizacion").text = str(doc.numeroautorizacion or "")

def _build_ventas_establecimiento_xml(parent_xml, sales_docs):
    """Builds <ventaEst> elements for each establishment."""
    sales_by_estab = {}
    for doc in sales_docs:
        estab = str(doc.estab or "999").zfill(3)
        if estab not in sales_by_estab:
            sales_by_estab[estab] = 0
        sales_by_estab[estab] += doc.net_total

    if not sales_by_estab: # Add at least one entry if no sales
        venta_est_xml = ET.SubElement(parent_xml, "ventaEst")
        ET.SubElement(venta_est_xml, "codEstab").text = "001"
        ET.SubElement(venta_est_xml, "ventasEstab").text = "0.00"
        return

    for estab, total in sales_by_estab.items():
        venta_est_xml = ET.SubElement(parent_xml, "ventaEst")
        ET.SubElement(venta_est_xml, "codEstab").text = estab
        ET.SubElement(venta_est_xml, "ventasEstab").text = f"{total:.2f}"
        # ET.SubElement(venta_est_xml, "ivaComp").text = "0.00" # Ficha tecnica needed for this

@frappe.whitelist()
def generate_xml(data, filters):
    if isinstance(filters, str): filters = json.loads(filters)

    docs = get_raw_docs(filters)
    docs = _enrich_data(docs)

    company = filters.get("company")
    year = filters.get("year")
    month = filters.get("month")

    company_doc = frappe.get_doc("Company", company)
    num_estab_ruc = frappe.db.count("Sri Establishment", {"company_link": company})

    # Separate documents
    purchase_docs = [d for d in docs if d.doctype == 'Purchase Invoice' and d.docstatus == 1]
    sales_docs = [d for d in docs if d.doctype == 'Sales Invoice' and d.docstatus == 1]
    annulled_docs = [d for d in docs if d.docstatus == 2]

    total_ventas = sum(d.grand_total for d in sales_docs)

    root = ET.Element("iva")
    ET.SubElement(root, "TipoIDInformante").text = "R"
    ET.SubElement(root, "IdInformante").text = str(company_doc.tax_id)
    ET.SubElement(root, "razonSocial").text = str(company_doc.company_name)
    ET.SubElement(root, "Anio").text = str(year)
    ET.SubElement(root, "Mes").text = str(month).zfill(2)
    ET.SubElement(root, "numEstabRuc").text = str(num_estab_ruc or "1").zfill(3)
    ET.SubElement(root, "totalVentas").text = f"{total_ventas:.2f}"
    ET.SubElement(root, "codigoOperativo").text = "IVA"

    # Section <compras>
    compras_xml = ET.SubElement(root, "compras")
    for doc in purchase_docs:
        _build_purchase_xml(compras_xml, doc)

    # Section <ventas>
    ventas_xml = ET.SubElement(root, "ventas")
    grouped_sales = _group_sales(sales_docs)
    _build_sales_xml(ventas_xml, grouped_sales)

    # Section <ventasEstablecimiento>
    ventas_estab_xml = ET.SubElement(root, "ventasEstablecimiento")
    _build_ventas_establecimiento_xml(ventas_estab_xml, sales_docs)

    # Section <anulados>
    anulados_xml = ET.SubElement(root, "anulados")
    for doc in annulled_docs:
        _build_annulled_xml(anulados_xml, doc)

    xml_str = ET.tostring(root, 'utf-8', xml_declaration=True, encoding='UTF-8')
    parsed_str = minidom.parseString(xml_str)
    pretty_xml_str = parsed_str.toprettyxml(indent="  ", encoding="UTF-8").decode()

    file_name = f"ATS-{year}-{month}.xml"
    return {"file_name": file_name, "file_content": pretty_xml_str}
