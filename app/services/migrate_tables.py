from sqlalchemy import create_engine, MetaData, Table, inspect
from sqlalchemy.exc import SQLAlchemyError

from app.services.database import get_db_connection_url, create_table, create_database_engine
from app.services.migrate.common import migrate_supported_pairs


def read_table_schema(database, table_name, table_type='source', create=False, source_db=None):
    try:
        # Get database connection URL
        selected_database_url = get_db_connection_url(database)

        # Create database engine
        engine = create_engine(selected_database_url, future=True)

        success = True
        message = "Schema fetched successfully"

        # Explicitly connect to check connection errors and table existence
        with engine.connect() as connection:
            # Check if table exists
            inspector = inspect(engine)
            if not inspector.has_table(table_name):
                message = f"Table '{table_name}' does not exist in {table_type} database '{database.title}'."

                if create and table_type == 'target':
                    message = f"Created '{table_name}' table and schema fetched successfully"
                    created, created_message = create_table(table_name, database, source_db)
                    if not created:
                        return False, message, []
                else:
                    return False, message, []

            # Initialize MetaData object
            metadata = MetaData()

            # Reflect the table schema
            table = Table(table_name, metadata, autoload_with=connection)

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


def migrate_data(migrate_table_obj, task):
    import importlib
    from config.luigi import luigi, local_scheduler

    # Check the migration pair
    is_supported, supported_message, task_path = migrate_supported_pairs(
        migrate_table_obj.source_db.dialect,
        migrate_table_obj.target_db.dialect,
        check=True
    )

    if not is_supported:
        return is_supported, supported_message

    # Dynamically import the task class
    module_path, class_name = task_path.rsplit('.', 1)
    task_module = importlib.import_module(module_path)
    task_class = getattr(task_module, class_name)

    try:
        success = True
        message = "Data copied successfully"

        luigi.build([task_class(
            #
            source_engine=create_database_engine(migrate_table_obj.source_db),
            target_engine=create_database_engine(migrate_table_obj.target_db),
            source_table=task.source_table,
            target_table=task.target_table,
            #
            live_schema=False,
            primary_id='id',
            # extract
            extract_offset=0,
            extract_limit=10,
            # extract_chunk_size=20,
            # load
            truncate_table=False,
            load_chunk_size=10,
            sleep_interval=1
        )], local_scheduler=local_scheduler)

        return success, message

    except SQLAlchemyError as e:
        # Handle database or reflection-related errors
        return False, f"Database error: {str(e)}", []

    except Exception as e:
        # Handle any other unexpected errors
        return False, f"Unexpected error: {str(e)}", []
