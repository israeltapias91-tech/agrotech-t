# AGROTECH — SaaS Multi-Finca

Fase actual: **FASE 3 — Preparar Backend** (Windows dev).

Stack: Python 3.13 + Django 5.2 + DRF + MariaDB 11.8.

## Estructura monorepo

```text
AGROTECH-T/
├── backend/   # Django + DRF (config/, apps futuras: accounts, farms...)
├── frontend/  # React (placeholder FASE 3)
└── docs/      # decisiones 6-47, SRS, modelo conceptual
```

## Regla crítica

> El modelo personalizado `User` (FASE 4) debe definirse ANTES de la primera migración.

Por eso en FASE 3 NO se corre `migrate`.

## Dev rápido

```powershell
# venv Python 3.13
python3.13 -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt

# Django
python backend\manage.py check
```

DB: MariaDB 11.8 en `127.0.0.1:3307` (3306 ocupado por MySQL80 local).
Ver `backend/.env.example` y `docs/`.
