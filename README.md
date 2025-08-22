# ERPNext Ecuador

Módulo de localización para ERPNext que integra las normativas y requerimientos de Ecuador, incluyendo la facturación electrónica del SRI.

## Características Principales

-   **Facturación Electrónica:** Generación y firma de documentos electrónicos (Facturas, Notas de Crédito, Retenciones, etc.) en formato XML, listos para ser enviados al SRI.
-   **Gestión de Firmas Electrónicas:** Almacenamiento seguro de los certificados de firma electrónica.
-   **Catálogos del SRI:** Incluye los catálogos del SRI como Tipos de Identificación, Tipos de Comprobantes, etc.
-   **Configuración Regional:** Permite configurar datos específicos de la normativa ecuatoriana.

## Guía de Instalación y Configuración

### Instalación

1.  Asegúrate de tener `bench` y un sitio de Frappe/ERPNext funcionando.
2.  Descarga e instala la aplicación en tu `bench`:
    ```bash
    bench get-app https://github.com/beebtech-net/erpnext_ec.git
    bench --site [tu-sitio] install-app erpnext_ec
    bench --site [tu-sitio] migrate
    ```

### Configuración de la Firma Electrónica

La firma electrónica es indispensable para generar los documentos tributarios válidos para el SRI.

1.  **Obtén tu Firma Electrónica:** Primero, debes adquirir un certificado de firma electrónica en formato de archivo (`.p12`) a través de una de las [entidades de certificación autorizadas en Ecuador](https://www.google.com/search?q=entidades+de+certificacion+autorizadas+ecuador).

2.  **Sube tu Firma al Sistema:**
    -   En ERPNext, ve al módulo **Sri**.
    -   Busca el DocType **Firma Electrónica** y crea un nuevo registro.
    -   Sube tu archivo `.p12` en el campo correspondiente.
    -   Ingresa la contraseña de tu firma electrónica. El sistema la almacenará de forma segura.
    -   Guarda el documento.

Una vez configurada, el sistema usará esta firma para autorizar todos los documentos electrónicos que generes.

## Doctypes Principales del Módulo

El módulo "Sri" en el escritorio de ERPNext te da acceso a las configuraciones y documentos más importantes:

-   **Firma Electrónica:** Para gestionar los certificados de firma electrónica.
-   **Establecimientos:** Define los establecimientos o sucursales de tu empresa registrados en el SRI.
-   **Puntos de Emisión:** Configura los puntos de emisión para cada establecimiento.
-   **Secuencias:** Gestiona las secuencias numéricas para los diferentes tipos de comprobantes.
-   **Ambientes SRI:** Configura el ambiente de trabajo (Pruebas o Producción) para la conexión con los web services del SRI.
-   **Tipos de Comprobantes:** Catálogo de los tipos de documentos tributarios según el SRI.
-   **Tipos de Identificación:** Catálogo de los tipos de identificación (RUC, Cédula, Pasaporte).
