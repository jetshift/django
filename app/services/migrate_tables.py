from sqlalchemy import create_engine, MetaData, Table, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from app.services.database import get_db_connection_url, fetch_mysql_schema
from app.services.mapping import mysql_to_clickhouse


def create_table(table_name, selected_database, source_database):
    columns = fetch_mysql_schema(source_database, table_name)
    ch_columns = []
    for col in columns:
        ch_type = mysql_to_clickhouse.get(col['DATA_TYPE'], 'String')
        nullable = 'NULL' if col['IS_NULLABLE'] == 'YES' else ''
        ch_columns.append(f"`{col['COLUMN_NAME']}` {ch_type} {nullable}")

    # Join column definitions with newline outside the f-string
    columns_str = ",\n    ".join(ch_columns)

    clickhouse_ddl = f"""
    CREATE TABLE {table_name} (
        {columns_str}
    ) ENGINE = MergeTree()
    ORDER BY tuple();
    """

    # Define the connection URL
    target_database_url = get_db_connection_url(selected_database)

    # Create the SQLAlchemy engine
    engine = create_engine(target_database_url, future=True)

    # Execute the DDL statement
    with engine.connect() as connection:
        # # Check if table exists in source database
        # inspector = inspect(engine)
        # if not inspector.has_table(table_name):
        #     message = f"Table '{table_name}' does not exist in source database '{source_database.title}'."
        #     return False, message

        connection.execute(text(clickhouse_ddl))

    return True, 'Successfully created table'


def read_table_schema(migrate_table_obj, table_type, table_name):
    try:
        # Extract migration data
        data = migrate_table_obj.data

        # Determine the table to read based on the type (source/target)
        if table_type == 'source':
            first_table = data.get('source_table')
            selected_database = migrate_table_obj.source_db
        else:
            first_table = data.get('target_table')
            selected_database = migrate_table_obj.target_db

        # Select table name from param or migration data
        selected_table = table_name or first_table
        if not selected_table:
            return False, "Table name not provided or missing in migration data", []

        # Get database connection URL
        selected_database_url = get_db_connection_url(selected_database)

        # Create database engine
        engine = create_engine(selected_database_url, future=True)

        success = True
        message = "Schema fetched successfully"

        # Explicitly connect to check connection errors and table existence
        with engine.connect() as connection:
            # Check if table exists
            inspector = inspect(engine)
            if not inspector.has_table(selected_table):
                message = f"Table '{selected_table}' does not exist in {table_type} database '{selected_database.title}'."

                if table_type == 'target':
                    message = f"Created '{selected_table}' table and schema fetched successfully"
                    created, created_message = create_table(selected_table, selected_database, migrate_table_obj.source_db)
                    if not created:
                        success = False, created_message, []
                else:
                    return False, message, []

            # Initialize MetaData object
            metadata = MetaData()

            # Reflect the table schema
            table = Table(selected_table, metadata, autoload_with=connection)

            # Collect schema information
            schema = []
            for column in table.columns:
                schema.append({
                    "name": column.name,
                    "type": str(column.type),
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                    "default": str(column.default) if column.default is not None else None
                })

        return success, message, schema

    except SQLAlchemyError as e:
        # Handle database or reflection-related errors
        return False, f"Database error: {str(e)}", []

    except Exception as e:
        # Handle any other unexpected errors
        return False, f"Unexpected error: {str(e)}", []
