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
        // --- Button Logic ---
        const setup_buttons = (company) => {
            // Clear existing buttons
            report.page.clear_inner_toolbar();

            // "Generar XML" button is always visible
            report.page.add_inner_button(__("Generar XML"), function() {
                const filters = report.get_values();
                if (!filters.company || !filters.year || !filters.month) {
                    frappe.msgprint(__("Por favor, seleccione Compañía, Año y Mes."));
                    return;
                }
                frappe.call({
                    method: 'frappe.desk.query_report.run',
                    args: {
                        report_name: 'Anexo Transaccional Simplificado',
                        filters: filters,
                    },
                    callback: function(r) {
                        if (r.message && r.message.result && r.message.result.length > 0) {
                            frappe.call({
                                method: "erpnext_ec.erpnext_ec.report.anexo_transaccional_simplificado.anexo_transaccional_simplificado.generate_xml",
                                args: {
                                    "data": r.message.result,
                                    "filters": filters
                                },
                                callback: function(response) {
                                    if (response.message) {
                                        const { file_name, file_content } = response.message;
                                        const blob = new Blob([file_content], { type: 'application/xml' });
                                        const link = document.createElement('a');
                                        link.href = window.URL.createObjectURL(blob);
                                        link.download = file_name;
                                        document.body.appendChild(link);
                                        link.click();
                                        document.body.removeChild(link);
                                    }
                                }
                            });
                        } else {
                            frappe.msgprint(__('No hay datos para generar el XML.'));
                        }
                    }
                });
            });

            // "Enviar al SRI" button is conditionally visible
            if (company) {
                frappe.call({
                    method: "erpnext_ec.erpnext_ec.report.anexo_transaccional_simplificado.anexo_transaccional_simplificado.get_regional_settings",
                    args: {
                        "company": company
                    },
                    callback: function(r) {
                        if (r.message && r.message.send_sri_manual) {
                            report.page.add_inner_button(__("Enviar al SRI"), function() {
                                frappe.msgprint(__("La funcionalidad de envío al SRI para el ATS aún no está implementada."));
                            });
                        }
                    }
                });
            }
        };

        // --- Filter Change Handler ---
        report.filters.find(f => f.df.fieldname === 'company').$input.on('change', function() {
            const company = $(this).val();
            setup_buttons(company);
        });

        // --- Initial Setup ---
        const initial_company = report.get_values().company;
        setup_buttons(initial_company);
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
