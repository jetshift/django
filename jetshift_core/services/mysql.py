from jetshift_core.helpers.mysql import *
from jetshift_core.helpers.database import get_db_connection_url
from sqlalchemy import create_engine, text

from jetshift_core.services.database_map import map_mysql_to_clickhouse, map_mysql_to_postgres


def create_mysql_to_postgres_table(sub_task, selected_database, source_database):
    try:
        columns = fetch_mysql_schema(source_database, sub_task.source_table)
        pg_columns = []
        primary_key_column = None

        for col in columns:
            is_nullable = col['IS_NULLABLE'] == 'YES'
            data_type = col['DATA_TYPE']
            precision = int(col.get('NUMERIC_PRECISION') or 18)
            scale = int(col.get('NUMERIC_SCALE') or 4)

            # Map to PostgreSQL type
            pg_type = map_mysql_to_postgres(data_type, is_nullable=is_nullable, precision=precision, scale=scale)
            pg_columns.append(f'"{col["COLUMN_NAME"]}" {pg_type}')

            # Detect MySQL primary key
            if col.get('COLUMN_KEY') == 'PRI' and col['COLUMN_NAME'] == 'id':
                primary_key_column = 'id'

        if not pg_columns:
            return False, 'No columns found in the source table.'

        # Join column definitions
        columns_str = ",\n    ".join(pg_columns)

        # Add PRIMARY KEY clause if available
        if primary_key_column:
            columns_str += f",\n    PRIMARY KEY (\"{primary_key_column}\")"

        postgres_ddl = f"""
        CREATE TABLE IF NOT EXISTS "{sub_task.target_table}" (
            {columns_str}
        );
        """

        # Connect to PostgreSQL and execute
        target_database_url = get_db_connection_url(selected_database)  # should return PostgreSQL URL
        engine = create_engine(target_database_url, future=True)

        with engine.begin() as connection:  # ensures auto-commit
            connection.execute(text(postgres_ddl))

        return True, 'Successfully created PostgreSQL table.'
    except Exception as e:
        return False, f"Failed to create PostgreSQL table. Error: {str(e)}"


def create_mysql_to_clickhouse_table(sub_task, selected_database, source_database):
    try:
        columns = fetch_mysql_schema(source_database, sub_task.source_table)
        ch_columns = []
        primary_key_column = None

        for col in columns:
            is_nullable = col['IS_NULLABLE'] == 'YES'
            data_type = col['DATA_TYPE']
            # Use custom decimal precision if available
            precision = int(col.get('NUMERIC_PRECISION') or 18)
            scale = int(col.get('NUMERIC_SCALE') or 4)

            # Map to ClickHouse type
            ch_type = map_mysql_to_clickhouse(data_type, is_nullable=is_nullable, precision=precision, scale=scale)
            ch_columns.append(f"`{col['COLUMN_NAME']}` {ch_type}")

            # Detect MySQL primary key
            if col.get('COLUMN_KEY') == 'PRI' and col['COLUMN_NAME'] == 'id':
                primary_key_column = 'id'

        if not ch_columns:
            return False, 'No columns found in the source table.'

        # Join column definitions
        columns_str = ",\n    ".join(ch_columns)

        # ORDER BY clause
        order_by = primary_key_column if primary_key_column else 'tuple()'

        # Use version column for ReplacingMergeTree
        version_column = sub_task.config.get('version_column')

        if version_column:
            engine_clause = f"ReplacingMergeTree({version_column})"
        else:
            engine_clause = "ReplacingMergeTree()"

        clickhouse_ddl = f"""
        CREATE TABLE {sub_task.target_table} (
            {columns_str}
        ) ENGINE = {engine_clause}
        ORDER BY {order_by};
        """

        # Create table in ClickHouse
        target_database_url = get_db_connection_url(selected_database)
        engine = create_engine(target_database_url, future=True)

        with engine.begin() as connection:
            connection.execute(text(clickhouse_ddl))

        return True, 'Successfully created ClickHouse table.'
    except Exception as e:
        return False, f"Failed to create ClickHouse table. Error: {str(e)}"
