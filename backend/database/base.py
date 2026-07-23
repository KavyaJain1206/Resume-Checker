"""
database/base.py
Declarative base every ORM model inherits from. Alembic's env.py imports
`Base.metadata` (via models/__init__.py, which registers every model on
this base) as the source of truth for autogenerate.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
