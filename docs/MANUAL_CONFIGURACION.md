# Manual de Configuración: ERPNext Ecuador

Este manual proporciona una guía paso a paso para configurar el módulo de localización de Ecuador en ERPNext.

## Paso 1: Configuración de la Compañía

Asegúrate de que los datos de tu compañía en ERPNext estén completos y correctos.
1.  Ve a `Contabilidad > Compañía` y selecciona tu compañía.
2.  Asegúrate de que los siguientes campos estén llenos:
    -   **Nombre de la Compañía**
    -   **RUC** (en el campo de ID de Impuestos)
    -   **Dirección Principal:** Es crucial que la compañía tenga una dirección principal (Billing Address) asignada y que esta contenga, como mínimo, el dato en "Línea de Dirección 1". Este campo se usa como la `dirMatriz` obligatoria en los documentos electrónicos.
    -   **Teléfono** y **Email**

## Paso 2: Configurar Ambientes del SRI

El módulo permite conectarse a los dos ambientes del SRI: Pruebas y Producción.
1.  Ve al módulo `Sri > Ambientes SRI`.
2.  Por defecto, el sistema incluye los dos ambientes que el SRI provee. No necesitas modificarlos, pero puedes revisarlos:
    -   **Ambiente 1 (Pruebas):** Usado para realizar pruebas de emisión de documentos sin validez tributaria.
    -   **Ambiente 2 (Producción):** Usado para la emisión de documentos reales con validez tributaria.
3.  En `Contabilidad > Configuración Contable`, en la sección de `Configuración Regional SRI`, selecciona el **Ambiente SRI por defecto** que deseas utilizar. Generalmente, se empieza con el ambiente de Pruebas.

## Paso 3: Configurar Firma Electrónica

La firma electrónica es indispensable para generar los documentos tributarios.
1.  **Obtén tu Firma Electrónica:** Adquiere un certificado de firma electrónica en formato `.p12` a través de una de las [entidades de certificación autorizadas en Ecuador](https://www.google.com/search?q=entidades+de+certificacion+autorizadas+ecuador).
2.  **Sube tu Firma al Sistema:**
    -   Ve al módulo `Sri > Firma Electrónica`.
    -   Crea un nuevo registro.
    -   Asígnale un nombre (ej. "Firma Principal").
    -   Sube tu archivo `.p12`.
    -   Ingresa la contraseña de tu firma electrónica. El sistema la almacenará de forma segura.
    -   Guarda el documento.
3.  **Asigna la Firma a tu Compañía:**
    -   Ve a `Contabilidad > Compañía` y selecciona tu compañía.
    -   En la sección `Configuración Regional SRI`, selecciona la firma que acabas de crear en el campo **Firma Electrónica Activa**.

## Paso 4: Crear Establecimientos y Puntos de Emisión

Debes registrar los establecimientos y puntos de emisión que tu compañía utiliza para facturar.
1.  Ve al módulo `Sri > Establecimientos`.
2.  Crea un nuevo **Establecimiento**.
    -   **Compañía:** Selecciona tu compañía.
    -   **Record Name (Código):** Ingresa el código del establecimiento asignado por el SRI (ej. `001`).
    -   **Description:** Dale un nombre descriptivo (ej. "Oficina Principal Quito").
3.  **Añadir Puntos de Emisión:**
    -   Dentro del mismo documento de **Establecimiento**, verás una tabla llamada **Puntos de Emisión**.
    -   Haz clic en "Agregar Fila" para añadir un nuevo punto de emisión.
    -   **Record Name (Código):** Ingresa el código del punto de emisión (ej. `001`).
    -   **Description:** Dale un nombre descriptivo (ej. "Caja 1").
    -   **Secuencias:** Ingresa el número inicial para cada tipo de documento (Factura, Nota de Crédito, etc.). Generalmente, este valor es `1` si estás empezando.
4.  Guarda el documento de Establecimiento. Repite el proceso para todos tus establecimientos y puntos de emisión.

## Paso 5: Verificar Secuencias (Opcional)

Las secuencias de los documentos se configuran dentro de cada Punto de Emisión (Paso 4). Sin embargo, puedes ver todas las secuencias del sistema de forma centralizada.
1.  Ve al módulo `Sri > Secuencias`.
2.  Aquí podrás ver y, si es necesario, ajustar el valor actual de la secuencia para cualquier tipo de documento y ambiente. **Atención:** Modificar esto directamente puede causar problemas si ya has emitido documentos.

## Paso 6: Crear Formatos de Impresión (RIDE)

El sistema necesita formatos de impresión específicos para generar la representación gráfica (RIDE) de los documentos electrónicos. El módulo puede crearlos por ti.

1.  Ve a la lista de **Formato de Impresión** (Puedes buscarlo en la barra de búsqueda).
2.  En la parte superior, verás un botón llamado **"Crear Formatos SRI"**.
3.  Haz clic en el botón. El sistema creará automáticamente todos los formatos de impresión necesarios (`Factura SRI`, `Retención SRI`, etc.).

## Paso 7: Configurar Plan de Cuentas

Para la correcta generación de los impuestos en los documentos XML, debes mapear tus cuentas contables de impuestos con los códigos que el SRI utiliza.

1.  Ve a `Contabilidad > Plan de Cuentas`.
2.  Busca las cuentas que utilizas para los impuestos (ej. IVA, ICE, etc.).
3.  Para cada cuenta de impuesto, edítala y busca el campo **`Sri Code`**.
4.  Introduce el código numérico que el SRI asigna a ese impuesto. Por ejemplo:
    -   Para IVA 12%, el `Sri Code` es `2`.
    -   Para IVA 0%, el `Sri Code` es `2` y el `Sri Codigo Porcentaje` es `0`.
    -   Para ICE, el `Sri Code` es `3`.
5.  Guarda los cambios en cada cuenta.

## ¡Configuración Completa!

Con estos pasos, tu sistema está listo para empezar a generar documentos electrónicos. Cuando crees una **Factura de Venta** y la **envíes (Submit)**, el sistema generará automáticamente el XML firmado y lo enviará al SRI (si la opción está habilitada). Podrás ver el estado de la autorización y el XML en el propio documento de la factura.

---

### **Importante: Requisitos para el Envío de Documentos**

Antes de que un documento pueda ser enviado exitosamente al SRI, el sistema validará que cumple con ciertos requisitos mínimos. Si al presionar "Enviar al SRI" recibes un aviso, asegúrate de cumplir con lo siguiente:

1.  **Email del Cliente:**
    -   **Error común:** "No se ha definido Email del cliente".
    -   **Solución:** El cliente seleccionado en la factura debe tener un correo electrónico válido. Ve a `CRM > Cliente`, busca al cliente, y asegúrate de que tenga una **dirección de facturación** guardada. Dentro de la dirección, el campo **Email** debe estar lleno.

2.  **Datos de Pago de la Factura:**
    -   **Error común:** "No se han definido datos de pago (solicitud de pago/entrada de pago)".
    -   **Solución:** Una factura debe tener un registro de pago asociado para poder ser enviada. Esto se puede hacer de dos maneras principales en ERPNext:
        -   **Opción A: Crear una Entrada de Pago.** Ve a `Contabilidad > Entrada de Pago`, crea un nuevo registro y aplícalo a la factura que deseas enviar. Esto es útil si la factura ya ha sido pagada total o parcialmente.
        -   **Opción B: Crear una Solicitud de Pago.** Desde la propia Factura de Venta, ve al menú `Crear > Solicitud de Pago`. Esto genera el registro necesario sin marcar la factura como pagada. Es la opción más común si solo necesitas cumplir el requisito para el envío al SRI.

## Paso 8: Configurar Descarga de Documentos desde el SRI

El módulo incluye una herramienta para descargar masivamente documentos electrónicos (Facturas, Retenciones, etc.) directamente desde el portal del SRI. Esta función es útil para la contabilidad de compras.

1.  Ve a `Integraciones > Configuración del Descargador del SRI` (SRI Downloader Settings).
2.  Rellena los siguientes campos:
    -   **SRI Login URL:** La URL de inicio de sesión del SRI. Viene pre-llenada.
    -   **SRI Target URL:** La URL a la que el sistema navegará después de iniciar sesión. Viene pre-llenada.
    -   **SRI Username:** Tu RUC o C.I. de usuario del SRI.
    -   **SRI Password:** Tu contraseña para el portal del SRI.
    -   **Timeout (seconds):** Tiempo máximo de espera para las operaciones en la página. 60 segundos es un valor recomendado.
    -   **Downloader Library (Librería de Descarga):** Esta opción te permite elegir la tecnología utilizada para la automatización del navegador.
        -   **Playwright (por defecto):** Una librería de automatización robusta y ampliamente utilizada.
        -   **Pydoll:** Una librería más nueva diseñada para simular el comportamiento humano de forma más precisa. **Selecciona esta opción si experimentas problemas con el CAPTCHA del SRI**, ya que `Pydoll` tiene más probabilidades de evitar ser detectado como un bot.

Una vez configurado, puedes ir a `Integraciones > Descarga de Facturas SRI` (SRI Invoice Download) para crear una nueva solicitud de descarga, especificando el año, mes, día y tipo de documento que deseas obtener.
