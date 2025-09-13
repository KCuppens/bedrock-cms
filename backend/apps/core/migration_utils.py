"""Utilities for database-conditional migrations."""

from django.db import connection, migrations


def conditional_sql_for_postgresql(sql, reverse_sql=None):
    """Create a RunSQL operation that only runs on PostgreSQL.

    Args:
        sql: SQL to run on PostgreSQL
        reverse_sql: SQL to run on reverse migration (optional)

    Returns:
        RunSQL operation that checks database vendor
    """

    def run_sql_if_postgresql(apps, schema_editor):
        if connection.vendor == "postgresql":
            with schema_editor.connection.cursor() as cursor:
                cursor.execute(sql)

    def reverse_sql_if_postgresql(apps, schema_editor):
        if reverse_sql and connection.vendor == "postgresql":
            with schema_editor.connection.cursor() as cursor:
                cursor.execute(reverse_sql)

    return migrations.RunPython(
        run_sql_if_postgresql,
        reverse_sql_if_postgresql if reverse_sql else None,
    )


def gin_index_operation(table_name, column_name, index_name, condition=None):
    """Create a GIN index operation that only runs on PostgreSQL.

    Args:
        table_name: Database table name
        column_name: JSON column to index
        index_name: Name of the index
        condition: Optional WHERE condition

    Returns:
        RunSQL operation for PostgreSQL GIN index
    """
    where_clause = f"WHERE {condition}" if condition else ""

    sql = f"""
    CREATE INDEX IF NOT EXISTS {index_name}
    ON {table_name} USING gin ({column_name} jsonb_path_ops)
    {where_clause};
    """

    reverse_sql = f"DROP INDEX IF EXISTS {index_name};"

    return conditional_sql_for_postgresql(sql.strip(), reverse_sql)
