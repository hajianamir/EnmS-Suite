# Phase 2 — Contract-First Development Policy

## 1. Mandatory Contract Rule
No implementation code may be merged into `main` without prior approval of its corresponding contract artifact:
1. **REST APIs**: OpenAPI 3.0 YAML spec (`contracts/openapi/`).
2. **Event Streams**: Kafka Schema Registry JSON/Protobuf schemas (`contracts/events/`).
3. **Database Entities**: Versioned DDL migration scripts (`db/migrations/`).
