# AER-1 Java

JDK 17+ only; no external runtime dependencies. The project includes a small JSON parser so it does not depend on Jackson/Gson.

No-network path (direct JDK, no Maven downloads needed):
```sh
javac -d target/classes src/main/java/dev/aer1/AER1.java
java -cp target/classes dev.aer1.AER1    # conformance, 45/45
```

Maven path:
```sh
mvn -q compile exec:java                 # conformance, 45/45
mvn -q compile exec:java -Dexec.args=emit # emitter
```

`AER1.java` includes core verification, strict timestamp/base64/UTF-8 checks, profile and anchor checks, the Section 8.1 Merkle construction, and the emitter.

---
AER-1 is created by Brennan Zambo. Learn more at https://zambo.dev.
