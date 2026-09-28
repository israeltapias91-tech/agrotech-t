# AGROTECH — Docs

- Decisiones 6–47: diseño conceptual cerrado (Usuario + Finca + Rol + Permisos).
- Modelo: USER (UUID, email login, account_status ACTIVE/SUSPENDED/DEACTIVATED + email_verified) → MEMBERSHIP (INVITED/ACTIVE/SUSPENDED/REVOKED, UNIQUE user+farm) → FARM (TRIAL/ACTIVE/SUSPENDED/CLOSED, owner_id) → ROLE (ADMINISTRADOR/OPERADOR/CONSULTA) → PERMISSION (módulo+acción).
- Pendientes NO inventados: precio mensual/anual, pasarela pago, duración periodo gracia, antifraude pruebas, matriz exacta permisos, retención cuentas, facturación, offline.

FASE 3 no bloquea por pendientes: `GRACE_PERIOD_DAYS` queda configurable vía env.
