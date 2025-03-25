from sqlalchemy import create_engine, text
from app.services.database import get_db_connection_url
from jetshift_core.helpers.mysql import map_mysql_to_clickhouse
from app.services.mysql_service import fetch_mysql_schema


def create_mysql_to_clickhouse_table(table_name, selected_database, source_database):
    try:
        columns = fetch_mysql_schema(source_database, table_name)
        ch_columns = []
        primary_key_column = None

        for col in columns:
            # Map MySQL data type to ClickHouse data type
            ch_type = map_mysql_to_clickhouse(col['DATA_TYPE'])
            nullable = 'NULL' if col['IS_NULLABLE'] == 'YES' else ''
            ch_columns.append(f"`{col['COLUMN_NAME']}` {ch_type} {nullable}")

            # Detect MySQL primary key
            if col.get('COLUMN_KEY') == 'PRI' and col['COLUMN_NAME'] == 'id':
                primary_key_column = 'id'

        if not ch_columns:
            return False, 'No columns found in the source table.'

        # Join column definitions
        columns_str = ",\n    ".join(ch_columns)

        # Dynamic ORDER BY based on primary key detection
        order_by = primary_key_column if primary_key_column else 'tuple()'

        clickhouse_ddl = f"""
        CREATE TABLE {table_name} (
            {columns_str}
        ) ENGINE = MergeTree()
        ORDER BY {order_by};
        """

        # Define the connection URL
        target_database_url = get_db_connection_url(selected_database)

        # Create the SQLAlchemy engine
        engine = create_engine(target_database_url, future=True)

        # Execute the DDL statement
        with engine.connect() as connection:
            connection.execute(text(clickhouse_ddl))

        return True, 'Successfully created ClickHouse table.'
    except Exception as e:
        return False, f"Failed to create ClickHouse table. Error: {str(e)}"
