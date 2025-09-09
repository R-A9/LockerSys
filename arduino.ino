// === Pin assignments ===
const int RELAYONE   = 2;
const int RELAYTWO   = 3;
const int RELAYTHREE = 4;  // Inverted logic

String inputCommand = "";

// Lock states and timers
unsigned long lock1OpenTime = 0;
unsigned long lock2OpenTime = 0;
unsigned long lock3OpenTime = 0;

bool lock1Open = false;
bool lock2Open = false;
bool lock3Open = false;

const unsigned long OPEN_DURATION = 3000; // auto-close after 3 seconds

void setup() {
  pinMode(RELAYONE, OUTPUT);
  pinMode(RELAYTWO, OUTPUT);
  pinMode(RELAYTHREE, OUTPUT);

  // Ensure all locks closed at boot
  digitalWrite(RELAYONE, HIGH);   // closed (active LOW)
  digitalWrite(RELAYTWO, HIGH);   // closed (active LOW)
  digitalWrite(RELAYTHREE, LOW);  // closed (active HIGH, inverted)

  Serial.begin(9600);
}

void loop() {
  // --- Handle serial input ---
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      processCommand(inputCommand);
      inputCommand = "";
    } else {
      inputCommand += c;
    }
  }

  // --- Auto-close logic ---
  unsigned long now = millis();

  if (lock1Open && (now - lock1OpenTime >= OPEN_DURATION)) {
    digitalWrite(RELAYONE, HIGH);
    lock1Open = false;
    Serial.println("Lock 1 auto-closed");
  }

  if (lock2Open && (now - lock2OpenTime >= OPEN_DURATION)) {
    digitalWrite(RELAYTWO, HIGH);
    lock2Open = false;
    Serial.println("Lock 2 auto-closed");
  }

  if (lock3Open && (now - lock3OpenTime >= OPEN_DURATION)) {
    digitalWrite(RELAYTHREE, LOW);   // inverted close
    lock3Open = false;
    Serial.println("Lock 3 auto-closed");
  }
}

void processCommand(String cmd) {
  cmd.trim();

  if (cmd == "L1") {
    if (!lock1Open) {
      digitalWrite(RELAYONE, LOW);
      Serial.println("Lock 1 opened");
    } else {
      Serial.println("Lock 1 already open, refreshing timer");
    }
    lock1Open = true;
    lock1OpenTime = millis();
  }
  else if (cmd == "L2") {
    if (!lock2Open) {
      digitalWrite(RELAYTWO, LOW);
      Serial.println("Lock 2 opened");
    } else {
      Serial.println("Lock 2 already open, refreshing timer");
    }
    lock2Open = true;
    lock2OpenTime = millis();
  }
  else if (cmd == "L3") {
    if (!lock3Open) {
      digitalWrite(RELAYTHREE, HIGH);  // inverted open
      Serial.println("Lock 3 opened");
    } else {
      Serial.println("Lock 3 already open, refreshing timer");
    }
    lock3Open = true;
    lock3OpenTime = millis();
  }
  else if (cmd == "ALL") {
    // Open all (account for inverted relay3)
    digitalWrite(RELAYONE, LOW);
    digitalWrite(RELAYTWO, LOW);
    digitalWrite(RELAYTHREE, HIGH);
    Serial.println("All locks opened");

    unsigned long now = millis();
    lock1Open = lock2Open = lock3Open = true;
    lock1OpenTime = now;
    lock2OpenTime = now;
    lock3OpenTime = now;
  }
  else {
    Serial.println("Invalid command: " + cmd);
  }
}
