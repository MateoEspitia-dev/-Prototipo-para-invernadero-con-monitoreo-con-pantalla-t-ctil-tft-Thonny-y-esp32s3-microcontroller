# MicroPython para ESP32-S3
# UI táctil en ILI9341 + XPT2046
# Sensores I2C: SHT30 (Temp/Humedad), BH1750 (Luz)
# ADC: Humedad de Suelo (3 canales)
# Actuadores: Ventilador, Riego, Fertirriego
# ------------------------------------------------------------
from machine import Pin, SPI, I2C, ADC
from ili9341 import Display, color565
from xpt2046 import Touch
import time
import math
# ================== CONFIGURACIÓN DE PINES ==================
# --- Pantalla ILI9341 (SPI) ---
TFT_MOSI = 48
TFT_MISO = 41
TFT_SCK  = 45
LCD_CS   = 1
LCD_DC   = 38
LCD_RST  = 40

# --- Touch XPT2046 (SPI) ---
TOUCH_MOSI = 11
TOUCH_MISO = 13
TOUCH_SCK  = 3
TOUCH_CS   = 10

# --- Bus I2C (SHT30 + BH1750) ---f
I2C_SDA = 15
I2C_SCL = 16
I2C_FREQ = 100000

# --- ADC Humedad de Suelo ---
# --- Ajustado para 3 sensores en los pines 4, 5, 6
SOIL_ADC_PINS = (4, 5, 6)

# --- Actuadores ---
PIN_RIEGO = 18
PIN_FERTI = 8
PIN_FAN   = 9

# ================== COLORES ==================
BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)
RED = color565(255, 0, 0)
GREEN = color565(0, 255, 0)
LOGO_GREEN = color565(0, 200, 0) # Verde para el logo (puedes ajustar)
BLUE = color565(0, 0, 255)
CYAN = color565(0, 255, 255)
MAGENTA = color565(255, 0, 255)
YELLOW = color565(255, 255, 0)
LIGHT_BLUE = color565(173, 216, 230)

# ---> NUEVAS CONSTANTES PARA AUTOMATIZACIÓN <---
# Riego (Sensor 2 - Pin 5)
HUMEDAD_MINIMA_RIEGO = 0      # Porcentaje (%) para activar riego
RIEGO_DURACION = 5            # Segundos que dura el riego
RIEGO_INTERVALO = 10          # Segundos de espera después de regar antes de volver a comprobar

# Fertirriego
FERTI_INTERVALO = 300          # Segundos entre activaciones
FERTI_DURACION = 4            # Segundos que dura la fertirrigación

# Ventilador
TEMP_UMBRAL_FAN = 36          # Grados Celsius para activar el ventilador
UMBRAL_DESCONECTADO = 59000

# ---> VARIABLES PARA CONTROLAR TIEMPOS <---
# Guardarán el tiempo (en milisegundos) de la última acción
ultimo_riego_fin = 0
ultimo_ferti_inicio = 0
riego_activo = False
riego_inicio_tiempo = 0
ferti_activo = False
ferti_inicio_tiempo = 0

# ================== IMPORTAR DATOS DEL LOGO ==================
try:
    from logo_data import WIDTH as LOGO_WIDTH, HEIGHT as LOGO_HEIGHT, logo_bytes
    print(f"Logo data loaded: {LOGO_WIDTH}x{LOGO_HEIGHT}")
    logo_available = True
except ImportError:
    print("ERROR: Could not find or import logo_data.py!")
    LOGO_WIDTH, LOGO_HEIGHT, logo_bytes = 0, 0, None
    logo_available = False
except Exception as e:
    print(f"Error importing logo data: {e}")
    LOGO_WIDTH, LOGO_HEIGHT, logo_bytes = 0, 0, None
    logo_available = False
    
    
def draw_crosshair_logo(center_x, center_y, radius, line_length):
    """ Dibuja un logo simple de mira/crosshair """
    outer_radius = radius
    middle_radius = radius * 2 // 3 # Radio intermedio
    inner_radius = radius // 3      # Radio interno
    corner_offset = radius + 5      # Desplazamiento para las esquinas
    corner_size = 15                # Tamaño de las líneas de esquina

    # 1. Círculo exterior (blanco o gris claro) - Usaremos blanco
    display.draw_circle(center_x, center_y, outer_radius, WHITE)
    display.draw_circle(center_x, center_y, outer_radius - 1, WHITE) # Más grueso

    # 2. Círculo intermedio (azul claro relleno)
    display.fill_circle(center_x, center_y, middle_radius, LIGHT_BLUE)

    # 3. Círculo interior (blanco para tapar el azul)
    display.fill_circle(center_x, center_y, inner_radius, WHITE)

    # 4. Líneas cruzadas (negras)
    line_half = line_length // 2
    display.draw_line(center_x - line_half, center_y, center_x + line_half, center_y, BLACK) # Horizontal
    display.draw_line(center_x, center_y - line_half, center_x, center_y + line_half, BLACK) # Vertical
    # Líneas más gruesas (opcional)
    display.draw_line(center_x - line_half, center_y+1, center_x + line_half, center_y+1, BLACK) 
    display.draw_line(center_x+1, center_y - line_half, center_x+1, center_y + line_half, BLACK)

    # 5. Marcas de esquina (negras) - Aproximadas con líneas
    # Superior izquierda
    display.draw_line(center_x - corner_offset, center_y - corner_offset + corner_size, center_x - corner_offset, center_y - corner_offset, BLACK) # Vertical
    display.draw_line(center_x - corner_offset, center_y - corner_offset, center_x - corner_offset + corner_size, center_y - corner_offset, BLACK) # Horizontal
    # Superior derecha
    display.draw_line(center_x + corner_offset, center_y - corner_offset + corner_size, center_x + corner_offset, center_y - corner_offset, BLACK) # Vertical
    display.draw_line(center_x + corner_offset, center_y - corner_offset, center_x + corner_offset - corner_size, center_y - corner_offset, BLACK) # Horizontal
    # Inferior izquierda
    display.draw_line(center_x - corner_offset, center_y + corner_offset - corner_size, center_x - corner_offset, center_y + corner_offset, BLACK) # Vertical
    display.draw_line(center_x - corner_offset, center_y + corner_offset, center_x - corner_offset + corner_size, center_y + corner_offset, BLACK) # Horizontal
    # Inferior derecha
    display.draw_line(center_x + corner_offset, center_y + corner_offset - corner_size, center_x + corner_offset, center_y + corner_offset, BLACK) # Vertical
    display.draw_line(center_x + corner_offset, center_y + corner_offset, center_x + corner_offset - corner_size, center_y + corner_offset, BLACK) # Horizontal
    
def draw_temp_logo(x_start, y_start, size):
    """ Dibuja un logo simple de sol + termómetro """
    sun_radius = size // 3
    sun_x = x_start + sun_radius + 5
    sun_y = y_start + size // 2
    
    thermo_width = size // 5
    thermo_height = size
    thermo_x = sun_x + sun_radius + 10 
    thermo_y = y_start
    thermo_bulb_radius = thermo_width // 2 + 2
    
    # 1. Sol (Círculo rojo relleno)
    display.fill_circle(sun_x, sun_y, sun_radius, RED)
    
    # 2. Rayos del sol (Líneas rojas) - Aproximado
    ray_len = 5
    display.draw_line(sun_x + sun_radius, sun_y, sun_x + sun_radius + ray_len, sun_y, RED) # Derecha
    display.draw_line(sun_x - sun_radius, sun_y, sun_x - sun_radius - ray_len, sun_y, RED) # Izquierda
    display.draw_line(sun_x, sun_y + sun_radius, sun_x, sun_y + sun_radius + ray_len, RED) # Abajo
    display.draw_line(sun_x, sun_y - sun_radius, sun_x, sun_y - sun_radius - ray_len, RED) # Arriba
    # Diagonales (simplificado)
    diag_offset = int(sun_radius * 0.707) # Aprox en 45 grados
    diag_len = int(ray_len * 0.707)
    display.draw_line(sun_x + diag_offset, sun_y - diag_offset, sun_x + diag_offset + diag_len, sun_y - diag_offset - diag_len, RED) # Sup Der
    display.draw_line(sun_x - diag_offset, sun_y - diag_offset, sun_x - diag_offset - diag_len, sun_y - diag_offset - diag_len, RED) # Sup Izq
    display.draw_line(sun_x + diag_offset, sun_y + diag_offset, sun_x + diag_offset + diag_len, sun_y + diag_offset + diag_len, RED) # Inf Der
    display.draw_line(sun_x - diag_offset, sun_y + diag_offset, sun_x - diag_offset - diag_len, sun_y + diag_offset + diag_len, RED) # Inf Izq

    # 3. Termómetro - Contorno (Negro o Blanco)
    thermo_outline_color = BLACK # O WHITE si prefieres
    # Bulbo inferior
    display.draw_circle(thermo_x + thermo_width // 2, thermo_y + thermo_height - thermo_bulb_radius, thermo_bulb_radius, thermo_outline_color)
    # Cuerpo vertical
    display.draw_rectangle(thermo_x, thermo_y, thermo_width, thermo_height - thermo_bulb_radius, thermo_outline_color)
    # Tapa superior (opcional)
    display.draw_line(thermo_x, thermo_y, thermo_x + thermo_width -1 , thermo_y, thermo_outline_color) 

    # 4. Termómetro - Relleno (Rojo)
    fill_height = thermo_height * 2 // 3 # Qué tan lleno está (ej. 2/3)
    display.fill_circle(thermo_x + thermo_width // 2, thermo_y + thermo_height - thermo_bulb_radius, thermo_bulb_radius - 2, RED) # Bulbo relleno
    display.fill_rectangle(thermo_x + 2, thermo_y + thermo_height - fill_height , thermo_width - 4, fill_height - thermo_bulb_radius, RED) # Cuerpo relleno

    # 5. Marcas del termómetro (Negro o Blanco)
    tick_x = thermo_x + thermo_width + 5
    num_ticks = 5
    tick_spacing = (thermo_height - thermo_bulb_radius - 10) // (num_ticks -1)
    for i in range(num_ticks):
        tick_y = thermo_y + 5 + i * tick_spacing
        display.draw_line(tick_x, tick_y, tick_x + 5, tick_y, thermo_outline_color)

# ---> NUEVA FUNCIÓN: Dibuja el logo de humedad <---
def draw_humidity_logo(x_center, y_center, radius):
    """ Dibuja un logo simple de gota con % """
    
    # 1. Gota (Círculo azul relleno - simplificado)
    display.fill_circle(x_center, y_center, radius, BLUE)
    
    #     # Rellenar manualmente podría ser necesario
        
    # 2. Símbolo de Porcentaje (%) en blanco
    percent_color = WHITE
    line_thickness = 2 # Grosor simulado
    circle_radius = radius // 4
    circle_offset_x = radius // 3
    circle_offset_y = radius // 3
    
    # Círculo superior izquierdo
    display.fill_circle(x_center - circle_offset_x, y_center - circle_offset_y, circle_radius, percent_color)
    
    # Círculo inferior derecho
    display.fill_circle(x_center + circle_offset_x, y_center + circle_offset_y, circle_radius, percent_color)
    
    # Línea diagonal (gruesa)
    diag_length = int(radius * 0.8) # Largo relativo
    angle = -45 # Ángulo en grados para la diagonal
    rad_angle = math.radians(angle)
    start_x = int(x_center - (diag_length // 2) * math.cos(rad_angle))
    start_y = int(y_center - (diag_length // 2) * math.sin(rad_angle))
    end_x = int(x_center + (diag_length // 2) * math.cos(rad_angle))
    end_y = int(y_center + (diag_length // 2) * math.sin(rad_angle))
    
    # Dibujar línea gruesa (varias líneas paralelas)
    for i in range(-line_thickness // 2, line_thickness // 2 + 1):
        # Desplazamiento perpendicular (aproximado)
        offset_x = int(i * math.sin(rad_angle)) 
        offset_y = int(-i * math.cos(rad_angle))
        display.draw_line(start_x + offset_x, start_y + offset_y, end_x + offset_x, end_y + offset_y, percent_color)
        

# ---> NEW FUNCTION: Draws the sun logo <---
def draw_sun_logo(x_center, y_center, radius):
    """ Draws a simple green sun logo """
    body_radius = radius * 2 // 3 # Radius of the central circle
    ray_length = radius // 3      # Length of the rays
    num_rays = 8                  # Number of rays to draw

    # 1. Sun Body (Filled Green Circle)
    display.fill_circle(x_center, y_center, body_radius, LOGO_GREEN)

    # 2. Sun Rays (Green Lines)
    for i in range(num_rays):
        angle = math.radians(i * (360 / num_rays)) # Calculate angle for each ray
        # Calculate start point (on the edge of the body)
        start_x = int(x_center + body_radius * math.cos(angle))
        start_y = int(y_center + body_radius * math.sin(angle))
        # Calculate end point (further out)
        end_x = int(x_center + (body_radius + ray_length) * math.cos(angle))
        end_y = int(y_center + (body_radius + ray_length) * math.sin(angle))
        # Draw the ray (make it slightly thicker)
        display.draw_line(start_x, start_y, end_x, end_y, LOGO_GREEN)
        # Optional: Thicker line by drawing offset lines (can be tricky with angles)
        # display.draw_line(start_x+1, start_y, end_x+1, end_y, LOGO_GREEN)
# ... (Código anterior sin cambios hasta COLORES) ...
def draw_soil_logo(x_start, y_start, width, height):
    """ Draws a simplified cyan soil sensor logo """
    body_height = height * 3 // 4 # Main rectangular part
    tip_height = height // 4      # Pointy tip part
    top_width = width // 3        # Small top connector width (approx)
    
    # 1. Main Body (Cyan Rectangle)
    display.fill_rectangle(x_start, y_start, width, body_height, CYAN)
    
    # 2. Pointy Tip (Approximate with triangle or lines)
    tip_y_start = y_start + body_height
    # Using fill_triangle if available (replace if not)
    try:
        display.fill_triangle(x_start, tip_y_start, 
                              x_start + width, tip_y_start, 
                              x_start + width // 2, y_start + height, CYAN)
    except AttributeError: 
        # Fallback using lines if fill_triangle doesn't exist
        display.draw_line(x_start, tip_y_start, x_start + width // 2, y_start + height, CYAN)
        display.draw_line(x_start + width, tip_y_start, x_start + width // 2, y_start + height, CYAN)
        
        

# ================== COLORES ==================
BLACK = color565(0, 0, 0)
WHITE = color565(255, 255, 255)
RED = color565(255, 0, 0)
GREEN = color565(0, 255, 0)
# ... (Resto de colores) ...
LOGO_GREEN = color565(0, 200, 0) 

# ... (Resto del código hasta las funciones de pantalla) ...

# ================== DRIVERS SENSORES ==================
class SHT30:
    def __init__(self, i2c, addr=0x44):
        self.i2c = i2c
        self.addr = addr

    def read(self):
        self.i2c.writeto(self.addr, bytes([0x2C, 0x06]))
        time.sleep_ms(15)
        data = self.i2c.readfrom(self.addr, 6)
        t_raw = (data[0] << 8) | data[1]
        rh_raw = (data[3] << 8) | data[4]
        temp_c = -45 + (175 * (t_raw / 65535.0))
        rh = 100 * (rh_raw / 65535.0)
        return temp_c, rh

class BH1750:
    POWER_ON = 0x01
    RESET = 0x07
    CONT_HIGH_RES = 0x10

    def __init__(self, i2c, addr=0x23):
        self.i2c = i2c
        self.addr = addr
        self.i2c.writeto(self.addr, bytes([self.POWER_ON]))
        time.sleep_ms(10)
        self.i2c.writeto(self.addr, bytes([self.RESET]))
        time.sleep_ms(10)
        self.i2c.writeto(self.addr, bytes([self.CONT_HIGH_RES]))
        time.sleep_ms(180)

    def read_lux(self):
        data = self.i2c.readfrom(self.addr, 2)
        raw = (data[0] << 8) | data[1]
        lux = raw / 1.2
        return lux

# ================== INICIALIZACIÓN HW ==================
# SPI TFT
spi_tft = SPI(1, baudrate=10_000_000, mosi=Pin(TFT_MOSI), miso=Pin(TFT_MISO), sck=Pin(TFT_SCK))
display = Display(spi_tft, cs=Pin(LCD_CS), dc=Pin(LCD_DC), rst=Pin(LCD_RST), width=320, height=240, rotation=270)

# SPI Touch
spi_touch = SPI(2, baudrate=1_000_000, mosi=Pin(TOUCH_MOSI), miso=Pin(TOUCH_MISO), sck=Pin(TOUCH_SCK))
touch = Touch(spi_touch, cs=Pin(TOUCH_CS), width=320, height=240,
              x_min=200, x_max=3900, y_min=200, y_max=3900)

# I2C Sensores
i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=I2C_FREQ)
sht30 = SHT30(i2c)
bh1750 = BH1750(i2c)

# ADC Suelo
soil_adcs = [ADC(Pin(p)) for p in SOIL_ADC_PINS]
for adc in soil_adcs:
    try:
        adc.atten(ADC.ATTN_11DB)
    except:
        pass

# Actuadores
riego = Pin(PIN_RIEGO, Pin.OUT); riego.value(1)
ferti = Pin(PIN_FERTI, Pin.OUT); ferti.value(1)
fan   = Pin(PIN_FAN,   Pin.OUT); fan.value(1)

# ================== UI BÁSICA ==================
# (Funciones de UI sin cambios...)
def pantalla_bienvenida():
    # 1. Fondo Negro
    display.clear(BLACK) 
    
    logo_available = False # Assume no logo initially
    # Check if logo data was successfully imported earlier
    if 'LOGO_WIDTH' in globals() and LOGO_WIDTH > 0: 
        logo_available = True
        logo_x = (display.width - LOGO_WIDTH) // 2
        logo_y = (display.height - LOGO_HEIGHT) // 2 - 10 # Move logo slightly up
        texto_superior_y = logo_y - 20 
        if texto_superior_y < 5: texto_superior_y = 5 
        texto_inferior_y = logo_y + LOGO_HEIGHT + 10 # Move text closer
    else:
        # Fallback positions if no logo
        texto_superior_y = 40
        texto_inferior_y = 140

    # 2. Dibujar texto superior
    texto_superior = "INVERNADERO AUTOMATIZADO"
    texto_superior_x = (display.width - (len(texto_superior) * 8)) // 2 
    display.draw_text8x8(texto_superior_x, texto_superior_y, texto_superior, CYAN, BLACK)

    # 3. Dibujar logo (si está disponible)
    if logo_available and logo_bytes:
        print(f"Dibujando logo {LOGO_WIDTH}x{LOGO_HEIGHT} en ({logo_x}, {logo_y})...")
        try:
            start_time = time.ticks_ms()
            bytes_per_pixel = 2
            black_value_threshold = 0x0841 

            for y_rel in range(LOGO_HEIGHT):
                for x_rel in range(LOGO_WIDTH):
                    index = (y_rel * LOGO_WIDTH + x_rel) * bytes_per_pixel
                    if index + 1 < len(logo_bytes):
                        byte1 = logo_bytes[index]
                        byte2 = logo_bytes[index + 1]
                        color_value = (byte1 << 8) | byte2
                        if color_value >= black_value_threshold: 
                            display.draw_pixel(logo_x + x_rel, logo_y + y_rel, LOGO_GREEN)
                    else: break
                else: continue
                break
            draw_time = time.ticks_diff(time.ticks_ms(), start_time)
            # print(f"Logo dibujado en {draw_time} ms.") # Optional print

        except Exception as e:
            print(f"Error dibujando logo: {e}")
            display.draw_text8x8(logo_x, logo_y + LOGO_HEIGHT // 2, "Error Logo", WHITE, RED)
    elif not logo_available:
         # Mensaje si falta logo_data.py
         display.draw_text8x8(40, 100, "Error: Falta logo_data.py", RED, BLACK)


    # 4. Dibujar texto inferior (SIEMPRE visible durante la espera)
    texto_inferior = "Click de Inicio"
    texto_inferior_x = (display.width - (len(texto_inferior) * 8)) // 2 
    display.draw_text8x8(texto_inferior_x, texto_inferior_y, texto_inferior, GREEN, BLACK)

    # 5. Espera y Detecta Toque (DENTRO de bienvenida)
    start_touch = None
    start_time_welcome = time.ticks_ms()
    timeout_ms = 3000 # Espera máximo 3 segundos por un toque

    while time.ticks_diff(time.ticks_ms(), start_time_welcome) < timeout_ms:
        # ---> USA raw_touch() aquí <---
        if touch.raw_touch(): # raw_touch() devuelve (x,y) o None, no necesita calibración
            start_touch = True
            print("Toque detectado para calibrar.")
            break # Sal del bucle si se detecta toque
        time.sleep_ms(50) # Revisa ~20 veces por segundo

    return start_touch # Devuelve True si hubo toque, False/None si no


def draw_menu():
    display.clear(BLACK)
    display.draw_text8x8(90, 15, "MENU DE CONTROL", YELLOW, BLACK)
    botones = [
        ("TEMP",        20,  45, RED),
        ("HUMEDAD",     170, 45, BLUE),
        ("LUZ",         20,  95, GREEN),
        ("SUELO",       170, 95, CYAN),
        ("RIEGO",       20,  145, MAGENTA),
        ("FERTIRRIEGO", 170, 145, YELLOW),
        ("VENTILADOR",  70,  195, WHITE),
    ]
    for txt, x, y, color in botones:
        display.fill_rectangle(x, y, 130, 35, color)
        display.draw_text8x8(x+8, y+12, txt, BLACK, color)


def detectar_boton(x, y):
    if 70 <= x <= 110 and 100 <= y <= 115:
        return "TEMP"
    if 65 <= y <= 105 and 70 <= x <= 110:
        return "LUZ"
    if 40 <= y <= 45 and 65 <= x <= 105:
        return "RIEGO"
    if 100 <= y <= 115 and 10 <= x <= 50:
        return "HUMEDAD"
    if 75 <= y <= 85 and 10 <= x <= 50:
        return "SUELO"
    if 40 <= y <= 45 and 10 <= x <= 50:
        return "FERTIRRIEGO"
    if 10 <= y <= 12 and 43 <= x <= 87:
        return "VENTILADOR"
    return None

def boton_volver():
    display.fill_rectangle(100, 205, 120, 28, RED)
    display.draw_text8x8(128, 214, "VOLVER", WHITE, RED)

def manejar_interaccion(button_zones):
    while True:
        pos = touch.get_touch()
        if pos:
            x, y = pos
            x, y = y, x
            print(f"Toque detectado en: X={x}, Y={y}")
            for name, (x_min, x_max, y_min, y_max) in button_zones.items():
                if x_min <= x <= x_max and y_min <= y <= y_max:
                    return name
        time.sleep(0.3)

# --- Lecturas y pantallas ---

def pantalla_temp():
    display.clear(BLACK)
    boton_volver() # Dibuja el botón VOLVER una vez
    
    logo_x = 15
    logo_y = 30
    logo_size = 100 # Tamaño base del logo (ajusta según necesites)
    draw_temp_logo(logo_x, logo_y, logo_size)
    while True: 
        check_automation(); 
        try:
            t, _ = sht30.read()
            # ---> Ajusta posición del texto para no solapar el logo <---
            text_x = logo_x + logo_size + 40 # Mueve el texto a la derecha del logo
            display.draw_text8x8(text_x, 90, "Temperatura:", RED, BLACK)
            display.draw_text8x8(text_x, 110, f"{t:.2f} C   ", RED, BLACK) 
        except Exception as e:
            display.draw_text8x8(20, 100, f"Err SHT30:{e} ", RED, BLACK)

        # 2. Comprobar toque en VOLVER
        pos = touch.get_touch()
        if pos:
            x, y = pos; x, y = y, x # Tu transformación de coordenadas
            # Coordenadas del botón volver: (35, 80, 3, 15)
            if 35 <= x <= 80 and 3 <= y <= 15: 
                return # Salir de la función

        # 3. Pausa
        time.sleep(0.5) 

def pantalla_humedad():
    display.clear(BLACK)
    boton_volver() # Dibuja el botón VOLVER una vez
    # --- Dibuja el logo ---
    logo_center_x = 70   # Posición X del centro del logo
    logo_center_y = 95   # Posición Y del centro del logo
    logo_radius = 30     # Radio (tamaño) del logo
    draw_humidity_logo(logo_center_x, logo_center_y, logo_radius)
    # ----------------------

    while True: # Bucle de actualización
        check_automation()
        # 1. Leer sensor y mostrar
        try:
            _, rh = sht30.read()
            # ---> Ajusta posición del texto <---
            text_x = logo_center_x + logo_radius + 30 # Posición X a la derecha del logo
            text_y_label = 85 # Posición Y del texto "Humedad:"
            text_y_value = text_y_label + 20 # Posición Y del valor
            
            # Borra área de texto anterior
            display.fill_rectangle(text_x - 5, text_y_label - 2, 100, 40, BLACK) 
            
            display.draw_text8x8(text_x, text_y_label, "Humedad:", BLUE, BLACK)
            display.draw_text8x8(text_x, text_y_value, f"{rh:.1f} %", BLUE, BLACK) 
        except Exception as e:
            display.fill_rectangle(text_x - 5, text_y_label - 2, 100, 40, BLACK) 
            display.draw_text8x8(text_x, text_y_label, f"Err SHT30:", RED, BLACK) 
            display.draw_text8x8(text_x, text_y_value, f"{e}", RED, BLACK)

        # 2. Comprobar toque en VOLVER
        pos = touch.get_touch()
        if pos:
            x, y = pos; x, y = y, x # Tu transformación de coordenadas
            # Coordenadas del botón volver: (35, 80, 3, 15)
            if 35 <= x <= 80 and 3 <= y <= 15: 
                return # Salir de la función

        # 3. Pausa
        time.sleep(0.5)

def pantalla_luz():
    display.clear(BLACK)
    boton_volver() # Dibuja el botón VOLVER una vez
    
    logo_center_x = 70   # X position for the logo center
    logo_center_y = 95   # Y position for the logo center
    logo_radius = 30     # Overall radius (including rays)
    draw_sun_logo(logo_center_x, logo_center_y, logo_radius)
    
    while True: # Bucle de actualización
        check_automation()
        # 1. Leer sensor y mostrar
        try:
            lux = bh1750.read_lux()
            # ---> Adjust text position <---
            text_x = logo_center_x + logo_radius + 30 # X position to the right of the logo
            text_y_label = 85 # Y position for "Luz (lux):"
            text_y_value = text_y_label + 20 # Y position for the value
            
            # Clear previous text area
            display.fill_rectangle(text_x - 5, text_y_label - 2, 100, 40, BLACK) 
            
            display.draw_text8x8(text_x, text_y_label, "Luz (lux):", GREEN, BLACK)
            display.draw_text8x8(text_x, text_y_value, f"{lux:.0f} lx", GREEN, BLACK) 
        except Exception as e:
            # Clear text area and show error
            display.fill_rectangle(text_x - 5, text_y_label - 2, 100, 40, BLACK) 
            display.draw_text8x8(text_x, text_y_label, f"Err BH1750:", RED, BLACK) 
            display.draw_text8x8(text_x, text_y_value, f"{e}", RED, BLACK) # Borra errores previos

        # 2. Comprobar toque en VOLVER
        pos = touch.get_touch()
        if pos:
            x, y = pos; x, y = y, x # Tu transformación de coordenadas
            # Coordenadas del botón volver: (35, 80, 3, 15)
            if 35 <= x <= 80 and 3 <= y <= 15: 
                return # Salir de la función

        # 3. Pausa
        time.sleep(0.5)
    
# ---> CAMBIO: Funciones de mapeo individuales para cada sensor <---
def map_sensor(raw, dry=58000, wet=55000): # Calibración unificada
    if raw > dry: raw = dry
    if raw < wet: raw = wet
    if dry == wet: return 0
    pct = 100 * (dry - raw) / (dry - wet)
    return int(pct)

# ---> CAMBIO: Lógica de pantalla_suelo() actualizada <---
def pantalla_suelo():
    display.clear(BLACK)
    display.draw_text8x8(90, 20, "HUMEDAD DE SUELO", YELLOW, BLACK)

    logo_width = 10
    logo_height = 25
    logo_x = 15 # X position for all logos
    label_x = logo_x + logo_width + 8 # X position for text labels (Sensor Suelo X:)
    # Dibuja las etiquetas estáticas una sola vez
    y1 = 65
    y2 = y1 + 28 # Adjust spacing as needed
    y3 = y2 + 28 # Adjust spacing as needed
    
    # --- Draw logos ---
    draw_soil_logo(logo_x, y1, logo_width, logo_height)
    draw_soil_logo(logo_x, y2, logo_width, logo_height)
    draw_soil_logo(logo_x, y3, logo_width, logo_height)
    
    # --- Draw static text labels ---
    display.draw_text8x8(label_x, y1 + 8, "Sensor Suelo 1:", CYAN, BLACK) # Pin 4
    display.draw_text8x8(label_x, y2 + 8, "Sensor Suelo 2:", CYAN, BLACK) # Pin 5
    display.draw_text8x8(label_x, y3 + 8, "Sensor Suelo 3:", CYAN, BLACK) # Pin 6
    
    boton_volver()
    
    while True:
        check_automation()
        # Sensor 1 (Pin 4)...
        value_x = display.width - 50 

        # Sensor 1
        raw1 = soil_adcs[0].read_u16(); val1 = 0 if raw1 > UMBRAL_DESCONECTADO else map_sensor(raw1)
        display.fill_rectangle(value_x, y1 + 8, 40, 8, BLACK) # Clear previous value
        display.draw_text8x8(value_x, y1 + 8, f"{val1}%", CYAN, BLACK); time.sleep_ms(10)
        
        # Sensor 2
        raw2 = soil_adcs[1].read_u16(); val2 = 0 if raw2 > UMBRAL_DESCONECTADO else map_sensor(raw2)
        display.fill_rectangle(value_x, y2 + 8, 40, 8, BLACK) # Clear previous value
        display.draw_text8x8(value_x, y2 + 8, f"{val2}%", CYAN, BLACK); time.sleep_ms(10)
        
        # Sensor 3
        raw3 = soil_adcs[2].read_u16(); val3 = 0 if raw3 > UMBRAL_DESCONECTADO else map_sensor(raw3)
        display.fill_rectangle(value_x, y3 + 8, 40, 8, BLACK) # Clear previous value
        display.draw_text8x8(value_x, y3 + 8, f"{val3}%", CYAN, BLACK)
        
        print(f"Valores Crudos ADC: Pin 4={raw1}  Pin 5={raw2}  Pin 6={raw3}")
        
        # Comprueba si se ha tocado el botón "VOLVER"
        pos = touch.get_touch()
        if pos:
            x, y = pos; x, y = y, x
            if 35 <= x <= 80 and 3 <= y <= 15: return

        time.sleep(0.5)

def pantalla_toggle(nombre, pin_obj, color):
    display.clear(BLACK)
    
    # Define la lógica activo-bajo
    estado_real_on = 0 
    estado_real_off = 1
    
    check_automation()
    
    # Lee el estado actual REAL del pin
    estado_actual = pin_obj.value() 

    # Dibuja el nombre del actuador
    display.draw_text8x8(70, 70, f"{nombre}", color, BLACK)
    
    # ---> CORRECCIÓN AQUÍ <---
    # Muestra el estado inicial CORRECTAMENTE basado en el valor del pin
    if estado_actual == estado_real_on: # Si el pin está en BAJO (0), muestra ON
        display.draw_text8x8(70, 95, "Estado: ON  ", color, BLACK)
    else: # Si el pin está en ALTO (1), muestra OFF
        display.draw_text8x8(70, 95, "Estado: OFF ", color, BLACK)
        
    # Botones ON / OFF
    display.fill_rectangle(50, 140, 80, 30, GREEN)
    display.draw_text8x8(75, 150, "ON", BLACK, GREEN)
    display.fill_rectangle(190, 140, 80, 30, RED)
    display.draw_text8x8(210, 150, "OFF", WHITE, RED)
    boton_volver()
    
    botones_toogle = {
        "on": (69, 97, 48, 50),
        "off": (34, 68, 47, 50),
        "volver": (35, 80, 3, 15)
    }
    
    accion = manejar_interaccion(botones_toogle)
    if accion == "on":
        pin_obj.value(0)
        estado = 0
        display.draw_text8x8(70, 95, "Estado: ON  ", color, BLACK)
        check_automation()
        time.sleep(0.5)
    elif accion == "off":
        pin_obj.value(1)
        estado = 1
        display.draw_text8x8(70, 95, "Estado: OFF ", color, BLACK)
        check_automation()
        time.sleep(0.5)
    elif accion == "volver":
        return

# ---> NUEVA FUNCIÓN PARA LA LÓGICA AUTOMÁTICA <---
def check_automation():
    global ultimo_riego_fin, ultimo_ferti_inicio, riego_activo, riego_inicio_tiempo, ferti_activo, ferti_inicio_tiempo

    ahora = time.ticks_ms() # Obtiene el tiempo actual en milisegundos

    # 1. RIEGO (Basado en Sensor 2 - Pin 5)
    try:
        raw_humedad_s2 = soil_adcs[1].read_u16()
        if raw_humedad_s2 > UMBRAL_DESCONECTADO:
            humedad_s2 = 0 
        else:
            humedad_s2 = map_sensor(raw_humedad_s2)

        # Comprobar si hay que activar el riego
        if not riego_activo and humedad_s2 <= HUMEDAD_MINIMA_RIEGO:
            if time.ticks_diff(ahora, ultimo_riego_fin) > RIEGO_INTERVALO * 1000:
                print("AUTO: Activando RIEGO")
                riego.value(0) 
                riego_activo = True
                riego_inicio_tiempo = ahora
                draw_status_bar() # Actualiza icono en barra superior

        # Comprobar si hay que desactivar el riego
        if riego_activo and time.ticks_diff(ahora, riego_inicio_tiempo) >= RIEGO_DURACION * 1000:
            print("AUTO: Desactivando RIEGO")
            riego.value(1) 
            riego_activo = False
            ultimo_riego_fin = ahora 
            draw_status_bar() 

    except Exception as e:
        print(f"Error en lógica de riego: {e}")

    # 3. VENTILADOR (Basado en temperatura)
    try:
        # Solo lee temp si no estamos ya en la pantalla de temperatura
        # (para evitar lecturas duplicadas rápidas)
        # Esto es opcional, pero puede ser bueno.
        # Necesitaríamos una variable global para saber en qué pantalla estamos.
        # Por simplicidad, lo dejamos leer siempre por ahora.
        temp_actual, _ = sht30.read()

        if temp_actual > TEMP_UMBRAL_FAN:
            if fan.value() == 1: 
                print("AUTO: Activando VENTILADOR (Temp alta)")
                fan.value(0) 
                draw_status_bar()
        else:
            if fan.value() == 0: 
                print("AUTO: Desactivando VENTILADOR (Temp normal)")
                fan.value(1) 
                draw_status_bar()
    except Exception as e:
        print(f"Error en lógica de ventilador: {e}")


# ================== LOOP PRINCIPAL ==================
# (Sin cambios)
def main():
    pantalla_bienvenida()
    draw_menu()
    
    while True:
        check_automation() 

        # --- COMPROBACIÓN DE TOQUE EN LA PANTALLA --- 
        pos = touch.get_touch()
        if pos:
            x, y = pos; x, y = y, x # Tu transformación
            print(f"Toque detectado en: X={x}, Y={y}")
            sel = detectar_boton(x, y) # Comprueba si toca un botón del menú

            # Navega a la pantalla correspondiente si se tocó un botón
            if sel == "TEMP":       pantalla_temp()
            elif sel == "HUMEDAD":  pantalla_humedad()
            elif sel == "LUZ":      pantalla_luz()
            elif sel == "SUELO":    pantalla_suelo()
            elif sel == "RIEGO":    pantalla_toggle("RIEGO", riego, MAGENTA)
            elif sel == "FERTIRRIEGO": pantalla_toggle("FERTIRRIEGO", ferti, YELLOW)
            elif sel == "VENTILADOR":  pantalla_toggle("VENTILADOR", fan, WHITE)

            # Si se entró a alguna pantalla (sel no es None), redibuja el menú al salir
            if sel:
                draw_menu()
                draw_status_bar() 

        # Pequeña pausa para no saturar el CPU y permitir otras tareas
        time.sleep_ms(100) # Revisa sensores y toque 10 veces por segundo

# (Funciones de calibración y barra de estado sin cambios)
def pantalla_calibracion():
    """Calibración táctil: 4 toques (sup izq, sup der, inf izq, inf der)"""
    pts = []
    corners = [(20,20,"Toca esquina SUP IZQ"),(300,20,"Toca esquina SUP DER"),(20,220,"Toca esquina INF IZQ"),(300,220,"Toca esquina INF DER")]
    display.clear(BLACK)
    display.draw_text8x8(40, 20, "CALIBRACION TACTIL", YELLOW, BLACK)
    logo_center_x = display.width // 2
    logo_center_y = display.height // 2 + 10 # Un poco más abajo del centro
    logo_radius = 30 # Tamaño del logo
    logo_line_length = logo_radius * 2 + 10 # Largo de las líneas cruzadas
    draw_crosshair_logo(logo_center_x, logo_center_y, logo_radius, logo_line_length)
    for (xd, yd, msg) in corners:
        display.fill_circle(xd, yd, 5, RED)
        display.draw_text8x8(20, 40, msg, WHITE, BLACK)
        while True:
            pos = touch.raw_touch()
            if pos:
                rx, ry = pos
                pts.append((rx, ry))
                time.sleep(1)
                break
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    touch.x_min, touch.x_max = min(xs), max(xs)
    touch.y_min, touch.y_max = min(ys), max(ys)
    try:
        touch.set_range(touch.x_min, touch.x_max, touch.y_min, touch.y_max)
    except:
        pass
    display.clear(BLACK)
    display.draw_text8x8(40, 100, "Calibracion guardada", GREEN, BLACK)
    time.sleep(1)

# ---> NUEVA FUNCIÓN: Dibuja un icono de estado ON/OFF <---
def draw_actuator_status_icon(pin_obj, x, y):
    """ Dibuja un círculo de estado (verde=ON, blanco=OFF) en x, y """
    # Lógica activo-bajo: 0 = ON, 1 = OFF
    if pin_obj.value() == 0: 
        display.fill_circle(x, y, 5, GREEN) # ON = Verde
    else:
        display.fill_circle(x, y, 5, BLACK) # Relleno negro para OFF
        display.draw_circle(x, y, 5, WHITE) # Borde blanco para OFF

# ---> FUNCIÓN MODIFICADA: Barra de estado con iconos al lado <---
def draw_status_bar():
    """Dibuja iconos de estado en la parte superior: Fan, Riego, Ferti"""
    display.fill_rectangle(0,0,320,12,BLACK) # Limpia la barra
    
    # FAN
    display.draw_text8x8(190, 2,"FAN", WHITE, BLACK)
    draw_actuator_status_icon(fan, 225, 6) # Dibuja icono al lado

    # RIEGO
    display.draw_text8x8(240, 2,"RIE", WHITE, BLACK)
    draw_actuator_status_icon(riego, 275, 6) # Dibuja icono al lado

    # FERTIRRIEGO
    display.draw_text8x8(290, 2,"FER", WHITE, BLACK)
    draw_actuator_status_icon(ferti, 320-10, 6) # Dibuja icono al lado

# actualizar draw_menu para mostrar barra de estado
_old_draw_menu = draw_menu

def draw_menu_with_status():
    _old_draw_menu()
    draw_status_bar()

# sustituir en runtime
draw_menu = draw_menu_with_status

# Ejecuta calibración al inicio si el usuario lo desea
pantalla_bienvenida()
should_calibrate = pantalla_bienvenida() 

# Ejecuta calibración SOLO si hubo toque durante bienvenida
if should_calibrate:
    pantalla_calibracion()

# iniciar loop principal
main()