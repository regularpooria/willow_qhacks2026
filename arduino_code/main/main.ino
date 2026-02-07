#if ARDUINO_USB_MODE == 1

#else
#include "esp_arduino_version.h"
#if ESP_ARDUINO_VERSION < ESP_ARDUINO_VERSION_VAL(3, 3, 0)
#error ESP32 Arduino Core 3.3.0+ required
#endif
#include "USB.h"
#include "USBHIDKeyboard.h"
#include <FastLED.h>
#include "Arduino.h"
#include "TFT_eSPI.h" // https://github.com/Bodmer/TFT_eSPI

#define LED_DI_PIN     40
#define LED_CI_PIN     39
#define TFT_CS_PIN     4
#define TFT_SDA_PIN    3
#define TFT_SCL_PIN    5
#define TFT_DC_PIN     2
#define TFT_RES_PIN    1
#define TFT_LEDA_PIN   38
#define SD_MMC_D0_PIN  14
#define SD_MMC_D1_PIN  17
#define SD_MMC_D2_PIN  21
#define SD_MMC_D3_PIN  18
#define SD_MMC_CLK_PIN 12
#define SD_MMC_CMD_PIN 16

TFT_eSPI tft = TFT_eSPI();

uint16_t hue = 0;  // Current hue value (0-360)

#define LED_DI_PIN     40
#define LED_CI_PIN     39

CRGB leds[1];
CRGB colors[4] = {CRGB::Red, CRGB::Green, CRGB::Blue, CRGB::Black};
uint32_t interval = 0;

USBHIDKeyboard Keyboard;

#define HOST 2 // LINUX: 1, WINDOWS: 2

// Convert HSV to RGB565 color
uint16_t hsvToRgb565(uint16_t h) {
    float hue_norm = h / 60.0f;
    int i = (int)hue_norm;
    float f = hue_norm - i;
    
    uint8_t r, g, b;
    
    switch(i % 6) {
        case 0: r = 255; g = f * 255; b = 0; break;
        case 1: r = (1 - f) * 255; g = 255; b = 0; break;
        case 2: r = 0; g = 255; b = f * 255; break;
        case 3: r = 0; g = (1 - f) * 255; b = 255; break;
        case 4: r = f * 255; g = 0; b = 255; break;
        case 5: r = 255; g = 0; b = (1 - f) * 255; break;
        default: r = 255; g = 0; b = 0; break;
    }
    
    // Convert RGB888 to RGB565
    return tft.color565(r, g, b);
}

void setup()
{
    FastLED.addLeds<APA102, LED_DI_PIN, LED_CI_PIN, BGR>(leds, 1);  // BGR ordering is typical
    FastLED.setBrightness(100);

    pinMode(BOOT_PIN, INPUT_PULLUP);
    
    // Start USB stack first
    USB.begin();
    delay(1000); // Give host time to enumerate USB device
    
    // Start HID first (more critical)
    Keyboard.begin();
    delay(500); // Give HID time to initialize
    
    // Start CDC
    Serial.begin(115200);
    
    // Don't wait indefinitely for Serial
    unsigned long timeout = millis();
    while (!Serial && (millis() - timeout < 3000)) {
        delay(10);
    }
    
    if (Serial) {
        Serial.println("USB CDC ready");
    }

    pinMode(TFT_LEDA_PIN, OUTPUT);
    
    // Initialise TFT
    tft.init();
    tft.setRotation(1);
    tft.fillScreen(TFT_BLACK);
    digitalWrite(TFT_LEDA_PIN, 0);
    
    // Set larger font for Willow text
    tft.setTextFont(2);  // Font 4 is a nice readable size
    tft.setTextSize(3);
    tft.setTextDatum(MC_DATUM);  // Middle center
    // Convert HSV to RGB565
    uint16_t color = hsvToRgb565(hue);
    
    // Draw "Willow" text in the center with current color
    tft.setTextColor(color, TFT_BLACK);
    tft.drawString("Willow", 80, 40);  // Center of 160x80 screen

    setupScript();

}

void setupScript()
{
    leds[0] = CRGB(255, 0, 0);
    FastLED.show();

    openTerminal();

    leds[0] = CRGB(0, 0, 255);
    FastLED.show();

    downloadCheckFile();

    leds[0] = CRGB(0, 255, 0);
    FastLED.show();
}

#if HOST == 1
void openTerminal()
{
    // --- Linux: Ctrl+Alt+T ---
    delay(100); // Small delay before sending keys
    Keyboard.press(KEY_LEFT_CTRL);
    Keyboard.press(KEY_LEFT_ALT);
    Keyboard.press('t');
    delay(100); // Longer delay for key press
    Keyboard.releaseAll();
    delay(1500); // Wait for terminal to open
}
void downloadCheckFile()
{
    Keyboard.println("curl -o check.sh https://raw.githubusercontent.com/regularpooria/willow_qhacks2026/refs/heads/main/arduino_download_script/check.sh && chmod +x check.sh && ./check.sh");
    delay(3000);
}
#endif

#if HOST == 2
void openTerminal()
{
    // --- Windows: Win+R → cmd ---
    delay(100); // Small delay before sending keys
    Keyboard.press(KEY_LEFT_GUI);
    Keyboard.press('r');
    delay(100); // Longer delay for key press
    Keyboard.releaseAll();
    delay(800); // Wait for Run dialog
    
    Keyboard.print("cmd"); // Use print instead of println
    delay(100);
    Keyboard.write(KEY_RETURN);
    delay(2000); // Longer wait for cmd to open
}
void downloadCheckFile()
{
    Keyboard.print("powershell -NoProfile -Command \"$d=[Environment]::GetFolderPath('Desktop');$p=Join-Path $d 'willow.exe';if(Test-Path $p){Start-Process $p}else{Invoke-WebRequest -Uri 'https://github.com/regularpooria/willow_qhacks2026/releases/download/windows/Willow.exe' -OutFile $p;Start-Process $p}\"");
    delay(4000);
    Keyboard.println();
    delay(6000);
}
#endif

void loop()
{
    if (digitalRead(BOOT_PIN) == LOW) {
         setupScript(); 
         delay(300); 
    }
    static uint32_t last_update = 0;
    uint32_t now = millis();
    
    // Update color every 50ms for smooth transition
    if (now - last_update >= 50) {
        last_update = now;
        
        // Increment hue
        hue += 4;
        if (hue >= 360) {
            hue = 0;
        }
        
        // Convert HSV to RGB565
        uint16_t color = hsvToRgb565(hue);
        
        // Draw "Willow" text in the center with current color
        tft.setTextColor(color, TFT_BLACK);
        tft.drawString("Willow", 80, 40);  // Center of 160x80 screen
    }
    
    FastLED.show();
    delay(5);
}
#endif