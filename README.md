# bookstore-backend

Django REST Framework backend for the Enterprise Book Store platform.

## Tech Stack

- **Django 4.2** — web framework
- **Django REST Framework 3.15** — API layer
- **PostgreSQL** (AWS RDS) — production database
- **Gunicorn** — production WSGI server
- **WhiteNoise** — static file serving
- **Render** — hosting platform

## Local Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure environment file
cp .env.example .env
# Fill in SECRET_KEY and DATABASE_URL

# 4. Run migrations
python manage.py migrate

# 5. Create a superuser (optional)
python manage.py createsuperuser

# 6. Start the development server
python manage.py runserver
```

## Environment Variables

| Variable               | Description                              |
|------------------------|------------------------------------------|
| `SECRET_KEY`           | Django secret key                        |
| `DEBUG`                | `True` for development, `False` for prod |
| `DATABASE_URL`         | PostgreSQL connection string (AWS RDS)   |
| `ALLOWED_HOSTS`        | Comma-separated list of allowed hosts    |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed origins  |
| `ANALYTICS_SERVICE_URL`| FastAPI microservice base URL            |

## Running Tests

```bash
python manage.py test apps/
```

## Deployment Target

**Render** — configuration in `render.yaml`.
Health probe endpoint: `GET /health/` → `{"status": "ok"}`

## App Structure

```
apps/
├── core/          Base models, health endpoint
├── users/         User, UserProfile, UserAddress
├── authors/       Author profiles
├── categories/    Book categories (tree structure)
├── books/         Book catalogue
├── inventory/     Stock management
├── cart/          Shopping cart
├── wishlist/      User wishlists
├── orders/        Order lifecycle
├── payments/      Payment records
├── coupons/       Discount coupons
├── reviews/       Book reviews & ratings
├── notifications/ In-app notifications
└── analytics/     Page view stubs (delegates to FastAPI)
```

## Phase 0 Status

Foundation skeleton only. User model + health endpoint are functional.
All other endpoints return valid structure but contain no business logic.
No authentication endpoints exist in this phase.
