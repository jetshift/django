from jetshift_core.helpers.clcikhouse import prepare_params
from jetshift_core.helpers.database import create_database_engine
from jetshift_core.services.clickhouse import load_data
from prefect import task as prefect_task
from jetshift_core.js_logger import get_logger

js_logger = get_logger()


# @prefect_task(cache_key_fn=lambda *args: None)
def extract_cdc_data_from_database(params, output_path, chunk_size=100):
    import os
    import pandas as pd
    from sqlalchemy import MetaData, Table, select

    try:
        table_name = params.source_table
        source_engine = params.source_engine

        # Step 1: Read order_id column from CSV
        df_ids = pd.read_csv(output_path, usecols=['id'])
        ids = df_ids['id'].dropna().astype(int).tolist()

        if not ids:
            js_logger.warning("No order_ids found in CSV.")
            return

        # Clear old data
        if os.path.exists(params.output_path):
            os.remove(params.output_path)

        # Step 2: Reflect the table
        metadata = MetaData()
        table = Table(table_name, metadata, autoload_with=source_engine)

        # Step 3: Process in chunks
        total_rows = 0
        header_written = False
        for i in range(0, len(ids), chunk_size):
            chunk_ids = ids[i:i + chunk_size]
            stmt = select(table).where(table.c.id.in_(chunk_ids))
            df_chunk = pd.read_sql(stmt, source_engine)

            if not df_chunk.empty:
                df_chunk.to_csv(params.output_path, mode='a', index=False, header=not header_written)
                header_written = True
                total_rows += len(df_chunk)

        js_logger.info(f"Extracted {total_rows} rows from {table_name} into {params.output_path}")
    except Exception as e:
        js_logger.error(f"Extraction failed: {str(e)}")
