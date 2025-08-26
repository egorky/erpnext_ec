# Estructura del Proyecto ERPNext Ecuador

Este documento detalla la estructura del proyecto `erpnext_ec`, un módulo de ERPNext para la facturación electrónica de Ecuador. El objetivo es proporcionar una guía clara para que los desarrolladores puedan entender dónde encontrar y modificar el código relevante para sus tareas.

## Directorio Raíz

- **`.gitignore`**: Especifica los archivos y directorios que Git debe ignorar.
- **`MANUAL_*.md`**: (Movidos a `docs/`) Archivos de documentación manual.
- **`README.md`**: Archivo de introducción al proyecto.
- **`erpnext_ec/`**: Directorio principal del módulo.
- **`license.txt`**: Licencia del proyecto.
- **`pyproject.toml`**: Archivo de configuración del proyecto de Python.
- **`requirements.txt`**: Lista de dependencias de Python.
- **`run_imports.sh`**: Script para ejecutar importaciones.
- **`run_patch_custom_fields.sh`**: Script para aplicar parches a campos personalizados.
- **`run_patches.sh`**: Script para ejecutar parches.
- **`set-production.txt`**: Archivo de configuración para el entorno de producción.
- **`setup.py`**: Script de configuración para la instalación del paquete de Python.

## Directorio `erpnext_ec`

Este es el directorio principal del módulo de Python. Contiene toda la lógica del backend, los doctypes, y los archivos públicos.

### `config/`

- **`desktop.py`**: Configuración del escritorio de ERPNext, añade los doctypes del módulo al escritorio.
- **`erpnext_ec.py`**: Define los puntos de entrada para los hooks de la aplicación.

### `erpnext_ec/` y `erpnext_sri/`

Estos directorios contienen los doctypes de la aplicación. Cada subdirectorio es un doctype con su propio controlador de Python (`.py`), JSON (`.json`) y script de cliente (`.js`).

- **`erpnext_ec/doctype/`**: Contiene los doctypes que extienden la funcionalidad de ERPNext para Ecuador, como `purchase_invoice`, `sales_invoice`, etc.
- **`erpnext_sri/doctype/`**: Contiene los doctypes relacionados con el SRI, como `sri_establishment`, `sri_ptoemi`, etc.

### `fixtures/`

Contiene datos que se cargan en la base de datos durante la instalación del módulo, como tipos de documentos, configuraciones iniciales, etc.

### `hooks.py`

Este archivo es fundamental en las aplicaciones de Frappe. Define cómo este módulo interactúa con el resto de ERPNext. Aquí se especifican los overrides de los métodos de los doctypes, los scripts que se deben cargar, las tareas programadas, etc.

### `install.py`

Script que se ejecuta durante la instalación del módulo.

### `patches/`

Contiene scripts de Python que se ejecutan para aplicar cambios en la base de datos o en los datos existentes después de una actualización del módulo.

### `public/`

Contiene los archivos que son accesibles públicamente a través del navegador.

- **`css/`**: Hojas de estilo CSS.
- **`dist/`**: Archivos generados a partir de otros archivos, como bundles de JavaScript.
- **`jinja/`**: Plantillas de Jinja2 para la generación de RIDES (representación impresa del documento electrónico) y correos electrónicos.
- **`js/`**: Archivos de JavaScript.
  - **`overrides/`**: Contiene scripts que sobreescriben o extienden la funcionalidad de los formularios de ERPNext, como `sales_invoice_form_sri.js` y `purchase_invoice_form_sri.js`. Aquí es donde se realizan las modificaciones a la interfaz de usuario de los doctypes.
- **`xml/`**: Archivos XML de ejemplo o para pruebas.

### `templates/`

Contiene plantillas para páginas web y otros componentes de la interfaz de usuario.

### `translations/`

Archivos de traducción para la internacionalización del módulo.

### `utilities/`

Contiene módulos de Python con funciones de utilidad que se utilizan en todo el módulo.

- **`doc_builder_*.py`**: Scripts para construir los documentos electrónicos en formato XML.
- **`signature_tool.py`**: Herramientas para la firma electrónica de los documentos.
- **`sri_ws.py`**: Funciones para la comunicación con los web services del SRI.
- **`xsd/`**: Esquemas XSD para la validación de los documentos XML.
