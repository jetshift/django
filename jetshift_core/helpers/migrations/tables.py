import importlib
import threading
from concurrent.futures import ThreadPoolExecutor

from jetshift_core.js_logger import get_logger
from sqlalchemy import create_engine, MetaData, Table, inspect
from sqlalchemy.exc import SQLAlchemyError

from jetshift_core.helpers.database import get_db_connection_url, create_table
from jetshift_core.helpers.migrations.common import migrate_supported_pairs

js_logger = get_logger()


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


def migrate_data(migrate_table_obj, migration_task):
    # Check migration pair support
    is_supported, supported_message, task_path = migrate_supported_pairs(
        migrate_table_obj.source_db.dialect,
        migrate_table_obj.target_db.dialect,
        check=True
    )
    if not is_supported:
        return False, supported_message

    try:
        # Dynamically load and call the correct Prefect flow
        module_path, flow_name = task_path.rsplit('.', 1)
        flow_module = importlib.import_module(module_path)
        flow_func = getattr(flow_module, flow_name)

        # Run without threading
        flow_func(migrate_table_obj, migration_task)

        # Define the worker function that runs the flow
        # def flow_worker():
        #     js_logger.info(f"[{threading.current_thread().name}] Flow started")
        #     flow_func(migrate_table_obj, task)
        #     js_logger.info(f"[{threading.current_thread().name}] Flow completed")
        #
        # # Decoupled execution - Don't block main thread with future.result()
        # executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="MigrationThread")
        # executor.submit(flow_worker)

        # Return immediately after starting the thread
        return True, "Data migration flow run successfully"

    except SQLAlchemyError as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
