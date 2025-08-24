import frappe
import os
import json
from types import SimpleNamespace
from lxml import etree
from xml.etree.ElementTree import Element, SubElement, tostring
from datetime import datetime
from dateutil import parser
from decimal import Decimal

#Metodo que gestiona el upload de los archivos seleccionados
@frappe.whitelist()
def custom_upload(file = None):
    print(file)

    file_content = frappe.local.uploaded_file
    file_name = frappe.local.uploaded_filename
    file_path = frappe.local.site + "/private/files/" + file_name
    
    #print(file_content)
    #print(file_name)
    #print(file_path)
    # your magic here to rename, check if file exists, change path ...

    with open(file_path, "wb") as file:
        file.write(file_content)

def evaluate_supplier(create_if_not_exists, tax_id, supplier_name, nombreComercial, dirMatriz):
    found_data = frappe.get_all('Supplier', filters={"tax_id": tax_id, "name": supplier_name}, fields = ['*'])

    if (found_data):
        print('Proveedor ya existe')
        pass
    else:
        print('Proveedor NO existe')
        new_data = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "tax_id":  tax_id,
            "nombreComercial":  nombreComercial,
            "primary_address":  dirMatriz,
            "is_internal_supplier":  0,
            "is_transporter":  0,
            "supplier_group":  "Todos los grupos de proveedores"
        })

        new_data.insert()
        frappe.db.commit()

def evaluate_item(create_if_not_exists, item_code, item_name, item_group, item_brand, item_description, item_standard_rate):
    print('Buscar productos')
    print(item_code, item_name)
    #TODO: Revisar el filtro, no funciona si se combina item_code y item_name
    #found_data = frappe.get_all('Item', filters={"item_code": item_code, "item_name": item_name})
    #found_data = frappe.get_all('Item', fields='*', filters=[["item_code", "=", item_code],["item_name", "=", item_name]])
    found_data = frappe.get_all('Item', fields='*', filters={"item_code":item_code})

    #print(found_data)

    if (found_data):
        print('Item ya existe')
        pass
    else:
        print('Item NO existe')
        new_data = frappe.get_doc({
            "doctype": "Item",
            "item_code":  item_code,
            "item_name":  item_name,
            "item_group":  item_group,
            "brand":  item_brand,
            "description":  item_description,
            "standard_rate":  item_standard_rate,
        })

        new_data.insert()
        frappe.db.commit()

def evaluate_brand(create_if_not_exists, name_for_search):
    found_data = frappe.get_all('Brand', filters={"name": name_for_search})

    if (found_data):
        print('Marca ya existe')
        pass
    else:
        print('Marca NO existe')
        new_data = frappe.get_doc({
            "doctype": "Brand",
            "name":  name_for_search,
            "brand":  name_for_search,
            "description":  name_for_search
        })

        new_data.insert()
        frappe.db.commit()

def evaluate_product_group(create_if_not_exists, name_for_search):
    found_data = frappe.get_all('Item Group', filters={"name": name_for_search})

    if (found_data):
        print('Grupo de producto ya existe')
        pass
    else:

        #Realizar la busqueda automatica de este nombre
        parent_item_group = "Todos los grupos de artículos"

        print('Grupo de producto NO existe')
        new_data = frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name":  name_for_search,
            "parent_item_group":  parent_item_group,
            "route":  name_for_search
        })

        new_data.insert()
        frappe.db.commit()

def search_account_tax(create_if_not_exists, codigo, codigoPorcentaje, tarifa):
    found_data_taxes_template = frappe.get_all('Purchase Taxes and Charges Template', fields = ['*'])
    #print(found_data_taxes_template)

    if(found_data_taxes_template):
        for item_template in found_data_taxes_template:
            
            #print(item_template.name)
            found_data_item_taxes_template = frappe.get_all('Purchase Taxes and Charges', fields = ['*'], filters={"parent": item_template.name})
            #print("found_data_item_taxes_template")
            #print(found_data_item_taxes_template)

            #Buscar Items de la Plantilla
            for tax_detail in found_data_item_taxes_template:
                #print("Cuenta de impuestos:", tax_detail.account_head)
                #print("Tasa de impuestos:", tax_detail.rate)
                
                #print("add_deduct_tax:", tax_detail.add_deduct_tax)
                #print("category:", tax_detail.category)
                #print("charge_type:", tax_detail.charge_type)

                if(tax_detail.category == 'Total' and tax_detail.add_deduct_tax == 'Add' and tax_detail.charge_type == 'On Net Total'):
                    found_account = frappe.get_all('Account', fields = ['*'], filters={"name": tax_detail.account_head})

                    #print(found_account)

                    for account_item in found_account:
                        print("name:", account_item.name)
                        print("sricode:", account_item.sricode)
                        print("codigoporcentaje:", account_item.codigoporcentaje)
                        print("tax_rate:", account_item.tax_rate)
                        print("------------------------")
                        print(codigo, codigoPorcentaje, tarifa)

                        if(account_item.sricode == codigo and account_item.codigoporcentaje == codigoPorcentaje and account_item.tax_rate == float(tarifa)):
                            #Se retorna el item template encontrado ya que si contiene el impuesto
                            # al que se hace referencia
                            print("Se encontro la cuenta que coincide...")
                            print("Plantilla de impuesto de compra:")
                            print(item_template.name)
                            return account_item
                        

def evaluate_taxes(create_if_not_exists, codigo, codigoPorcentaje, tarifa):
    found_data_taxes_template = frappe.get_all('Purchase Taxes and Charges Template', fields = ['*'])
    #print(found_data_taxes_template)

    if(found_data_taxes_template):
        for item_template in found_data_taxes_template:
            
            #print(item_template.name)
            found_data_item_taxes_template = frappe.get_all('Purchase Taxes and Charges', fields = ['*'], filters={"parent": item_template.name})
            #print("found_data_item_taxes_template")
            #print(found_data_item_taxes_template)

            #Buscar Items de la Plantilla
            for tax_detail in found_data_item_taxes_template:
                #print("Cuenta de impuestos:", tax_detail.account_head)
                #print("Tasa de impuestos:", tax_detail.rate)
                
                #print("add_deduct_tax:", tax_detail.add_deduct_tax)
                #print("category:", tax_detail.category)
                #print("charge_type:", tax_detail.charge_type)

                if(tax_detail.category == 'Total' and tax_detail.add_deduct_tax == 'Add' and tax_detail.charge_type == 'On Net Total'):
                    found_account = frappe.get_all('Account', fields = ['*'], filters={"name": tax_detail.account_head})

                    #print(found_account)

                    for account_item in found_account:
                        print("name:", account_item.name)
                        print("sricode:", account_item.sricode)
                        print("codigoporcentaje:", account_item.codigoporcentaje)
                        print("tax_rate:", account_item.tax_rate)
                        print("------------------------")
                        print(codigo, codigoPorcentaje, tarifa)

                        if(account_item.sricode == codigo and account_item.codigoporcentaje == codigoPorcentaje and account_item.tax_rate == float(tarifa)):
                            #Se retorna el item template encontrado ya que si contiene el impuesto
                            # al que se hace referencia
                            print("Se encontro la cuenta que coincide...")
                            print("Plantilla de impuesto de compra:")
                            print(item_template.name)
                            return item_template

              

    #Crear
    #company : "RONALD STALIN CHONILLO VILLON"
    #name : "Ecuador Tax 15% (Compra) - RSCV"

@frappe.whitelist()
def import_purchase_invoice_from_xml(file, auto_create_data, update_invoices, remove_files):
    print(file)
    #print(file.is_private)
    print(auto_create_data)
    print(update_invoices)
    print(remove_files)

    file_json = json.loads(file, object_hook=lambda d: SimpleNamespace(**d))

    access_folder = '/public'
    if(file_json.is_private):
        #access_folder = 'private' #NOT add is automatic on frappe.local.site
        #TODO: Check on 13 version
        access_folder = ''

    #file_content = frappe.local.uploaded_file
    #file_name = frappe.local.uploaded_filename
    #file_path = frappe.local.site + "/private/files/" + file_name
    
    #print(file_content)
    #print(file_name)
    #print(file_path)
    # your magic here to rename, check if file exists, change path ...

    #with open(file_path, "wb") as file:
    #    file.write(file_content)

    file_path = frappe.local.site + access_folder + file_json.file_url

    f=open(file_path, "rb")
    xml_string_data=f.read()
    f.close()
    
    doc_root = etree.fromstring(xml_string_data)
    doc_comprobante = None

    # Determinar el tipo de XML y extraer la factura
    if doc_root.tag == 'autorizacion':
        comprobante_text = doc_root.findtext('comprobante')
        if comprobante_text:
            doc_comprobante = etree.fromstring(comprobante_text.strip().encode('utf-8'))
        else:
            frappe.throw("El XML de autorización no contiene la etiqueta 'comprobante' con los datos de la factura.")
    elif doc_root.tag == 'factura':
        doc_comprobante = doc_root
    else:
        frappe.throw("El archivo XML no es un documento de 'autorizacion' o 'factura' válido.")

    if doc_comprobante is not None:
        defaulProductGroup = 'Adquisiciones (DI)'
        defaultBrand = 'Sin Marca (DI)'

        found_purchase_invoice = frappe.get_all('Purchase Invoice', filters={"numeroautorizacion": doc_comprobante.find('infoTributaria').find('claveAcceso').text}, fields = ['*'])

        if(found_purchase_invoice):
            print('Registro exitente, no se creará nuevo')
            return

        evaluate_product_group(True, defaulProductGroup)
        evaluate_brand(True, defaultBrand)
        evaluate_supplier(True,
                          doc_comprobante.find('infoTributaria').find('ruc').text,
                          doc_comprobante.find('infoTributaria').find('razonSocial').text,
                          doc_comprobante.find('infoTributaria').find('nombreComercial').text,
                          doc_comprobante.find('infoTributaria').find('dirMatriz').text)

        print('Registro nuevo')

        fechaAutorizacion_text = doc_root.findtext('fechaAutorizacion')
        if fechaAutorizacion_text:
            fechaAutorizacion = parser.parse(fechaAutorizacion_text)
        else:
            fechaAutorizacion = parser.parse(doc_comprobante.find('infoFactura').find('fechaEmision').text)

        new_tax_items = []
        total_con_impuestos_node = doc_comprobante.find('infoFactura').find('totalConImpuestos')
        if total_con_impuestos_node is not None:
            for totalConImpuestoItem in total_con_impuestos_node:
                tarifa_node = totalConImpuestoItem.find('tarifa')
                tarifa_text = None

                if tarifa_node is not None:
                    tarifa_text = tarifa_node.text
                else:
                    codigo = totalConImpuestoItem.find('codigo').text
                    codigoPorcentaje = totalConImpuestoItem.find('codigoPorcentaje').text
                    
                    detalles_node = doc_comprobante.find('detalles')
                    if detalles_node is not None:
                        for detalleItem in detalles_node:
                            impuestos_node = detalleItem.find('impuestos')
                            if impuestos_node is None:
                                continue
                            for impuestoItem in impuestos_node:
                                if impuestoItem.find('codigo').text == codigo and impuestoItem.find('codigoPorcentaje').text == codigoPorcentaje:
                                    tarifa_node_from_detail = impuestoItem.find('tarifa')
                                    if tarifa_node_from_detail is not None:
                                        tarifa_text = tarifa_node_from_detail.text
                                        break
                            if tarifa_text:
                                break

                if tarifa_text is not None:
                    found_account = search_account_tax(True, 
                                        totalConImpuestoItem.find('codigo').text, 
                                        totalConImpuestoItem.find('codigoPorcentaje').text, 
                                        tarifa_text)
                    if(found_account):
                        new_tax_items.append({
                            "category" : "Total", "add_deduct_tax" : "Add", "charge_type" : "On Net Total",
                            "account_head" : found_account.name, "description" : found_account.account_name + "@" + str(found_account.tax_rate),
                            "rate" : float(tarifa_text), "tax_amount" : float(totalConImpuestoItem.find('valor').text),
                            "tax_amount_after_discount_amount" : float(totalConImpuestoItem.find('valor').text),
                            "total" : float(totalConImpuestoItem.find('baseImponible').text) + float(totalConImpuestoItem.find('valor').text),
                            "base_tax_amount" : float(totalConImpuestoItem.find('valor').text)
                        })

        new_items = []
        idx_item = 0
        for detalleItem in doc_comprobante.find('detalles'):
            evaluate_item(True,
                          detalleItem.find('codigoPrincipal').text,
                          detalleItem.find('descripcion').text,
                          defaulProductGroup,
                          defaultBrand,
                          detalleItem.find('descripcion').text,
                          float(detalleItem.find('precioUnitario').text)
                          )
            new_items.append({
                "idx": idx_item, "qty": float(detalleItem.find('cantidad').text), "rate": float(detalleItem.find('precioUnitario').text),
                "name": detalleItem.find('descripcion').text, "item_name": detalleItem.find('descripcion').text,
                "description": detalleItem.find('descripcion').text, "item_code": detalleItem.find('codigoPrincipal').text,
                "item_group": defaulProductGroup, "parent": "", "docstatus": "", "amount": float(detalleItem.find('precioTotalSinImpuesto').text),
                "brand": defaultBrand, "parentfield": "", "parenttype": "", "product_bundle": ""
            })
            idx_item += 1

        infoAdicional = []
        info_adicional_node = doc_comprobante.find('infoAdicional')
        if info_adicional_node is not None:
            for infoAdicionalItem in info_adicional_node:
                if(infoAdicionalItem.tag == 'campoAdicional'):
                    infoAdicional.append({
                        "nombre": infoAdicionalItem.attrib['nombre'],
                        "valor": infoAdicionalItem.text
                    })

        n_secuencial = int(doc_comprobante.find('infoTributaria').find('secuencial').text)
        docidsri = doc_comprobante.find('infoTributaria').find('estab').text + '-' + doc_comprobante.find('infoTributaria').find('ptoEmi').text + '-' + f'{n_secuencial:09d}'
        bill_date = parser.parse(doc_comprobante.find('infoFactura').find('fechaEmision').text)

        new_purchase_invoice_ = {
            "docstatus": 0, "doctype": "Purchase Invoice",
            "numeroautorizacion": doc_comprobante.find('infoTributaria').find('claveAcceso').text,
            "supplier" : doc_comprobante.find('infoTributaria').find('razonSocial').text,
            "estab": doc_comprobante.find('infoTributaria').find('estab').text,
            "ptoemi": doc_comprobante.find('infoTributaria').find('ptoEmi').text,
            "secuencial" : doc_comprobante.find('infoTributaria').find('secuencial').text,
            "sri_ambiente" : int(doc_comprobante.find('infoTributaria').find('ambiente').text),
            "sri_estado" : 200, "sri_response" : 'AUTORIZADO', "docidsri": docidsri,
            "fechaautorizacion" : fechaAutorizacion.replace(tzinfo=None), "bill_no" : docidsri,
            "bill_date": bill_date.replace(tzinfo=None), "is_sri_imported": True,
            "items": new_items, "taxes" : new_tax_items, "infoadicional": infoAdicional
        }

        reference_purchase_invoice = frappe.get_doc(new_purchase_invoice_)
        reference_purchase_invoice.insert()
        reference_purchase_invoice.save()

    if(remove_files):
        
        print(file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    #final de proceso de importacion
    #este proceso es individual
    #se ejecuta una vez por cada xml
