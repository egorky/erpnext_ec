# Manual de Modificaciones a Documentos Estándar

Este documento detalla los campos y modificaciones que el módulo `erpnext_ec` añade a los documentos estándar de ERPNext para cumplir con la normativa ecuatoriana.

---

## 1. Compañía (Company)

La configuración a nivel de compañía es fundamental para el funcionamiento del módulo. Se añaden los siguientes campos en `Contabilidad > Compañía`:

#### Pestaña de Dirección e Impuestos
-   **Nombre Comercial:** El nombre comercial de la compañía, que puede ser diferente de la razón social.
-   **Contribuyente Especial No:** Número de resolución si la compañía es un contribuyente especial.
-   **Obligado Contabilidad:** Casilla para marcar si la compañía está obligada a llevar contabilidad.
-   **Contribuyente Rimpe:** Casilla para marcar si la compañía pertenece al régimen RIMPE.
-   **Agente Retención Resolución No:** Número de resolución si la compañía es agente de retención.

#### Nueva Sección: Configuración Regional SRI
-   **Ambiente Sri:** Permite seleccionar el ambiente de trabajo (Pruebas o Producción) para la conexión con el SRI.
-   **Firma Electrónica:** Permite seleccionar la firma electrónica activa que se usará para firmar los documentos de esta compañía.
-   **Usar modo simulación:** Si se marca, los documentos se firman pero no se envían al SRI. Útil para pruebas internas.
-   **Configuración:** Enlace a la configuración regional de Ecuador.

#### Nueva Sección: Formatos de Impresión Ride
-   Se añaden campos para seleccionar el **Formato de Impresión (Print Format)** por defecto para el RIDE (Representación Impresa del Documento Electrónico) de cada tipo de documento (Factura, Nota de Crédito, etc.).

#### Nueva Sección: Plantillas de Emails Rides
-   Se añaden campos para seleccionar la **Plantilla de Email (Email Template)** por defecto que se usará al enviar por correo cada tipo de documento electrónico.

---

## 2. Cliente (Customer) y Proveedor (Supplier)

A los maestros de Clientes y Proveedores se les añaden campos para cumplir con los requerimientos de información del SRI.

-   **Nombre Comercial:** El nombre comercial del cliente/proveedor.
-   **Tipo Identificación:** Un enlace al catálogo `Sri Type Id` para seleccionar el tipo de identificación (RUC, Cédula, Pasaporte, etc.).

---

## 3. Factura de Venta (Sales Invoice) y Factura de Compra (Purchase Invoice)

A los principales documentos transaccionales se les añade una nueva sección "Datos SRI" para gestionar la información de facturación electrónica.

-   **Establecimiento:** Campo de enlace para seleccionar el `Sri Establishment` desde el cual se emite el documento.
-   **Punto Emisión:** Campo de enlace dinámico para seleccionar el `Sri Ptoemi`. Las opciones se filtran según el establecimiento escogido.
-   **secuencial:** Número de secuencia del documento. Es un campo de solo lectura que el sistema calcula automáticamente.
-   **numeroAutorizacion:** Número de autorización devuelto por el SRI. Es de solo lectura.
-   **fechaAutorizacion:** Fecha y hora de la autorización del SRI. Es de solo lectura.
-   **sri_estado:** Estado del documento en el SRI (ej. Enviado, Autorizado, Rechazado).
-   **sri_response:** Mensaje de respuesta del SRI, útil para diagnosticar errores.
-   **infoAdicional:** Una tabla para añadir campos de información adicional requeridos en el XML.
-   **Es liquidación de compra (Solo en Factura de Compra):** Casilla para marcar si la factura es en realidad una Liquidación de Compra y debe ser tratada como tal.

---

## 4. Nota de Entrega (Delivery Note)

Al igual que en las facturas, se añade una sección "Datos SRI" para gestionar los datos de la Guía de Remisión.

-   **Campos similares a Factura:** Se añaden campos para `estab`, `ptoemi`, `secuencial` y los campos de estado y autorización del SRI, pero aplicados a la Guía de Remisión.
-   **Datos del Transportista:** Campos para especificar la información del transportista y del vehículo.

---

## 5. Modo de Pago (Mode of Payment)

-   **Forma de Pago SRI:** Se añade un campo para vincular cada modo de pago de ERPNext con la forma de pago correspondiente del catálogo del SRI (ej. "SIN UTILIZACION DEL SISTEMA FINANCIERO", "TARJETA DE CREDITO", etc.).
