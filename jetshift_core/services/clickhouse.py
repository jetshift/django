import pandas as pd
import time
from prefect import task as prefect_task
from sqlalchemy import create_engine, text

from jetshift_core.helpers.database import get_db_connection_url
from jetshift_core.helpers.clcikhouse import insert_into_clickhouse, get_clickhouse_to_pandas_type, optimize_table_final
from jetshift_core.helpers.common import *
from jetshift_core.helpers.migrations.tables import read_table_schema
from jetshift_core.helpers.mysql import *


def clickhouse_table_exists(connection, table_name, database_name):
    from sqlalchemy import text
    result = connection.execute(text(f"SELECT count() FROM system.tables WHERE name = :table_name AND database = :db_name"),
                                {"table_name": table_name, "db_name": database_name})
    return result.scalar() > 0


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

        with engine.connect() as connection:
            connection.execute(text(clickhouse_ddl))

        return True, 'Successfully created ClickHouse table.'
    except Exception as e:
        return False, f"Failed to create ClickHouse table. Error: {str(e)}"


@prefect_task(cache_key_fn=lambda *args: None)
def extract_data(params):
    js_logger = get_logger()

    try:
        if params.extract_limit != 0:
            fetch_and_extract_limit(params)
        else:
            fetch_and_extract_chunk(params)
        js_logger.info(f"Data extracted to {params.output_path}")
    except Exception as e:
        js_logger.error(f"Extraction failed: {str(e)}")
        raise e
    return params.output_path


@prefect_task(cache_key_fn=lambda *args: None)
def load_data(params):
    js_logger = get_logger()

    if not os.path.exists(params.output_path):
        js_logger.warning(f"No data to load for {params.target_table}")
        return False

    # Step 1: Read target table schema from ClickHouse
    success, message, schema = read_table_schema(
        database=params.target_db,
        task=params.task,
        table_type='target'
    )

    # Step 2: Precompute pandas dtypes and date columns
    pandas_dtypes = {}
    parse_date_columns = []

    for col in schema:
        ch_type = col['type']
        pandas_type = get_clickhouse_to_pandas_type(ch_type)
        if pandas_type == 'datetime64[ns]':
            parse_date_columns.append(col['name'])
        else:
            pandas_dtypes[col['name']] = pandas_type

    js_logger.info(f"Pandas dtypes: {pandas_dtypes}")
    js_logger.info(f"Date columns for parsing: {parse_date_columns}")

    # Step 3: Load and insert CSV chunk-by-chunk with auto dtype parsing
    num_rows = 0

    try:
        for chunk in pd.read_csv(
                params.output_path,
                chunksize=params.load_chunk_size,
                dtype=pandas_dtypes,
                parse_dates=parse_date_columns,
                keep_default_na=False,
                na_values=['NULL', 'null', '']
        ):
            # No need for per-column type conversion here

            # Insert chunk into ClickHouse
            success, last_inserted_id = insert_into_clickhouse(
                params.target_engine,
                params.target_table,
                chunk
            )
            if success:
                num_rows += len(chunk)
                js_logger.info(f"Inserted {len(chunk)} rows. Last ID {last_inserted_id}")

            time.sleep(params.sleep_interval)

        js_logger.info(f"Total inserted: {num_rows} rows into {params.target_table}")

        # Optimize table final (remove version data)
        if not params.keep_version_rows:
            optimize_table_final(params.target_engine, params.target_table)

    except Exception as e:
        js_logger.error(f"Load failed: {str(e)}")
        raise e

    return num_rows
