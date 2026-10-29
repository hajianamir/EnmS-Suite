# 11. APIs and Integrations (Complete OpenAPI Contract & RFC 9457)

## 11.1 API Conventions & Architecture
- **Error Format**: Strictly RFC 9457 Problem Details (`application/problem+json`).
- **Pagination**: Cursor-based (`limit`, `starting_after`, `has_more`).
- **Idempotency**: Supported via `Idempotency-Key` HTTP header on all POST/PUT/PATCH mutating endpoints.
- **Authentication**: Keycloak OIDC JWT with bearer tokens (`Authorization: Bearer <token>`). Tenant ID derived from JWT token claims (`tenant_id`).

---

## 11.2 UI Screen to API Operation Mapping Matrix

| Section 12 UI Screen | Functional Purpose | Mapped OpenAPI Endpoint | Method | Scope Required |
| :--- | :--- | :--- | :--- | :--- |
| **KPI Overview Bar** | High-level site/building energy & EnPI summary | `/api/v1/dashboards/kpi-summary` | `GET` | `telemetry:read` |
| **Main Chart Window** | Consumption vs Baseline CUSUM overlay | `/api/v1/enpi/cusum-trend` | `GET` | `enpi:read` |
| **Active Anomalies Widget** | Real-time tri-state anomaly alert list | `/api/v1/anomalies/active` | `GET` | `anomalies:read` |
| **Action Creation Modal** | Convert alert into tracked PDCA task | `/api/v1/actions` | `POST` | `actions:write` |
| **ISO Audit Pack Screen** | Export immutable evidence PDF package | `/api/v1/audit/export-pack` | `POST` | `audit:export` |

---

## 11.3 Executable OpenAPI 3.0 Specification (YAML)

```yaml
openapi: 3.0.3
info:
  title: VerdantOS Platform v1 API
  version: 1.0.0
  description: Comprehensive REST API for VerdantOS energy management platform.
servers:
  - url: https://api.verdantos.com/api/v1
    description: Production Cloud API Gateway
paths:
  /dashboards/kpi-summary:
    get:
      summary: Retrieve KPI summary for dashboard
      security:
        - OAuth2: [telemetry:read]
      parameters:
        - name: site_id
          in: query
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: KPI summary metrics.
          content:
            application/json:
              schema:
                type: object
                properties:
                  total_energy_kwh:
                    type: number
                  enpi_normalized_kwh_m2:
                    type: number
                  active_actions_count:
                    type: integer
        '400':
          $ref: '#/components/responses/ProblemDetails'

  /actions:
    post:
      summary: Create new PDCA Action Item
      security:
        - OAuth2: [actions:write]
      parameters:
        - name: Idempotency-Key
          in: header
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                asset_id:
                  type: string
                  format: uuid
                title:
                  type: string
                expected_annual_savings_kwh:
                  type: number
              required: [title, expected_annual_savings_kwh]
      responses:
        '201':
          description: Action item created successfully.
        '400':
          $ref: '#/components/responses/ProblemDetails'
        '409':
          $ref: '#/components/responses/ProblemDetails'

components:
  securitySchemes:
    OAuth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://auth.verdantos.com/realms/verdantos/protocol/openid-connect/auth
          tokenUrl: https://auth.verdantos.com/realms/verdantos/protocol/openid-connect/token
          scopes:
            telemetry:read: Read telemetry data
            actions:write: Create and edit action items
            audit:export: Export ISO audit evidence packs

  responses:
    ProblemDetails:
      description: RFC 9457 Standard Error Body
      content:
        application/problem+json:
          schema:
            type: object
            properties:
              type:
                type: string
                format: uri
              title:
                type: string
              status:
                type: integer
              detail:
                type: string
              instance:
                type: string
                format: uri
            required: [type, title, status, detail]
```
