from sqlalchemy.orm import Session, joinedload

from app.models.database_design import DatabaseDesign, DatabaseTable

SUPPORTED_DIALECTS = {"postgresql", "mysql", "sqlite", "sqlserver"}


def _quote(identifier: str, dialect: str) -> str:
    if dialect == "mysql":
        return f"`{identifier}`"
    if dialect == "sqlserver":
        return f"[{identifier}]"
    return f'"{identifier}"'


def _type(data_type: str, dialect: str) -> str:
    raw = data_type.upper().strip()
    if raw == "SERIAL":
        return "INTEGER IDENTITY(1,1)" if dialect == "sqlserver" else ("INTEGER AUTO_INCREMENT" if dialect == "mysql" else "INTEGER")
    if raw == "BOOLEAN" and dialect == "sqlserver":
        return "BIT"
    if raw == "TEXT" and dialect == "sqlserver":
        return "NVARCHAR(MAX)"
    return raw


def generate_sql(db: Session, design: DatabaseDesign, dialect: str | None = None) -> str:
    dialect = (dialect or design.target_dialect).lower()
    if dialect not in SUPPORTED_DIALECTS:
        raise ValueError(f"Unsupported SQL dialect: {dialect}")

    design = (
        db.query(DatabaseDesign)
        .options(joinedload(DatabaseDesign.tables).joinedload(DatabaseTable.columns), joinedload(DatabaseDesign.relationships))
        .filter(DatabaseDesign.id == design.id)
        .first()
    )
    table_names = {t.name.lower() for t in design.tables}
    lines = [f"-- SpecForge AI database export ({dialect})", f"-- Design: {design.name}", ""]

    for table in design.tables:
        parts = []
        primary = []
        uniques = []
        for column in sorted(table.columns, key=lambda c: c.position):
            line = f"    {_quote(column.name, dialect)} {_type(column.data_type, dialect)}"
            if column.primary_key:
                primary.append(column.name)
            if column.unique and not column.primary_key:
                uniques.append(column.name)
            if not column.nullable and not column.primary_key:
                line += " NOT NULL"
            if column.default_value is not None:
                line += f" DEFAULT {column.default_value}"
            parts.append(line)
        if primary:
            parts.append("    PRIMARY KEY (" + ", ".join(_quote(x, dialect) for x in primary) + ")")
        for unique in uniques:
            parts.append(f"    UNIQUE ({_quote(unique, dialect)})")
        lines.append(f"CREATE TABLE {_quote(table.name, dialect)} (\n" + ",\n".join(parts) + "\n);")
        lines.append("")

    for rel in design.relationships:
        if rel.from_table.lower() not in table_names or rel.to_table.lower() not in table_names:
            continue
        lines.append(
            f"ALTER TABLE {_quote(rel.from_table, dialect)} ADD CONSTRAINT "
            f"fk_{rel.from_table}_{rel.from_column}_{rel.to_table}_{rel.to_column} "
            f"FOREIGN KEY ({_quote(rel.from_column, dialect)}) REFERENCES "
            f"{_quote(rel.to_table, dialect)} ({_quote(rel.to_column, dialect)}) ON DELETE {rel.on_delete.upper()};"
        )
    return "\n".join(lines).rstrip() + "\n"
