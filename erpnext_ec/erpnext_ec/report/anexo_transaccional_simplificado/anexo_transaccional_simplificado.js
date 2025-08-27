// Copyright (c) 2025, Jules and contributors
// For license information, please see license.txt

frappe.query_reports["Anexo Transaccional Simplificado"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_default("company"),
            "reqd": 1
        },
        {
            "fieldname": "year",
            "label": __("Año"),
            "fieldtype": "Select",
            "options": get_years(),
            "default": new Date().getFullYear(),
            "reqd": 1
        },
        {
            "fieldname": "month",
            "label": __("Mes"),
            "fieldtype": "Select",
            "options": [
                { "value": "01", "label": __("Enero") },
                { "value": "02", "label": __("Febrero") },
                { "value": "03", "label": __("Marzo") },
                { "value": "04", "label": __("Abril") },
                { "value": "05", "label": __("Mayo") },
                { "value": "06", "label": __("Junio") },
                { "value": "07", "label": __("Julio") },
                { "value": "08", "label": __("Agosto") },
                { "value": "09", "label": __("Septiembre") },
                { "value": "10", "label": __("Octubre") },
                { "value": "11", "label": __("Noviembre") },
                { "value": "12", "label": __("Diciembre") }
            ],
            "default": ("0" + (new Date().getMonth() + 1)).slice(-2),
            "reqd": 1
        }
    ],
    "onload": function(report) {
        report.page.add_inner_button(__("Generar XML"), function() {
            const filters = report.get_values();
            if (!filters.company || !filters.year || !filters.month) {
                frappe.msgprint(__("Por favor, seleccione Compañía, Año y Mes."));
                return;
            }

            // Fetch the data again to pass to the XML generation method
            frappe.call({
                method: 'frappe.desk.query_report.run',
                args: {
                    report_name: 'Anexo Transaccional Simplificado',
                    filters: filters,
                },
                callback: function(r) {
                    if (r.message && r.message.result) {
                        // Call a new python method to generate and download the XML
                        frappe.call({
                            method: "erpnext_ec.erpnext_ec.report.anexo_transaccional_simplificado.anexo_transaccional_simplificado.generate_xml",
                            args: {
                                "data": r.message.result,
                                "filters": filters
                            },
                            callback: function(response) {
                                if (response.message) {
                                    const { file_name, file_content } = response.message;
                                    frappe.ui.download(file_content, file_name, "application/xml");
                                }
                            }
                        });
                    } else {
                        frappe.msgprint(__('No hay datos para generar el XML.'));
                    }
                }
            });
        });
    }
};

function get_years() {
    const current_year = new Date().getFullYear();
    const years = [];
    for (let i = 0; i < 10; i++) {
        years.push(current_year - i);
    }
    return years;
}
