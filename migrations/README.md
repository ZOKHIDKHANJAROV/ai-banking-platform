Run migrations from the repository root.

Example:

```bash
set DATABASE_URL=postgresql+asyncpg://admin:admin@localhost:5432/banking
py -3 -m alembic upgrade head
```
