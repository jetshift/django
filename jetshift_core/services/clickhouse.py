import pandas as pd
import time
from prefect import flow, task
from sqlalchemy import create_engine, text

from jetshift_core.helpers.database import get_db_connection_url
from jetshift_core.helpers.clcikhouse import insert_into_clickhouse, get_clickhouse_to_pandas_type
from jetshift_core.helpers.common import *
from jetshift_core.helpers.migrations.tables import read_table_schema
from jetshift_core.helpers.mysql import *


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


@task(cache_key_fn=lambda *args: None)
def extract_data(params):
    js_logger = get_logger()

    try:
        if params.extract_limit:
            fetch_and_extract_limit(params)
        else:
            fetch_and_extract_chunk(params)
        js_logger.info(f"Data extracted to {params.output_path}")
    except Exception as e:
        js_logger.error(f"Extraction failed: {str(e)}")
        raise e
    return params.output_path


@task(cache_key_fn=lambda *args: None)
def load_data(params):
    js_logger = get_logger()

    if not os.path.exists(params.output_path):
        js_logger.warning(f"No data to load for {params.target_table}")
        return False

    # 🔎 Step 1: Read target table schema from ClickHouse
    success, message, schema = read_table_schema(
        database=params.target_db,
        table_name=params.target_table,
        table_type='target'
    )

    # 🔎 Step 2: Precompute pandas dtypes and date columns
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

    # 🔎 Step 3: Load and insert CSV chunk-by-chunk with auto dtype parsing
    num_rows = 0
    last_inserted_id = None

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

            # 🔄 Insert chunk into ClickHouse
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
    except Exception as e:
        js_logger.error(f"Load failed: {str(e)}")
        raise e

    return num_rows
