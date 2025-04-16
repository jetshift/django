def supported_dialects():
    return ["sqlite", "mysql", "postgresql", "clickhouse"]


def get_db_connection_url(database):
    import os

    database_url = ''
    password = database.password or ''  # handle None safely

    if database.dialect == 'sqlite':
        path = "instance/" + database.database
        if not os.path.isfile(path):
            raise ValueError(f"Database file does not exist: {database.database}")
        database_url = "sqlite:///" + path

    if database.dialect == 'mysql':
        database_url = (
            f"mysql+pymysql://{database.username}:{password}@{database.host}:{database.port}/{database.database}"
            "?connect_timeout=5"
        )

        if database.secure:
            database_url += "&ssl=true"

    if database.dialect == 'postgresql':
        database_url = (
            f"postgresql+psycopg://{database.username}:{password}@{database.host}:{database.port}/{database.database}"
            "?connect_timeout=5"
        )

        if database.secure:
            database_url += "&sslmode=require"

    if database.dialect == 'clickhouse':
        database_url = (
            f"clickhouse+http://{database.username}:{password}@{database.host}:{database.port}/{database.database}"
            "?connect_timeout=5&send_receive_timeout=5"
        )

        if database.secure:
            database_url += "&protocol=https"

    return database_url


def check_database_connection(database):
    from sqlalchemy import text, create_engine
    from sqlalchemy.exc import OperationalError

    try:
        # Check supported dialects
        if database.dialect not in supported_dialects():
            raise ValueError(f"Unsupported dialect: {database.dialect}")

        database_url = get_db_connection_url(database)
        print(database_url)
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


def check_table_exists(connection, database, table_name):
    from sqlalchemy import inspect, text

    try:
        if database.dialect == "clickhouse":
            result = connection.execute(text("""
                SELECT count() FROM system.tables WHERE name = :table_name AND database = :db_name
            """), {"table_name": table_name, "db_name": database.database})
            return result.scalar() > 0

        elif database.dialect == "mysql":
            result = connection.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = :db_name AND table_name = :table_name
            """), {"db_name": database.database, "table_name": table_name})
            return result.scalar() > 0

        else:
            inspector = inspect(connection)
            return inspector.has_table(table_name)

    except Exception as e:
        # Optional: log or handle dialect-specific error here
        raise RuntimeError(f"Error checking table existence: {e}")


def create_table(task, selected_database, source_database):
    from jetshift_core.services.clickhouse import create_mysql_to_clickhouse_table

    source_dialect = source_database.dialect
    target_dialect = selected_database.dialect  # Target

    # ClickHouse
    if source_dialect == 'mysql' and target_dialect == 'clickhouse':
        return create_mysql_to_clickhouse_table(task, selected_database, source_database)

    return False, f"Unsupported dialect pairs! Source: {source_dialect} & Target: {target_dialect}"
