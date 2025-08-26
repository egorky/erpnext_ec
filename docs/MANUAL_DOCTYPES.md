# Manual de Referencia de DocTypes: ERPNext Ecuador

Este documento detalla todos los DocTypes personalizados que el módulo `erpnext_ec` añade a tu sistema ERPNext.

## DocTypes de Configuración Principal

Estos son los DocTypes que necesitas configurar para que el módulo funcione correctamente. Se encuentran principalmente en el módulo **Sri**.

---

### Sri Environment
-   **Propósito:** Define los ambientes de conexión a los web services del SRI.
-   **Uso:** Permite al sistema saber a qué URLs debe enviar los documentos para su autorización. Típicamente, tendrás dos registros: "Pruebas" y "Producción".
-   **Campos Clave:**
    -   `service_url_recept`: URL para enviar nuevos documentos.
    -   `service_url_authorize`: URL para consultar la autorización de un documento.

---

### Sri Signature
-   **Propósito:** Almacena de forma segura los certificados de firma electrónica.
-   **Uso:** Contiene el archivo `.p12` y la contraseña de tu firma electrónica, que se utiliza para firmar digitalmente todos los documentos tributarios antes de enviarlos al SRI.
-   **Campos Clave:**
    -   `p12`: Campo para subir tu archivo de firma electrónica.
    -   `password`: Campo para introducir la contraseña de tu firma.

---

### Sri Establishment
-   **Propósito:** Representa un establecimiento o sucursal de tu compañía registrado en el SRI.
-   **Uso:** Agrupa los puntos de emisión. Debes crear un registro por cada establecimiento físico que tengas.
-   **Campos Clave:**
    -   `company_link`: Vincula el establecimiento a una compañía de ERPNext.
    -   `record_name`: Código del establecimiento (ej. `001`).
    -   `sri_ptoemi_detail`: Tabla para definir los puntos de emisión de este establecimiento.

---

### Sri Ptoemi
-   **Propósito:** Define un punto de emisión dentro de un establecimiento.
-   **Uso:** Este es un **DocType hijo** que se gestiona únicamente desde la tabla "Puntos de Emisión" dentro de un `Sri Establishment`. No se puede acceder a él directamente.
-   **Campos Clave:**
    -   `record_name`: Código del punto de emisión (ej. `001`).
    -   `sec_factura`, `sec_notacredito`, etc.: Campos para definir el número de secuencia inicial para cada tipo de comprobante en este punto de emisión.

---

### Sri Sequence
-   **Propósito:** Gestiona de forma centralizada las secuencias numéricas de todos los documentos.
-   **Uso:** Aunque las secuencias se definen en cada `Sri Ptoemi`, este DocType permite consultarlas y ajustarlas globalmente si fuera necesario.
-   **Campos Clave:**
    -   `sri_type_doc_lnk`: El tipo de documento al que pertenece la secuencia.
    -   `sri_environment_lnk`: El ambiente (Pruebas/Producción) de la secuencia.
    -   `value`: El último número de secuencia utilizado.

---

### Regional Settings Ec
-   **Propósito:** Permite configurar ciertos parámetros regionales específicos de Ecuador.
-   **Uso:** Se accede desde `Contabilidad > Configuración Contable`.
-   **Campos Clave:**
    -   `ambiente_sri_por_defecto`: Permite seleccionar si el sistema funciona en modo Pruebas o Producción.
    -   `firma_electronica_activa`: Permite seleccionar qué `Sri Signature` se usará por defecto para la compañía.

---

## DocTypes de Catálogo y Soporte

Estos DocTypes almacenan información de catálogos del SRI o se utilizan para dar soporte a otros procesos. Generalmente, vienen pre-poblados con datos y no requieren modificación.

---

### Sri Type Doc
-   **Propósito:** Catálogo de los tipos de documentos tributarios según el SRI (Factura, Nota de Crédito, etc.).
-   **Uso:** Utilizado por otros DocTypes para referenciar el tipo de documento correcto.

---

### Sri Type Id
-   **Propósito:** Catálogo de los tipos de identificación según el SRI (RUC, Cédula, Pasaporte, etc.).
-   **Uso:** Utilizado en clientes y proveedores para definir su tipo de identificación.

---

### Xml Responses
-   **Propósito:** Almacena las respuestas (autorizaciones o rechazos) recibidas desde el SRI para cada documento electrónico enviado.
-   **Uso:** Es un log técnico. Permite consultar el historial de comunicación con el SRI y diagnosticar problemas.

---

### Purchase Withholding Sri Ec
-   **Propósito:** Representa un Comprobante de Retención de compra.
-   **Uso:** Permite generar el documento de retención que se le emite a un proveedor.

---

### Detalle Impuestos / Campo Adicional / Reembolso Detalle
-   **Propósito:** Son DocTypes hijos utilizados en otros documentos (como facturas o retenciones) para almacenar información detallada sobre impuestos, campos adicionales requeridos por el SRI, o detalles de reembolsos.
-   **Uso:** Se gestionan a través de las tablas en sus respectivos documentos padres.
