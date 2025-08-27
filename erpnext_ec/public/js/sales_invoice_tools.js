/***********************************/
function resolveFromExternal(r, doc, btnProcess)
{
	console.log(r);


	jsonResponse = JSON.parse(r.message);
	console.log(jsonResponse);

	//console.log(json_data.data.claveAccesoConsultada);
	//console.log(json_data.data.autorizaciones.autorizacion[0].numeroAutorizacion);
	
	if(jsonResponse.ok && jsonResponse.data && jsonResponse.data.numeroComprobantes > 0)
	{
		const autorizacion = Array.isArray(jsonResponse.data.autorizaciones.autorizacion)
			? jsonResponse.data.autorizaciones.autorizacion[0]
			: jsonResponse.data.autorizaciones.autorizacion;

		var newNumeroAutorizacion = autorizacion.numeroAutorizacion;
		// old icon version <use class="" href="#icon-reply-all"></use>
		//	new icon version <i class="fa fa-paper-plane"></i>
		$(btnProcess).parent().find('.custom-animation').remove();
		$(btnProcess).parent().append(`
		<button class="btn btn-xs btn-default" data-name="` + doc.name + `" title="Enviar por email" onclick="event.stopPropagation(); document.Website.SendEmail('` + doc.name + `'); ">                					
			<i class="fa fa-paper-plane"></i></button>`);

		frappe.show_alert({
			message: __(`Documento ${doc.name} procesado <br>Nueva clave de acceso SRI: ` + newNumeroAutorizacion),
			indicator: 'green'
		}, 5);
		
		console.log('DATOS DE ERROR');
		console.log(jsonResponse.error);

		//Se mostrará alerta de error en este nivel solamente si es que
		// jsonResponse.error contiene información que deba ser mostrada
		if(jsonResponse.error!==null && jsonResponse.error!==undefined && jsonResponse.error !== '')
		{
			var string_error = jsonResponse.error;
			frappe.show_alert({
				message: __(string_error),
				indicator: 'red'
			}, 10);
		}

		//bye bye!!
		return;

	}
	else 
	{
		//MOSTRAR EL MENSAJE DE ERROR MAS DETALLADO
		//console.log(req);
		//console.log("Error", req.statusText);
		//console.log('1x');
		var string_error = jsonResponse.error;
		var string_informacionAdicional = '';
		var string_mensaje = '';
		try
		{
			const autorizacion = Array.isArray(jsonResponse.data.autorizaciones.autorizacion)
				? jsonResponse.data.autorizaciones.autorizacion[0]
				: jsonResponse.data.autorizaciones.autorizacion;

			const mensaje = autorizacion.mensajes.mensaje[0] || autorizacion.mensajes.mensaje || {};

			string_error = jsonResponse.error;
			string_mensaje = mensaje.mensaje_;
			string_informacionAdicional = mensaje.informacionAdicional;

			string_error = string_error == null ? '' : string_error;
			string_mensaje = string_mensaje == null ? '' : string_mensaje;
			string_informacionAdicional = string_informacionAdicional == null ? '' : string_informacionAdicional;
		}
		catch(ex_messages)
		{

		}

		frappe.show_alert({
			message: __(`Error al procesar documento ${doc.name}:` + string_error + ":" + string_mensaje + ":" + string_informacionAdicional),
			indicator: 'red'
		}, 10);
	}

	//console.log('Terminado proceso con el SRI!');
	$(btnProcess).show();
	$(btnProcess).parent().find('.custom-animation').remove();  
}

function resolveFromInternalSales(r, doc, btnProcess)
{
	console.log("Response received in resolveFromInternalSales:");
	console.log(r);

	if (!r.message) {
		frappe.show_alert({ message: __("Respuesta inválida del servidor."), indicator: 'red' }, 10);
		$(btnProcess).show();
		$(btnProcess).parent().find('.custom-animation').remove();
		return;
	}

	const jsonResponse = r.message;

	// Handle responses where 'numeroComprobantes' is "0" or not present
	if (jsonResponse.numeroComprobantes && jsonResponse.numeroComprobantes != "0")
	{
		// Safely access the 'autorizacion' object, whether it's an array or single object
		const autorizacion = Array.isArray(jsonResponse.autorizaciones.autorizacion)
			? jsonResponse.autorizaciones.autorizacion[0]
			: jsonResponse.autorizaciones.autorizacion;

		if (autorizacion && autorizacion.estado === 'AUTORIZADO') {
			const newNumeroAutorizacion = autorizacion.numeroAutorizacion;

			$(btnProcess).parent().find('.custom-animation').remove();
			$(btnProcess).parent().append(
				`<button class="btn btn-xs btn-default" data-name="${doc.name}" title="Enviar por email" onclick="event.stopPropagation(); document.Website.SendEmail('${doc.name}');">
					<i class="fa fa-paper-plane"></i>
				</button>`
			);

			let alert_message = `Documento ${doc.name} procesado <br>Nueva clave de acceso SRI: ${newNumeroAutorizacion}`;
			if (!jsonResponse.ok && jsonResponse.custom_info) {
				alert_message = jsonResponse.custom_info;
			}
			frappe.show_alert({ message: __(alert_message), indicator: 'green' }, 5);
			
		} else if (autorizacion) {
			// Handle non-authorized responses
			const mensaje = autorizacion.mensajes && (Array.isArray(autorizacion.mensajes.mensaje) ? autorizacion.mensajes.mensaje[0] : autorizacion.mensajes.mensaje);
			const string_error = `
				${autorizacion.estado}:<br>
				<b>Identificador (${mensaje ? mensaje.identificador : 'N/A'}):</b> ${mensaje ? mensaje.mensaje : 'Error no especificado.'}<br>
				<b>Info Adicional:</b> ${mensaje ? mensaje.informacionAdicional : 'N/A'}
			`;
			frappe.show_alert({ message: __(string_error), indicator: 'red' }, 15);
		}
	} else {
		// Handle cases with no 'numeroComprobantes' or other errors
		let error_message = `Error al procesar ${doc.name}.`;
		if (jsonResponse.comprobantes && jsonResponse.comprobantes.comprobante) {
			const mensaje = Array.isArray(jsonResponse.comprobantes.comprobante.mensajes.mensaje)
				? jsonResponse.comprobantes.comprobante.mensajes.mensaje[0]
				: jsonResponse.comprobantes.comprobante.mensajes.mensaje;
			if (mensaje) {
				error_message += `<br><b>Mensaje:</b> ${mensaje.mensaje}<br><b>Info:</b> ${mensaje.informacionAdicional || 'N/A'}`;
			}
		} else if (jsonResponse.custom_info) {
			error_message = jsonResponse.custom_info;
		}
		frappe.show_alert({ message: __(error_message), indicator: 'red' }, 15);
	}

	//console.log('Terminado proceso con el SRI!');
	$(btnProcess).show();
	$(btnProcess).parent().find('.custom-animation').remove();  
}

function SendSalesInvoiceToSri(documentIsReady, document_preview, doc)
{
	var doctype_erpnext = 'Sales Invoice';
	var typeDocSri = 'FAC';
	var documentName = 'Factura';
    var sitenameVar = frappe.boot.sitename;

	console.log(doc.is_return);
	console.log(doc.status);
	//"Return"
	//evaluar si es nota de crédito
	if(doc.is_return)
	{
		typeDocSri = 'NCR';
		documentName = 'Nota de Crédito';
	}
	{
		if(doc.is_debit_note)
		{
			typeDocSri = 'NDE';
			documentName = 'Nota de Débito';
		}
	}
	
	if (documentIsReady)
	{
		frappe.warn('Enviar ' + documentName + ' al SRI?',
			document_preview,
			() => {

				frappe.show_alert({
					message: __(`Documento ${doc.name} está siendo procesado en el SRI, por favor espere un momento. `),
					indicator: 'green'
				}, 7);

				var btnProcess = $('.list-actions button[data-name="' + doc.name + '"]').parent().find('.btn-action');
				//Oculta el botón
				$(btnProcess).hide();
				//Muestra animación de carga
				$(btnProcess).after(document.Website.loadingAnimation);

				// action to perform if Yes is selected
				//console.log('Enviando al SRI');
				//resolveFromInternal(null, doc, btnProcess);
				//return;	

				frappe.call({
					method: "erpnext_ec.utilities.sri_ws.send_doc_native",
					args: 
					{
						doc: doc,
						typeDocSri: typeDocSri,
						doctype_erpnext: doctype_erpnext,
						siteName: sitenameVar,
						freeze: true,
						freeze_message: "Procesando documento, espere un momento.",
						success: function(r) {},
						always: function(r) {},
					},
					callback: function(r)
					{
						//resolveFromExternal(r, doc, btnProcess);
						resolveFromInternalSales(r, doc, btnProcess);
					},
					error: function(r) {
						$(btnProcess).show();
						$(btnProcess).parent().find('.custom-animation').remove();
					},
				});
			},
			'Confirmar proceso de envío al SRI'
		);
	}
	else 
	{
		//Cuando la factura no esté correcta
		frappe.msgprint({
			title: __(documentName + ' incompatible con el SRI'),
			indicator: 'red',
			message: __(document_preview)
		});
	}
}

function validationSri(doc)
{
	frappe.call({
		method: "erpnext_ec.utilities.doc_validator.validate_sales_invoice",
		args: 
		{
			doc_name: doc.name,
			freeze: false,
			freeze_message: "Procesando documento, espere un momento.",
			success: function(r) {},								
			always: function(r) {},
		},
		callback: function(r) 
		{
			console.log(r);			
			console.log(r.message.doctype_erpnext);
			//jsonResponse = JSON.parse(r.message);
			//console.log(jsonResponse);
			
			var data_header = '<table>';

			for(i=0; i < r.message.header.length; i++)
			{				
				data_header += `
				<tr>
                    <td>${r.message.header[i].description}:</td>
                    <td>${r.message.header[i].value}</td>
                </tr>
				`;
			}

			data_header += '</table>'

			var data_alert = '<table>';

			for(i=0; i < r.message.alerts.length; i++)
			{				
				data_alert += document.Website.CreateAlertItem(r.message.alerts[i].description);
			}

			data_alert += '</table>'

			console.log(data_alert);

			var document_preview = `
            <p>Confirmar para procesar el documento ${doc.name}</p>` + 
			data_header +
			data_alert +
                `<div class="warning-sri">Por favor, verifique que toda la información esté correctamente ingresada antes de enviarla al SRI y generar el documento electrónico.</div>`;

			SendSalesInvoiceToSri(r.message.documentIsReady, document_preview, doc);

			//if(r.message.documentIsReady)
			//{				
			//}
		},
		error: function(r) {
			var btnProcess = $('.list-actions button[data-name="' + doc.name + '"]').parent().find('.btn-action');
			$(btnProcess).show();
			$(btnProcess).parent().find('.custom-animation').remove();
		},
	});
}

function SendSalesInvoice(doc) 
{
	validationSri(doc);
}

