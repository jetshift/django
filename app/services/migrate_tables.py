from sqlalchemy import create_engine, MetaData, Table, inspect
from sqlalchemy.exc import SQLAlchemyError
from app.services.database import get_db_connection_url


def read_table_schema(migrate_table_obj, table_type, table_name):
    try:
        # Extract migration data
        data = migrate_table_obj.data

        # Determine the table to read based on the type (source/target)
        if table_type == 'source':
            first_table = data.get('source_table')
        else:
            first_table = data.get('target_table')

        # Select table name from param or migration data
        selected_table = table_name or first_table
        if not selected_table:
            return False, "Table name not provided or missing in migration data", []

        # Get database connection URL
        database = migrate_table_obj.source_db
        database_url = get_db_connection_url(database)

        # Create database engine
        engine = create_engine(database_url, future=True)

        # Explicitly connect to check connection errors and table existence
        with engine.connect() as connection:
            # Check if table exists
            inspector = inspect(engine)
            if not inspector.has_table(selected_table):
                return False, f"Table '{selected_table}' does not exist in the '{table_type}' database.", []

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

        success = True
        message = "Schema fetched successfully"
        return success, message, schema

    except SQLAlchemyError as e:
        # Handle database or reflection-related errors
        return False, f"Database error: {str(e)}", []

    except Exception as e:
        # Handle any other unexpected errors
        return False, f"Unexpected error: {str(e)}", []
