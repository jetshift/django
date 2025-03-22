from app.models import MigrateTable
from django.core.exceptions import ObjectDoesNotExist


def supported_dialects():
    return ["sqlite", "mysql", "postgresql", "clickhouse"]


def get_db_connection_url(database):
    import os

    database_url = ''
    if database.dialect == 'sqlite':
        path = "instance/" + database.database
        if not os.path.isfile(path):
            raise ValueError(f"Database file does not exist: {database.database}")
        database_url = "sqlite:///" + path

    if database.dialect == 'mysql':
        database_url = (
            f"mysql+pymysql://{database.username}:{database.password}@{database.host}:{database.port}/{database.database}"
            "?connect_timeout=5"
        )

    if database.dialect == 'postgresql':
        database_url = (
            f"postgresql+psycopg://{database.username}:{database.password}@{database.host}:{database.port}/{database.database}"
            "?connect_timeout=5"
        )

    if database.dialect == 'clickhouse':
        database_url = (
            f"clickhouse+native://{database.username}:{database.password}@{database.host}:{database.port}/{database.database}"
            "?connect_timeout=5&send_receive_timeout=5"
        )

    return database_url


def check_database_connection(database):
    from sqlalchemy import text, create_engine
    from sqlalchemy.exc import OperationalError

    try:
        # Check supported dialects
        if database.dialect not in supported_dialects():
            raise ValueError(f"Unsupported dialect: {database.dialect}")

        database_url = get_db_connection_url(database)
        engine = create_engine(database_url, future=True)
        with engine.connect() as connection:

            if database.dialect == 'sqlite':
                # Query sqlite_master for the first table
                result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                first_table = result.fetchone()
                if first_table:
                    success = True
                    message = f"Database '{database.title}' connection successful. The first table in the database is: {first_table[0]}"
                else:
                    success = False
                    message = f"Database '{database.title}' connection failed: {database.database}"
            else:
                connection.execute(text("SELECT 1"))
                connection.close()
                success = True
                message = f"Database '{database.title}' connection successful."
    except OperationalError as e:
        original_error = str(e.orig)
        success = False
        message = f"Database '{database.title}' connection failed: {original_error}"
    except Exception as e:
        success = False
        message = f"Database '{database.title}' connection failed: {e}"

    return success, message


def create_database_engine(database_model):
    from sqlalchemy import create_engine

    connection_url = get_db_connection_url(database_model)

    return create_engine(connection_url, future=True)


def create_table(table_name, selected_database, source_database):
    from app.services.clickhouse_service import create_mysql_to_clickhouse_table

    source_dialect = source_database.dialect
    target_dialect = selected_database.dialect  # Target

    # ClickHouse
    if source_dialect == 'mysql' and target_dialect == 'clickhouse':
        return create_mysql_to_clickhouse_table(table_name, selected_database, source_database)

    return False, f"Unsupported dialect pairs! Source: {source_dialect} & Target: {target_dialect}"


def get_migrate_table_by_id(table_id):
    try:
        migrate_table = MigrateTable.objects.get(id=table_id)
        return migrate_table
    except ObjectDoesNotExist:
        return None


# Todo:: Temp
def show_table_columns(engine, table_name):
    from sqlalchemy import MetaData

    metadata = MetaData()
    metadata.reflect(bind=engine)

    if table_name not in metadata.tables:
        raise Exception(f"Table '{table_name}' not found.")

    table = metadata.tables[table_name]

    # Extract (column name, python type)
    fields = []
    for column in table.columns:
        try:
            py_type = column.type.python_type
        except NotImplementedError:
            py_type = str(column.type)  # Fallback if python_type is not implemented
        fields.append((column.name, py_type))

    # Optional: Convert types if you have a conversion function
    # fields = [(field[0], convert_field_to_python(field[1])) for field in fields]

    # Get only field names
    table_fields = [field[0] for field in fields]

    return fields, table_fields
