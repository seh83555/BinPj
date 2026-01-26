#include <ESP32Servo.h>
#include <ESP32PWM.h>
#include <WebSocketsClient_Generic.h>
#include <WiFiManager.h>

// Credentials
#define WS_SERVER "WEBHOOK_URL"
#define WS_PORT 443 // OR 5000 IF IT'S LOCAL
#define WS_PATH "/websocket"
#define Password "SET_YOUR_ADMIN_PASSWORD" // THIS PASSWORD IS USE WHEN YOU CONNECT TO ESP32 WIFI TO TELL IT WHICH WIFI ESP32 NEED TO CONNECT BY ENTER TO THE ESP32'S WEBSITE IP ADDRESS 192.168.4.1

// Define variables
Servo Red, Yellow, Green, Blue;
WebSocketsClient webSocket;

bool alreadyConnected = false;
const int RESET_PIN = 0;


// WebsocketEventHandle
void webSocketEvent(const WStype_t& type, uint8_t * payload, const size_t& length){

  switch (type){
    
    case WStype_DISCONNECTED:
    if (alreadyConnected) {

      Serial.println("[WSc] Disconnected!");
      alreadyConnected = false;
    }
    break;

    case WStype_CONNECTED:
    {
      alreadyConnected = true;

      Serial.print("[WSc] Connected to url: ");
      Serial.println((char *) payload);
    }
    break;

    case WStype_TEXT:
    {
    Serial.printf("[WSc] Get text: %s\n", payload);

    int binNumber = atoi((char *)payload);
    if (binNumber >= 1 && binNumber <= 4) {
      moveServo(binNumber);
      }
    }
    break;

    case WStype_ERROR:
    case WStype_FRAGMENT_TEXT_START:
    case WStype_FRAGMENT_BIN_START:
    case WStype_FRAGMENT:
    case WStype_FRAGMENT_FIN:
    break;

    default:
    break;
    
  }
}

void setup() {

  Serial.begin(115200);

  pinMode(RESET_PIN, INPUT_PULLUP);

  // Connecting to wifi
  WiFiManager wm;
  wm.setConnectTimeout(15);
  wm.setConfigPortalTimeout(180);
  bool res;
  res = wm.autoConnect("AutoConnectAP", AdminPassword);
  if(!res) {
    Serial.println("Failed to connect");
    ESP.restart();
    }
  else {
    Serial.println("\nWifi Connected");
    }

  // Connect to WebSocket
  webSocket.beginSSL(WS_SERVER, WS_PORT, WS_PATH);

  // Event handler
  webSocket.onEvent(webSocketEvent);

  // try ever 1000 again if connection has failed
  webSocket.setReconnectInterval(1000);

  Serial.print("Connected to WebSockets Server @ IP address: ");
  Serial.println(WS_SERVER);

  // Prepare servo
  ESP32PWM::allocateTimer(0), ESP32PWM::allocateTimer(1), ESP32PWM::allocateTimer(2), ESP32PWM::allocateTimer(3);
  Red.attach(27, 500, 2400), Yellow.attach(26, 500, 2400), Green.attach(25, 500, 2400), Blue.attach(33, 500, 2400);
  Red.write(0), Yellow.write(0), Green.write(0), Blue.write(0);

}

void loop() {

  webSocket.loop();

  if (digitalRead(RESET_PIN) == LOW){
    int count = 0;

    // Counting 5 sec
    while (digitalRead(RESET_PIN) == LOW && count < 50){
      delay(100);
      count++;
      if (count % 10 == 0) Serial.print(5 - (count/10));
    }
    
    if (count >= 50){
      Serial.println("\nResetting WiFi & Restarting...");
      WiFiManager wm;
      wm.resetSettings();
      delay(1000);
      ESP.restart();
    }

  }

}

// Get input and move servo
void moveServo(int number) {

  Servo* s = nullptr;
  switch (number) {
      case 1: s = &Red;    break;
      case 2: s = &Yellow; break;
      case 3: s = &Green;  break;
      case 4: s = &Blue;   break;
      default: 
        Serial.println("Invalid number");
        return;
    }

  Serial.println("Moving to 90 degrees");
  s->write(90);

  delay(500);

  Serial.println("Moving back to 0 degrees");
  s->write(0);

}
