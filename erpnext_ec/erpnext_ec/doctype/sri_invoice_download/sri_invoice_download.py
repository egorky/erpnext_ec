import frappe
from frappe.model.document import Document
from frappe import _
import asyncio
import os
import base64
import time

class SRIInvoiceDownload(Document):
        pass

def _get_settings():
        return frappe.get_doc("SRI Downloader Settings")

def _get_chrome_executable_path():
        """
        Dynamically finds the path to the Playwright-installed Chromium executable.
        """
        try:
                home_dir = os.path.expanduser('~')
                playwright_cache_path = os.path.join(home_dir, '.cache', 'ms-playwright')

                if not os.path.isdir(playwright_cache_path):
                        return None

                for item in os.listdir(playwright_cache_path):
                        if item.startswith('chromium-') and os.path.isdir(os.path.join(playwright_cache_path, item)):
                                executable_path = os.path.join(playwright_cache_path, item, 'chrome-linux', 'chrome')
                                if os.path.exists(executable_path):
                                        return executable_path
                return None
        except Exception:
                # If any error occurs during path finding, return None safely.
                return None

async def _perform_sri_download_pydoll(docname):
        from pydoll.browser.chromium import Chrome
        from pydoll.browser.options import ChromiumOptions

        def log_debug(message):
                frappe.log_error(title="Pydoll Debug", message=message)

        log_debug("Starting Pydoll download process...")
        doc = frappe.get_doc("SRI Invoice Download", docname)
        settings = _get_settings()
        log_debug("Settings loaded.")

        username = settings.sri_username
        password = settings.get_password("sri_password")
        timeout_s = settings.timeout or 60

        if not username or not password:
                log_debug("Error: SRI Username or Password not set.")
                raise ValueError("SRI Username and Password must be set.")

        doc_type_map = {
                "Factura": "1",
                "Liquidación de compra de bienes y prestación de services": "2",
                "Notas de Crédito": "3",
                "Notas de Débito": "4",
                "Comprobante de Retención": "6"
        }

        log_debug("Setting Chromium options...")
        options = ChromiumOptions()

        chrome_path = _get_chrome_executable_path()
        if not chrome_path:
                log_debug("Chromium executable not found in Playwright cache.")
                raise FileNotFoundError("Could not find Playwright's Chromium executable. Please ensure Playwright is installed correctly (`playwright install chromium`).")

        options.binary_location = chrome_path
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--start-maximized')
        options.add_argument('--window-size=1024,768')
        options.add_argument('--disable-dev-shm-usage')
        fake_timestamp = int(time.time()) - (90 * 24 * 60 * 60)  # 90 days ago
        options.browser_preferences = {
            'profile': {
                'last_engagement_time': fake_timestamp,
                'exit_type': 'Normal',
                'exited_cleanly': True,
            },
            'newtab_page_location_override': 'https://www.google.com',
            'intl': {
                'accept_languages': 'es-EC,es,en-US,en',
            },
            'user_experience_metrics': {
                'reporting_enabled': False
            },
    'enable_do_not_track': True,
    'enable_referrers': False,
    'safebrowsing': {
        'enabled': False
    },
    # Disable data collection
    'profile': {
        'password_manager_enabled': False
    },
    'autofill': {
        'enabled': False
    },
    'search': {
        'suggest_enabled': False
    },
    'download': {
        'default_directory': '/tmp/automation-downloads',
        'prompt_for_download': False
    },
    # Session behavior
    'session': {
        'restore_on_startup': 5,  # Open New Tab Page
        'startup_urls': ['about:blank']
    },
    # Homepage
    'homepage': 'https://www.google.com',
    'homepage_is_newtabpage': False
        }

        log_debug(f"Chromium options set with binary location: {options.binary_location}")

        async with Chrome(options=options) as browser:
                tab = None
                try:
                        log_debug("Chrome launched. Starting new tab...")
                        tab = await browser.start()
                        log_debug("Tab object acquired.")

                        # 1. Login and navigate
                        log_debug(f"Navigating to login URL: {settings.sri_login_url}")
                        await tab.go_to(settings.sri_login_url, timeout=timeout_s)
                        log_debug("Login page loaded. Waiting for stability...")
                        await asyncio.sleep(5)

                        # Retry logic for filling credentials
                        last_exception = None
                        for attempt in range(3):
                                try:
                                        log_debug(f"Attempt {attempt + 1} to fill credentials.")
                                        user_field = await tab.find(name="usuario")
                                        await user_field.type_text(username, interval=1)
                                        await asyncio.sleep(2)

                                        pass_field = await tab.find(name="password")
                                        await pass_field.type_text(password, interval=1.2)

                                        log_debug("Credentials filled successfully.")
                                        last_exception = None
                                        break
                                except Exception as e:
                                        log_debug(f"Attempt {attempt + 1} failed with {type(e).__name__}. Retrying in 3 seconds...")
                                        last_exception = e
                                        await asyncio.sleep(3)

                        if last_exception:
                                raise last_exception

                        log_debug("Finding login button and waiting for it to be interactable.")
                        await asyncio.sleep(2)
                        login_button = await tab.find(id="kc-login")
                        #await login_button.wait_until(is_interactable=True, timeout=10)

                        log_debug("Clicking login button.")
                        await login_button.scroll_into_view()
                        await login_button.click_using_js()

                        log_debug("Waiting 5 seconds for page to load after login.")
                        await asyncio.sleep(10)
                        log_debug(f"Navigating to target URL: {settings.sri_target_url}")
                        all_cookies = await tab.get_cookies()
                        log_debug("Number of cookies: {len(all_cookies)}")
                        await tab.go_to(settings.sri_target_url, timeout=timeout_s)
                        log_debug("Target page loaded.")

                        # 2. Set download parameters
                        log_debug("Setting download parameters...")
                       # Year
                        await (await tab.find(name="frmPrincipal\:ano", timeout=10)).click(hold_time=0.5, x_offset=10, y_offset=5)
                        await asyncio.sleep(0.5)
                        await (await tab.find(tag_name='option', value=str(doc.year))).click(hold_time=0.5, x_offset=10, y_offset=5)
                        # Month
                        await (await tab.find(name="frmPrincipal\:mes", timeout=10)).click(hold_time=0.5, x_offset=10, y_offset=5)
                        await asyncio.sleep(2)
                        await (await tab.find(tag_name='option', value=str(doc.month))).click(hold_time=0.5, x_offset=10, y_offset=5)
                        # Day
                        await (await tab.find(name="frmPrincipal\:dia", timeout=10)).click(hold_time=0.5, x_offset=10, y_offset=5)
                        await asyncio.sleep(1.1)
                        await (await tab.find(tag_name='option', value=str(doc.day))).click(hold_time=0.5, x_offset=10, y_offset=5)
                        # Doc Type
                        doc_type_value = doc_type_map.get(doc.document_type)
                        if doc_type_value:
                                await (await tab.find(name="frmPrincipal\:cmbTipoComprobante", timeout=10)).click(hold_time=0.5, x_offset=10, y_offset=5)
                                await asyncio.sleep(1.5)
                                await (await tab.find(tag_name='option', value=doc_type_value)).click(hold_time=0.5, x_offset=10, y_offset=5)

                        log_debug("Download parameters set.")

                        # 3. Click search
                        await asyncio.sleep(2)
                        log_debug("Clicking search button (btnRecaptcha)...")
                        search_button = await tab.find(id="btnRecaptcha")
                        await search_button.wait_until(is_interactable=True, timeout=10)
                        await search_button.click(hold_time=0.5, x_offset=10, y_offset=5)
                        log_debug("Search button clicked.")

                        # 4. Intercept download
                        await asyncio.sleep(5)
                        log_debug("Waiting for download link selector...")
                        await tab.wait_for_selector("#frmPrincipal\\:lnkTxtlistado", timeout=timeout_s)
                        log_debug("Download link found.")

                        download_event = asyncio.Event()
                        download_content = None
                        file_name = "default_filename.txt"

                        async def on_request_paused(event):
                                nonlocal download_content, file_name
                                log_debug(f"Request paused: {event.request.url}")
                                if "frmPrincipal:j_idt160" in event.request.url:
                                        log_debug("Download request intercepted. Getting response body.")
                                        response = await tab.get_response_body(event.request_id)
                                        download_content = base64.b64decode(response['body'])
                                        for header in event.response_headers:
                                                if header['name'].lower() == 'content-disposition':
                                                        parts = header['value'].split(';')
                                                        for part in parts:
                                                                if part.strip().startswith('filename='):
                                                                        file_name = part.split('=')[1].strip('"')
                                                                        break
                                        await tab.continue_request(event.request_id)
                                        download_event.set()
                                else:
                                        await tab.continue_request(event.request_id)

                        tab.on('fetch.requestPaused', on_request_paused)
                        log_debug("Enabling fetch interception.")
                        await tab.enable_fetch_interception(handle_auth_requests=False)
                        log_debug("Clicking final download link.")
                        await (await tab.find(id="frmPrincipal:lnkTxtlistado")).click()
                        log_debug("Waiting for download event...")
                        await asyncio.wait_for(download_event.wait(), timeout=timeout_s)
                        log_debug("Download event received. Disabling interception.")
                        await tab.disable_fetch_interception()

                        if not download_content:
                                raise Exception("Failed to download file.")

                        # 5. Attach file to DocType
                        log_debug(f"Attaching file {file_name} to document {doc.name}")
                        temp_path = os.path.join("/tmp", file_name)
                        with open(temp_path, "wb") as f:
                                f.write(download_content)
                        with open(temp_path, "rb") as f:
                                file_content = f.read()
                        new_file = frappe.get_doc({
                                "doctype": "File", "file_name": file_name,
                                "attached_to_doctype": "SRI Invoice Download", "attached_to_name": doc.name,
                                "content": file_content, "is_private": 1
                        })
                        new_file.insert()
                        os.remove(temp_path)
                        log_debug("File attached successfully. Pydoll process complete.")
                        await tab.delete_all_cookies()
                        await browser.stop()

                except Exception as e:
                        if tab:
                                screenshot_path = frappe.get_site_path("public", "files", f"sri_error_{doc.name}.png")
                                log_debug(f"Pydoll process failed. Taking screenshot to {screenshot_path}")
                                await tab.take_screenshot(path=screenshot_path)
                        raise e


def _perform_sri_download_playwright(docname):
        from playwright.sync_api import sync_playwright

        doc = frappe.get_doc("SRI Invoice Download", docname)
        settings = _get_settings()
        username = settings.sri_username
        password = settings.get_password("sri_password")
        timeout_ms = (settings.timeout or 60) * 1000

        if not username or not password:
                raise ValueError("SRI Username and Password must be set.")

        doc_type_map = {
                "Factura": "1",
                "Liquidación de compra de bienes y prestación de servicios": "2",
                "Notas de Crédito": "3",
                "Notas de Débito": "4",
                "Comprobante de Retención": "6"
        }

        with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                try:
                        page.goto(settings.sri_login_url, timeout=timeout_ms)
                        page.locator("#usuario").fill(username)
                        page.locator("#password").fill(password)
                        page.locator("#kc-login").click()
                        page.wait_for_load_state('networkidle', timeout=timeout_ms)
                        page.goto(settings.sri_target_url, wait_until='networkidle', timeout=timeout_ms)
                        page.select_option("#frmPrincipal\\:ano", label=str(doc.year))
                        page.select_option("#frmPrincipal\\:mes", value=str(doc.month))
                        page.select_option("#frmPrincipal\\:dia", value=str(doc.day))
                        doc_type_value = doc_type_map.get(doc.document_type)
                        if doc_type_value:
                                page.select_option("#frmPrincipal\\:cmbTipoComprobante", value=doc_type_value)
                        page.locator("#btnRecaptcha").click()
                        page.wait_for_selector("#frmPrincipal\\:lnkTxtlistado", timeout=timeout_ms)
                        with page.expect_download() as download_info:
                                page.locator("#frmPrincipal\\:lnkTxtlistado").click()
                        download = download_info.value
                        temp_path = os.path.join("/tmp", download.suggested_filename)
                        download.save_as(temp_path)
                        with open(temp_path, "rb") as f:
                                file_content = f.read()
                        new_file = frappe.get_doc({
                                "doctype": "File", "file_name": download.suggested_filename,
                                "attached_to_doctype": "SRI Invoice Download", "attached_to_name": doc.name,
                                "content": file_content, "is_private": 1
                        })
                        new_file.insert()
                        os.remove(temp_path)

                        doc.status = "Completed"
                        doc.save()
                        frappe.db.commit()

                except Exception as e:
                        screenshot_path = frappe.get_site_path("public", "files", f"sri_error_{doc.name}.png")
                        page.screenshot(path=screenshot_path, full_page=True)
                        frappe.log_error(title=f"SRI Download Failed for {doc.name}", message=frappe.get_traceback())
                        raise e # Re-raise the exception to be caught by the main dispatcher
                finally:
                        browser.close()


def _perform_sri_download_camoufox(docname):
	from camoufox import Camoufox

	doc = frappe.get_doc("SRI Invoice Download", docname)
	settings = _get_settings()
	username = settings.sri_username
	password = settings.get_password("sri_password")
	timeout_ms = (settings.timeout or 60) * 1000

	if not username or not password:
		raise ValueError("SRI Username and Password must be set.")

	doc_type_map = {
		"Factura": "1",
		"Liquidación de compra de bienes y prestación de servicios": "2",
		"Notas de Crédito": "3",
		"Notas de Débito": "4",
		"Comprobante de Retención": "6"
	}

	profile_path = frappe.get_site_path("private", "camoufox_profile")

	# Comprehensive fingerprint injection configuration
	config = {
		# Window and Navigator Spoofing from user
		'window.outerHeight': 1056,
		'window.outerWidth': 1920,
		'window.innerHeight': 1008,
		'window.innerWidth': 1920,
		'window.history.length': 4,
		'navigator.userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
		'navigator.appCodeName': 'Mozilla',
		'navigator.appName': 'Netscape',
		'navigator.appVersion': '5.0 (Windows)',
		'navigator.oscpu': 'Windows NT 10.0; Win64; x64',
		'navigator.language': 'en-US',
		'navigator.languages': ['en-US'],
		'navigator.platform': 'Win32',
		'navigator.hardwareConcurrency': 12,
		'navigator.product': 'Gecko',
		'navigator.productSub': '20030107',
		'navigator.maxTouchPoints': 10,

		# Battery Status Spoofing
		'battery:charging': True,
		'battery:level': 0.85,
		'battery:chargingTime': 3600,
		'battery:dischargingTime': 10.00,

		# Comprehensive WebGL Spoofing
		"webGl:renderer": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x000046A6) Direct3D11 vs_5_0 ps_5_0, D3D11)",
		"webGl:vendor": "Google Inc. (Intel)",
		"webGl:contextAttributes": {
			"alpha": True, "antialias": True, "depth": True, "desynchronized": False,
			"failIfMajorPerformanceCaveat": False, "powerPreference": "default", "premultipliedAlpha": True,
			"preserveDrawingBuffer": False, "stencil": False, "xrCompatible": False
		},
		"webGl:supportedExtensions": [
			"ANGLE_instanced_arrays", "EXT_blend_minmax", "EXT_clip_control", "EXT_color_buffer_half_float",
			"EXT_depth_clamp", "EXT_disjoint_timer_query", "EXT_float_blend", "EXT_frag_depth",
			"EXT_polygon_offset_clamp", "EXT_shader_texture_lod", "EXT_texture_compression_bptc",
			"EXT_texture_compression_rgtc", "EXT_texture_filter_anisotropic", "EXT_texture_mirror_clamp_to_edge",
			"EXT_sRGB", "KHR_parallel_shader_compile", "OES_element_index_uint", "OES_fbo_render_mipmap",
			"OES_standard_derivatives", "OES_texture_float", "OES_texture_float_linear", "OES_texture_half_float",
			"OES_texture_half_float_linear", "OES_vertex_array_object", "WEBGL_blend_func_extended",
			"WEBGL_color_buffer_float", "WEBGL_compressed_texture_s3tc", "WEBGL_compressed_texture_s3tc_srgb",
			"WEBGL_debug_renderer_info", "WEBGL_debug_shaders", "WEBGL_depth_texture", "WEBGL_draw_buffers",
			"WEBGL_lose_context", "WEBGL_multi_draw", "WEBGL_polygon_mode"
		],
		"webGl:parameters": {
			"2849": 1, "2884": False, "2885": 1029, "2886": 2305, "2928": [0, 1], "2929": False, "2930": True,
			"2931": 1, "2932": 513, "2960": False, "2961": 0, "2962": 519, "2963": 4294967295, "2964": 7680,
			"2965": 7680, "2966": 7680, "2967": 0, "2968": 4294967295, "2978": [0, 0, 256, 256], "3024": True,
			"3042": False, "3074": None, "3088": [0, 0, 256, 256], "3089": False, "3106": [0, 0, 0, 0],
			"3107": [True, True, True, True], "3314": None, "3315": None, "3316": None, "3317": 4, "3330": None,
			"3331": None, "3332": None, "3333": 4, "3379": 16384, "3386": [32767, 32767], "3408": 4, "3410": 8,
			"3411": 8, "3412": 8, "3413": 8, "3414": 24, "3415": 0, "7936": "WebKit", "7937": "WebKit WebGL",
			"7938": "WebGL 1.0 (OpenGL ES 2.0 Chromium)", "10752": 0, "32773": [0, 0, 0, 0], "32777": 32774,
			"32823": False, "32824": 0, "32873": None, "32877": None, "32878": None, "32883": None, "32926": False,
			"32928": False, "32936": 1, "32937": 4, "32938": 1, "32939": False, "32968": 0, "32969": 1, "32970": 0,
			"32971": 1, "33000": None, "33001": None, "33170": 4352, "33901": [1, 1024], "33902": [1, 1],
			"34016": 33984, "34024": 16384, "34045": None, "34047": None, "34068": None, "34076": 16384,
			"34467": None, "34816": 519, "34817": 7680, "34818": 7680, "34819": 7680, "34852": None, "34853": None,
			"34854": None, "34855": None, "34856": None, "34857": None, "34858": None, "34859": None, "34860": None,
			"34877": 32774, "34921": 16, "34930": 16, "34964": None, "34965": None, "35071": None, "35076": None,
			"35077": None, "35371": None, "35373": None, "35374": None, "35375": None, "35376": None, "35377": None,
			"35379": None, "35380": None, "35657": None, "35658": None, "35659": None, "35660": 16, "35661": 32,
			"35723": None, "35724": "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)", "35725": None,
			"35738": 5121, "35739": 6408, "35968": None, "35977": None, "35978": None, "35979": None, "36003": 0,
			"36004": 4294967295, "36005": 4294967295, "36006": None, "36007": None, "36063": None, "36183": None,
			"36203": None, "36345": None, "36347": 4096, "36348": 30, "36349": 1024, "36387": None, "36388": None,
			"36392": None, "36795": None, "37137": None, "37154": None, "37157": None, "37440": False,
			"37441": False, "37443": 37444, "37444": None, "37445": "Google Inc. (Intel)",
			"37446": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x000046A6) Direct3D11 vs_5_0 ps_5_0, D3D11)",
			"37447": None, "38449": None
		},
		"webGl:shaderPrecisionFormats": {
			"35633,36336": {"rangeMin": 127, "rangeMax": 127, "precision": 23}, "35633,36337": {"rangeMin": 127, "rangeMax": 127, "precision": 23},
			"35633,36338": {"rangeMin": 127, "rangeMax": 127, "precision": 23}, "35633,36339": {"rangeMin": 31, "rangeMax": 30, "precision": 0},
			"35633,36340": {"rangeMin": 31, "rangeMax": 30, "precision": 0}, "35633,36341": {"rangeMin": 31, "rangeMax": 30, "precision": 0},
			"35632,36336": {"rangeMin": 127, "rangeMax": 127, "precision": 23}, "35632,36337": {"rangeMin": 127, "rangeMax": 127, "precision": 23},
			"35632,36338": {"rangeMin": 127, "rangeMax": 127, "precision": 23}, "35632,36339": {"rangeMin": 31, "rangeMax": 30, "precision": 0},
			"35632,36340": {"rangeMin": 31, "rangeMax": 30, "precision": 0}, "35632,36341": {"rangeMin": 31, "rangeMax": 30, "precision": 0}
		},
		"webGl2:renderer": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x000046A6) Direct3D11 vs_5_0 ps_5_0, D3D11)",
		"webGl2:vendor": "Google Inc. (Intel)",
		"webGl2:contextAttributes": {
			"alpha": True, "antialias": True, "depth": True, "desynchronized": False, "failIfMajorPerformanceCaveat": False,
			"powerPreference": "default", "premultipliedAlpha": True, "preserveDrawingBuffer": False, "stencil": False,
			"xrCompatible": False
		},
		"webGl2:supportedExtensions": [
			"EXT_clip_control", "EXT_color_buffer_float", "EXT_color_buffer_half_float", "EXT_conservative_depth",
			"EXT_depth_clamp", "EXT_disjoint_timer_query_webgl2", "EXT_float_blend", "EXT_polygon_offset_clamp",
			"EXT_render_snorm", "EXT_texture_compression_bptc", "EXT_texture_compression_rgtc",
			"EXT_texture_filter_anisotropic", "EXT_texture_mirror_clamp_to_edge", "EXT_texture_norm16",
			"KHR_parallel_shader_compile", "NV_shader_noperspective_interpolation", "OES_draw_buffers_indexed",
			"OES_sample_variables", "OES_shader_multisample_interpolation", "OES_texture_float_linear",
			"OVR_multiview2", "WEBGL_blend_func_extended", "WEBGL_clip_cull_distance",
			"WEBGL_compressed_texture_s3tc", "WEBGL_compressed_texture_s3tc_srgb", "WEBGL_debug_renderer_info",
			"WEBGL_debug_shaders", "WEBGL_lose_context", "WEBGL_multi_draw", "WEBGL_polygon_mode",
			"WEBGL_provoking_vertex", "WEBGL_stencil_texturing"
		],
		"webGl2:parameters": {
			"2849": 1, "2884": False, "2885": 1029, "2886": 2305, "2928": [0, 1], "2929": False, "2930": True,
			"2931": 1, "2932": 513, "2960": False, "2961": 0, "2962": 519, "2963": 4294967295, "2964": 7680,
			"2965": 7680, "2966": 7680, "2967": 0, "2968": 4294967295, "2978": [0, 0, 256, 256], "3024": True,
			"3042": False, "3074": 1029, "3088": [0, 0, 256, 256], "3089": False, "3106": [0, 0, 0, 0],
			"3107": [True, True, True, True], "3314": 0, "3315": 0, "3316": 0, "3317": 4, "3330": 0, "3331": 0,
			"3332": 0, "3333": 4, "3379": 16384, "3386": [32767, 32767], "3408": 4, "3410": 8, "3411": 8,
			"3412": 8, "3413": 8, "3414": 24, "3415": 0, "7936": "WebKit", "7937": "WebKit WebGL",
			"7938": "WebGL 2.0 (OpenGL ES 3.0 Chromium)", "10752": 0, "32773": [0, 0, 0, 0], "32777": 32774,
			"32823": False, "32824": 0, "32873": None, "32877": 0, "32878": 0, "32883": 2048, "32926": False,
			"32928": False, "32936": 1, "32937": 4, "32938": 1, "32939": False, "32968": 0, "32969": 1, "32970": 0,
			"32971": 1, "33000": 2147483647, "33001": 2147483647, "33170": 4352, "33901": [1, 1024],
			"33902": [1, 1], "34016": 33984, "34024": 16384, "34045": 2, "34047": None, "34068": None,
			"34076": 16384, "34467": None, "34816": 519, "34817": 7680, "34818": 7680, "34819": 7680, "34852": 8,
			"34853": 1029, "34854": 1029, "34855": 1029, "34856": 1029, "34857": 1029, "34858": 1029, "34859": 1029,
			"34860": 1029, "34877": 32774, "34921": 16, "34930": 16, "34964": None, "34965": None, "35071": 2048,
			"35076": -8, "35077": 7, "35371": 12, "35373": 12, "35374": 24, "35375": 24, "35376": 65536,
			"35377": 212992, "35379": 200704, "35380": 256, "35657": 4096, "35658": 16384, "35659": 120,
			"35660": 16, "35661": 32, "35723": 4352, "35724": "WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)",
			"35725": None, "35738": 5121, "35739": 6408, "35968": 4, "35977": False, "35978": 120, "35979": 4,
			"36003": 0, "36004": 4294967295, "36005": 4294967295, "36006": None, "36007": None, "36063": 8,
			"36183": 16, "36203": 4294967294, "36345": None, "36347": 4096, "36348": 30, "36349": 1024,
			"36387": False, "36388": False, "36392": None, "36795": None, "37137": 0, "37154": 120, "37157": 120,
			"37440": False, "37441": False, "37443": 37444, "37444": None, "37445": "Google Inc. (Intel)",
			"37446": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x000046A6) Direct3D11 vs_5_0 ps_5_0, D3D11)",
			"37447": 0, "38449": None
		},
		"webGl2:shaderPrecisionFormats": {
			"35633,36336": {"rangeMin": 127, "rangeMax": 127, "precision": 23}, "35633,36337": {"rangeMin": 127, "rangeMax": 127, "precision": 23},
			"35633,36338": {"rangeMin": 127, "rangeMax": 127, "precision": 23}, "35633,36339": {"rangeMin": 31, "rangeMax": 30, "precision": 0},
			"35633,36340": {"rangeMin": 31, "rangeMax": 30, "precision": 0}, "35633,36341": {"rangeMin": 31, "rangeMax": 30, "precision": 0},
			"35632,36336": {"rangeMin": 127, "rangeMax": 127, "precision": 23}, "35632,36337": {"rangeMin": 127, "rangeMax": 127, "precision": 23},
			"35632,36338": {"rangeMin": 127, "rangeMax": 127, "precision": 23}, "35632,36339": {"rangeMin": 31, "rangeMax": 30, "precision": 0},
			"35632,36340": {"rangeMin": 31, "rangeMax": 30, "precision": 0}, "35632,36341": {"rangeMin": 31, "rangeMax": 30, "precision": 0}
		}
	}

	with Camoufox(
		user_data_dir=profile_path,
		headless=True,
		persistent_context=True,
		config=config,
		i_know_what_im_doing=True
	) as driver:
		page = driver.new_page()
		try:
			page.goto(settings.sri_login_url, timeout=timeout_ms)
			page.locator("#usuario").fill(username)
			page.locator("#password").fill(password)
			page.locator("#kc-login").click()
			page.wait_for_load_state('networkidle', timeout=timeout_ms)
			page.goto(settings.sri_target_url, wait_until='networkidle', timeout=timeout_ms)
			page.select_option(f'select[name="frmPrincipal:ano"]', label=str(doc.year))
			page.select_option(f'select[name="frmPrincipal:mes"]', value=str(doc.month))
			page.select_option(f'select[name="frmPrincipal:dia"]', value=str(doc.day))
			doc_type_value = doc_type_map.get(doc.document_type)
			if doc_type_value:
				page.select_option(f'select[name="frmPrincipal:cmbTipoComprobante"]', value=doc_type_value)
			page.locator("#btnRecaptcha").click()
			page.wait_for_selector("#frmPrincipal\\:lnkTxtlistado", timeout=timeout_ms)
			with page.expect_download() as download_info:
				page.locator("#frmPrincipal\\:lnkTxtlistado").click()
			download = download_info.value
			temp_path = os.path.join("/tmp", download.suggested_filename)
			download.save_as(temp_path)
			with open(temp_path, "rb") as f:
				file_content = f.read()
			new_file = frappe.get_doc({
				"doctype": "File", "file_name": download.suggested_filename,
				"attached_to_doctype": "SRI Invoice Download", "attached_to_name": doc.name,
				"content": file_content, "is_private": 1
			})
			new_file.insert()
			os.remove(temp_path)
			doc.status = "Completed"
			doc.save(ignore_version=True)
			frappe.db.commit()
		except Exception as e:
			screenshot_path = frappe.get_site_path("public", "files", f"sri_error_{doc.name}.png")
			page.screenshot(path=screenshot_path, full_page=True)
			frappe.log_error(title=f"SRI Download Failed for {doc.name}", message=frappe.get_traceback())
			raise e

def _perform_sri_download(docname):
        settings = _get_settings()

        try:
                if settings.downloader_library == "Pydoll":
                        asyncio.run(_perform_sri_download_pydoll(docname))
                elif settings.downloader_library == "Camoufox":
                        _perform_sri_download_camoufox(docname)
                else: # Default to Playwright
                        _perform_sri_download_playwright(docname)

        except Exception as e:
                # Use ignore_version=True to prevent TimestampMismatchError if the doc was
                # modified while the background job was running.
                doc_to_fail = frappe.get_doc("SRI Invoice Download", docname)
                doc_to_fail.status = "Failed"
                doc_to_fail.save(ignore_version=True)
                frappe.db.commit()
                # Log any exception that was not caught and logged by the specific downloaders.
                # This is crucial for debugging failures during the initialization phase (e.g., browser not found).
                frappe.log_error(title=f"SRI Download Failed for {doc.name}", message=frappe.get_traceback())


@frappe.whitelist()
def start_download(docname):
        """
        Enqueues a background job to download invoices from the SRI portal.
        """
        frappe.enqueue(
        "erpnext_ec.erpnext_ec.doctype.sri_invoice_download.sri_invoice_download._perform_sri_download",
        queue="long",
        timeout=1500,
        docname=docname
    )

        doc = frappe.get_doc("SRI Invoice Download", docname)
        doc.status = "In Progress"
        doc.save()
        frappe.db.commit()

        return _("Download process has been enqueued and is running in the background.")
