def mysql_table_exists(connection, table_name, database_name):
    from sqlalchemy import text
    result = connection.execute(text("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = :db_name AND table_name = :table_name
    """), {"db_name": database_name, "table_name": table_name})

    return result.scalar() > 0


def fetch_mysql_schema(database, table):
    from jetshift_core.helpers.database import get_db_connection_url
    from sqlalchemy import create_engine, text

    database_url = get_db_connection_url(database)
    engine = create_engine(database_url, future=True)

    query = text("""
        SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, COLUMN_KEY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table
        ORDER BY ORDINAL_POSITION;
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {'db': database.database, 'table': table})
        columns = [dict(row._mapping) for row in result]
    return columns


def get_mysql_table_definition(table_name, live_schema=False):
    if live_schema is True:
        table = get_mysql_database_table_definition(table_name)
    else:
        table = get_mysql_yaml_table_definition(table_name)

    return table


# Reflect database structure from yaml file
def get_mysql_yaml_table_definition(table_name):
    import os
    import sys
    from jetshift_core.helpers.common import jprint
    from jetshift_core.commands.migrations.mysql import yaml_table_definition

    app_path = os.environ.get('APP_PATH', '')
    file_path = f'{app_path}play/migrations/{table_name}.yml'
    if not os.path.exists(file_path):
        jprint(f"Migration '{file_path}' does not exist.", 'error')
        sys.exit(1)

    table = yaml_table_definition(file_path)

    return table


# Reflect the existing database structure
def get_mysql_database_table_definition(table_name):
    from jetshift_core.utils.database.sqlalchemy_mysql import get_engine, MetaData, Table

    engine = get_engine()
    metadata = MetaData()
    metadata.reflect(bind=engine)

    # Access the users table using the reflected metadata
    table = Table(table_name, metadata, autoload_with=engine)

    return table


# def check_table_has_data(database, table_name):
#     try:
#         from jetshift_core.helpers.cli.common import read_database_from_id, read_database_from_yml_file
#         from sqlalchemy import create_engine, text
#
#         # Get connection URL
#         if isinstance(database, int):
#             database_url = read_database_from_id(database, 'connection_url')
#         else:
#             database_url = read_database_from_yml_file(database, 'connection_url')
#
#         engine = create_engine(database_url, future=True)
#
#         with engine.connect() as connection:
#             result = connection.execute(text(f"SELECT 1 FROM `{table_name}` LIMIT 1"))
#             return result.fetchone() is not None
#     except Exception as e:
#         handle_mysql_error(e)


def get_last_id(database, table_name, column_name='id'):
    try:
        from jetshift_core.helpers.cli.common import read_database_from_id, read_database_from_yml_file
        from sqlalchemy import create_engine, text

        # Get connection URL
        if isinstance(database, int):
            database_url = read_database_from_id(database, 'connection_url')
        else:
            database_url = read_database_from_yml_file(database, 'connection_url')

        engine = create_engine(database_url, future=True)

        with engine.connect() as connection:
            result = connection.execute(text(f"SELECT MAX({column_name}) FROM `{table_name}`"))
            row = result.fetchone()
            return row[0] if row and row[0] is not None else 0
    except Exception as e:
        handle_mysql_error(e)


def get_min_max_id(table_name):
    try:
        connection = mysql_connect()
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT MIN(id), MAX(id) FROM {table_name}")
            result = cursor.fetchone()
            if result[0] is None or result[1] is None:
                return 0, 0
            return result[0], result[1]
    except Exception as e:
        handle_mysql_error(e)


def handle_mysql_error(error):
    from jetshift_core.js_logger import get_logger
    js_logger = get_logger()
    js_logger.error(f"MySQL connection failed: {str(error)}")


def fetch_and_extract_limit(params):
    import pandas as pd
    from datetime import datetime, timedelta
    from jetshift_core.js_logger import get_logger
    from sqlalchemy import MetaData, Table, select
    from jetshift_core.helpers.common import clear_files, create_data_directory
    from jetshift_core.helpers.clickhouse import get_last_id_from_clickhouse, truncate_table as truncate_clickhouse_table

    js_logger = get_logger()

    table_name = params.source_table
    truncate_table = params.truncate_table
    output_path = params.output_path
    extract_offset = params.extract_offset
    extract_limit = params.extract_limit
    primary_id = params.primary_id
    detect_changes = params.detect_changes  # minutes or None

    if truncate_table:
        truncate_clickhouse_table(params.target_engine, table_name)

    # Reflect the table structure
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=params.source_engine)

    # Start building the SQLAlchemy query
    stmt = select(table)

    # Filter rows where updated_at is within the last minutes
    if detect_changes:
        threshold_time = datetime.now() - timedelta(minutes=int(params.detect_changes))
        stmt = stmt.where(table.c.updated_at >= threshold_time)
    else:
        # If primary_id is defined, apply the last_id filtering
        if primary_id:
            last_id = get_last_id_from_clickhouse(params.target_engine, params.target_table, primary_id)
            js_logger.info(f"Last ClickHouse {params.target_table} {primary_id}: {last_id}")
            stmt = stmt.where(table.c[primary_id] > last_id)

    # Apply limit and offset
    stmt = stmt.limit(extract_limit).offset(extract_offset)

    # Use pandas to execute and fetch the query result
    df = pd.read_sql(stmt, params.source_engine)

    # Clear old files and save new CSV
    clear_files(params)
    create_data_directory()
    df.to_csv(output_path, index=False)


def fetch_and_extract_chunk(params):
    import os
    import pandas as pd
    import time
    from jetshift_core.js_logger import get_logger
    from sqlalchemy import MetaData, Table, select, func
    from jetshift_core.helpers.clickhouse import get_last_id_from_clickhouse, truncate_table as truncate_clickhouse_table

    js_logger = get_logger()

    table_name = params.source_table
    truncate_table = params.truncate_table
    output_path = params.output_path
    extract_offset = params.extract_offset
    extract_chunk_size = params.extract_chunk_size
    primary_id = params.primary_id
    sleep_interval = params.sleep_interval

    if truncate_table:
        truncate_clickhouse_table(params.target_engine, table_name)

    # Clear old data
    if os.path.exists(params.output_path):
        os.remove(params.output_path)

    # Reflect the table
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=params.source_engine)

    # Build count query
    stmt_count = select(func.count()).select_from(table)
    last_id = None
    if primary_id:
        last_id = get_last_id_from_clickhouse(params.target_engine, table_name, primary_id)
        js_logger.info(f"Last ClickHouse {table_name} {primary_id}: {last_id}")
        stmt_count = stmt_count.where(table.c[primary_id] > last_id)

    # Execute count properly
    with params.source_engine.connect() as connection:
        total_rows = connection.execute(stmt_count).scalar()

    if total_rows > 0:
        total_rows -= extract_offset
    js_logger.info(f"Total rows in {table_name} (mysql): {total_rows}")

    loops = (total_rows + extract_chunk_size - 1) // extract_chunk_size
    js_logger.info(f"Total loops: {loops}")
    js_logger.info(f"\nExtracting data...")

    # Extract in chunks
    for i in range(loops):
        stmt = select(table)

        if primary_id and last_id is not None:
            stmt = stmt.where(table.c[primary_id] > last_id)

        # Apply limit and dynamic offset for each loop
        current_offset = (i * extract_chunk_size) + extract_offset
        stmt = stmt.limit(extract_chunk_size).offset(current_offset)

        # Read data into DataFrame
        df = pd.read_sql(stmt, params.source_engine)

        # Append chunk to CSV
        df.to_csv(output_path, mode='a', header=(i == 0), index=False)

        js_logger.info(f"Extracted {len(df)} rows from {table_name}. Loop {i + 1}/{loops}")
        time.sleep(sleep_interval)
