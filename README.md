🌱 Sistema de Control de Invernadero Automatizado (ESP32-S3)

Este proyecto implementa un sistema de gestión y monitoreo para invernaderos utilizando MicroPython en un microcontrolador ESP32-S3. Cuenta con una interfaz gráfica táctil (UI) robusta, lectura de múltiples sensores ambientales y automatización de actuadores (riego, ventilación y fertirriego).

📋 Características Principales

Interfaz Táctil: Menú interactivo sobre pantalla ILI9341 (320x240) con controlador táctil XPT2046.

Gráficos Vectoriales: Logos e iconos dibujados en tiempo real (sin necesidad de cargar imágenes pesadas).

Monitoreo Ambiental:

🌡️ Temperatura y Humedad Relativa (SHT30).

☀️ Luminosidad en Lux (BH1750).

💧 Humedad del suelo (3 canales ADC independientes).

Automatización Inteligente:

Ventilación: Activación automática basada en umbral de temperatura (>36°C).

Riego: Activación automática basada en humedad del suelo (Sensor 2) con control de duración e intervalos de espera.

Control Manual: Capacidad de anular la automatización y activar actuadores manualmente desde la pantalla táctil.

Barra de Estado: Indicadores visuales (ON/OFF) en la parte superior de la interfaz para Ventilador, Riego y Fertirriego.

🛠️ Hardware Requerido

Componente

Descripción

Protocolo

MCU

ESP32-S3

-

Pantalla

TFT ILI9341 2.4" o 2.8"

SPI

Touch

XPT2046

SPI

Sensor Temp/Hum

SHT30 (o SHT31)

I2C

Sensor Luz

BH1750

I2C

Sensores Suelo

Capacitivos (x3)

Analógico (ADC)

Actuadores

Relés o MOSFETs

Digital GPIO

🔌 Diagrama de Conexiones (Pinout)

La configuración de pines está definida en el código principal para el ESP32-S3:

Pantalla & Touch (SPI)

Dispositivo

Pin ESP32

TFT MOSI

48

TFT MISO

41

TFT SCK

45

TFT CS

1

TFT DC

38

TFT RST

40

Touch MOSI

11

Touch MISO

13

Touch SCK

3

Touch CS

10

Sensores & Actuadores

Dispositivo

Pin ESP32

Notas

I2C SDA

15

SHT30 + BH1750

I2C SCL

16

SHT30 + BH1750

Suelo 1

4

ADC

Suelo 2

5

ADC (Controla Riego Auto)

Suelo 3

6

ADC

Riego

18

Salida Digital (Activo Bajo)

Fertirriego

8

Salida Digital (Activo Bajo)

Ventilador

9

Salida Digital (Activo Bajo)

Nota: Los actuadores están configurados con lógica inversa (Activo Bajo / Active Low). 0 enciende, 1 apaga.

⚙️ Configuración y Automatización

Las constantes de control se encuentran al inicio del script main.py. Puedes ajustarlas según tus necesidades:

# Configuración de Riego Automático
HUMEDAD_MINIMA_RIEGO = 0   # % para activar
RIEGO_DURACION = 5         # Segundos de riego
RIEGO_INTERVALO = 10       # Segundos de espera entre riegos

# Configuración de Ventilación
TEMP_UMBRAL_FAN = 36       # °C para encender ventilador


🚀 Instalación

Instala el firmware de MicroPython en tu ESP32-S3.

Sube los siguientes archivos a la raíz del dispositivo:

main.py (El código principal).

ili9341.py (Driver de pantalla).

xpt2046.py (Driver del panel táctil).

logo_data.py (Opcional: datos de imagen para logo de inicio).

Reinicia el dispositivo.

Calibración: En el primer arranque, toca la pantalla durante la bienvenida para entrar al modo de calibración de 4 puntos.

📂 Estructura del Proyecto

├── main.py          # Lógica principal, UI y control
├── ili9341.py       # Librería driver de pantalla
├── xpt2046.py       # Librería driver táctil
└── logo_data.py     # (Opcional) Array de bytes para el logo


🤝 Contribuciones

Si deseas mejorar los gráficos o añadir soporte para MQTT/WiFi, ¡siéntete libre de hacer un Fork y enviar un Pull Request!
