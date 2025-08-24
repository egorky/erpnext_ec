frappe.ui.form.on('Sri Signature', {
    onload: function(frm) {
        
    },
    refresh(frm)
    {
        frm.add_custom_button(__("Probar Firma"), function() {            
            frappe.call({
                method: "erpnext_ec.utilities.sri_ws.test_signature",
                args: 
                {
                    signature_doc: frm.doc,                    
                    //freeze: true,
                    //freeze_message: "Procesando documento, espere un momento.",
                    success: function(r) {},								
                    always: function(r) {},
                },
                callback: function(r)
                {
                    console.log("SRI Debug: Raw response object 'r'", r);
                    console.log("SRI Debug: Message content 'r.message'", r.message);
                    console.log("SRI Debug: Type of r.message", typeof r.message);

                    let response = r.message;
                    try {
                        if (typeof response === 'string') {
                            console.log("SRI Debug: r.message is a string, attempting to parse.");
                            response = JSON.parse(response);
                            console.log("SRI Debug: Parsed response object", response);
                        }

                        if (response && response.status === "success") {
                            console.log("SRI Debug: Condition is true, showing success.");
                            frappe.show_alert({
                                message: __(response.message || "Firma válida."),
                                indicator: 'green'
                            }, 10);
                        } else {
                            console.log("SRI Debug: Condition is false, showing error.");
                            console.log("SRI Debug: response.status value is:", response ? response.status : "N/A");
                            frappe.show_alert({
                                message: __("Error al procesar firma: ") + (response ? response.message : "Respuesta no válida del servidor."),
                                indicator: 'red'
                            }, 10);
                        }
                    } catch (e) {
                        console.log("SRI Debug: Error during JSON parsing or processing.", e);
                        frappe.show_alert({
                            message: __("Error al interpretar la respuesta del servidor."),
                            indicator: 'red'
                        }, 10);
                    }
                },
                error: function(r) {
                    
                },
            });
        });

        frm.add_custom_button(__("Verificar Firma"), function() {            
            frappe.call({
                method: "erpnext_ec.utilities.sri_ws.verify_signature",
                args: 
                {
                    signature_doc: frm.doc,                    
                    //freeze: true,
                    //freeze_message: "Procesando documento, espere un momento.",
                    success: function(r) {},								
                    always: function(r) {},
                },
                callback: function(r) 
                {
                    //console.log(r);
                    
                    //console.log(r.message.issuer);

                    //jsonResponse = JSON.parse(r.message);
                    //console.log(jsonResponse);

                    if(r.message != undefined)
                    {
                        if(r.message.status == "success")
                        {
                            var message_body = "issuer:" + r.message.issuer + '</br>' +
                            "tax_id:" + r.message.tax_id + '</br>' +
                            "not_valid_before:" + r.message.not_valid_before + '</br>' +
                            "not_valid_after:<span class='font-weight-bold'>" + r.message.not_valid_after + '</span></br>' ;
                            
                            message_body = `
                            <table>
                                <tbody>                                    
                                    <tr>
                                        <td style="font-size:0.9em">RUC:</td>
                                        <td class="font-weight-bold">${r.message.tax_id}</td>
                                    </tr>
                                    <tr>
                                        <td style="font-size:0.9em">Issuer</td>
                                        <td class="font-weight-bold" style="font-size:0.8em">${r.message.issuer}</td>
                                    </tr>
                                    <tr>
                                        <td style="font-size:0.9em">Hasta:</td>
                                        <td class="font-weight-bold" style="font-size:0.9em">${r.message.not_valid_after}</td>
                                    </tr>
                                    <tr>
                                        <td style="font-size:0.9em">Desde:</td>
                                        <td class="font-weight-bold" style="font-size:0.9em">${r.message.not_valid_before}</td>
                                    </tr>
                                </tbody>
                            </table>
                            `;

                            frappe.show_alert({
                                message: message_body,
                                indicator: 'green'
                            }, 10);
                        }
                        else
                        {
                            frappe.show_alert({
                                message: __(`Error al procesar firma:` + r.message.status),
                                indicator: 'red'
                            }, 10);
                        }
                    }
                    else
                    {
                        frappe.show_alert({
                            message: __(`Error al procesar firma: ---`),
                            indicator: 'red'
                        }, 10);
                    }
                },
                error: function(r) {
                    frappe.show_alert({
                        message: __(`Error al procesar firma: - `),
                        indicator: 'red'
                    }, 10);
                },
            });
        });
    },    
});
