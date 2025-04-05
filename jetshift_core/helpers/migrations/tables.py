import importlib
from jetshift_core.js_logger import get_logger
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError

from jetshift_core.helpers.database import get_db_connection_url, create_table, check_table_exists
from jetshift_core.helpers.migrations.common import migrate_supported_pairs

js_logger = get_logger()


def read_table_schema(database, task, table_type='source', create=False, source_db=None):
    try:
        # Get database connection URL
        selected_database_url = get_db_connection_url(database)

        # Create database engine
        engine = create_engine(selected_database_url, future=True)

        table_name = task.source_table if table_type == 'source' else task.target_table

        success = True
        message = "Schema fetched successfully"

        # Explicitly connect to check connection errors and table existence
        try:
            with engine.connect() as connection:

                if not check_table_exists(connection, database, table_name):
                    message = f"Table '{table_name}' does not exist in {table_type} database '{database.title}'."

                    if create and table_type == 'target':
                        created, created_message = create_table(task, database, source_db)
                        if created:
                            message = f"Created '{table_name}' table and schema fetched successfully"
                        else:
                            return False, message, []
                    else:
                        return False, message, []

                metadata = MetaData()
                table = Table(table_name, metadata, autoload_with=connection)

        except SQLAlchemyError as e:
            return False, f"SQLAlchemy error occurred: {str(e)}", []
        except Exception as e:
            return False, f"Unexpected error occurred: {str(e)}", []

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
