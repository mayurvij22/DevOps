# Small runtime image: JRE only, no build tools.
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY target/demo-app.jar app.jar
# Run as non-root (DevSecOps best practice)
RUN useradd -r appuser
USER appuser
ENTRYPOINT ["java", "-jar", "app.jar"]
