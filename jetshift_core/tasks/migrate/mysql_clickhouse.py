import pandas as pd
import time
from prefect import flow, task
from jetshift_core.helpers.clcikhouse import insert_into_clickhouse, get_clickhouse_to_pandas_type
from jetshift_core.helpers.common import *
from jetshift_core.helpers.database import create_database_engine
from jetshift_core.helpers.migrations.tables import read_table_schema
from jetshift_core.helpers.mysql import *
from jetshift_core.js_logger import get_logger
from pathlib import Path
from jetshift_core.utils.init_django import setup_django
from jetshift_core.utils.prefect_api import pause_prefect_deployment


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


def mysql_to_clickhouse_flow_deploy(migrate_table_obj, task):
    from datetime import timedelta
    from jetshift_core.js_logger import get_logger
    js_logger = get_logger()

    # Step 1: Deploy
    deployment_id = mysql_to_clickhouse_flow.from_source(
        source=str(Path(__file__).parent),
        entrypoint="mysql_clickhouse.py:mysql_to_clickhouse_flow"
    ).deploy(
        name=f"{migrate_table_obj.title} : Task {task.id} ({task.source_table} to {task.target_table}) Deployment",
        parameters={
            "migrate_table_id": migrate_table_obj.id,
            "task_id": task.id
        },
        work_pool_name="default-agent-pool",
        tags=["mysql", "clickhouse", "auto"],
        # cron="* * * * *",  # Cron expression for every minute
        interval=timedelta(minutes=1)  # Schedule to run every minute
    )

    js_logger.info(f"Deployment {deployment_id} registered.")

    # # Step 2: Run the flow
    # async def run_flow():
    #     async with get_client() as client:
    #         flow_run = await client.create_flow_run_from_deployment(
    #             deployment_id=deployment_id,
    #             parameters={
    #                 "migrate_table_id": migrate_table_obj.id,
    #                 "task_id": task.id
    #             }
    #         )
    #         return flow_run.id
    #
    # flow_run_id = asyncio.run(run_flow())
    # js_logger.info(f"Flow run id: {flow_run_id}")


@flow(name="MySQL to ClickHouse Migration")
def mysql_to_clickhouse_flow(migrate_table_id, task_id):
    setup_django()
    import asyncio
    from prefect.context import FlowRunContext
    from app.models import MigrateTable, MigrationTask
    from sqlalchemy import text
    from jetshift_core.helpers.migrations.common import AttrDict

    js_logger = get_logger()

    migrate_table_obj = MigrateTable.objects.get(id=migrate_table_id)
    task = MigrationTask.objects.get(id=task_id)

    js_logger.info(f"Started {migrate_table_obj.title} flow.")

    # After successful run, pause the deployment
    context = FlowRunContext.get()
    deployment_id = context.flow_run.deployment_id

    # Create sqlalchemy engines
    source_engine = create_database_engine(migrate_table_obj.source_db)
    target_engine = create_database_engine(migrate_table_obj.target_db)

    # Counting source table's rows
    with source_engine.connect() as connection:
        source_count_result = connection.execute(text(f"SELECT COUNT(*) FROM {task.source_table}"))
    total_source_items = source_count_result.scalar() or 0
    js_logger.info(f"Total source items ({task.source_table}): {total_source_items}")

    # Counting target table's rows
    with target_engine.connect() as connection:
        target_count_result = connection.execute(text(f"SELECT COUNT(*) FROM {task.target_table}"))
    total_target_items = target_count_result.scalar() or 0
    js_logger.info(f"Total target items ({task.target_table}): {total_target_items}")

    # Compare and update task
    if total_source_items == total_target_items:
        # Update task
        task.status = 'completed'
        task.stats['total_source_items'] = total_source_items
        task.stats['total_target_items'] = total_target_items
        task.save()

        # Pause it immediately after deploying
        asyncio.run(pause_prefect_deployment(deployment_id))

        js_logger.info(f"Source and target tables match, skipping.")
        return True

    # Prepare parameters
    params = AttrDict(dict(
        source_db=migrate_table_obj.source_db,
        target_db=migrate_table_obj.target_db,
        source_engine=source_engine,
        target_engine=target_engine,
        source_table=task.source_table,
        target_table=task.target_table,
        # Get config
        live_schema=bool(task.config.get('live_schema', False)),
        primary_id=task.config.get('primary_id', None),
        extract_offset=int(task.config.get('extract_offset', 0)),
        extract_limit=int(task.config.get('extract_limit', 10)),
        extract_chunk_size=int(task.config.get('extract_chunk_size', 50)),
        truncate_table=bool(task.config.get('truncate_table', False)),
        load_chunk_size=int(task.config.get('load_chunk_size', 10)),
        sleep_interval=int(task.config.get('sleep_interval', 1)),
    ))
    params.output_path = f"data/{params.source_table}.csv"

    # Run tasks
    extract_data(params)
    total_loaded_items = load_data(params)

    js_logger.info(f"Total migrated items this time: {total_loaded_items}")

    total_migrated_items = total_target_items + total_loaded_items
    js_logger.info(f"Total migrated items: {total_migrated_items}")

    task_status = 'migrating'

    # Update task
    if total_source_items == total_migrated_items:

        if deployment_id:
            # Pause it immediately after deploying
            asyncio.run(pause_prefect_deployment(deployment_id))

        task.status = 'completed'
        task_status = 'completed'

    task.stats['total_source_items'] = total_source_items
    task.stats['total_target_items'] = total_migrated_items
    task.save()

    # Send WebSocket notification
    try:
        from app.utils.notify import trigger_websocket_notification
        trigger_websocket_notification({
            "migrate_table_id": migrate_table_obj.id,
            "task_id": task.id,
            "status": task_status,
            "total_source_items": total_source_items,
            "total_target_items": total_migrated_items
        })
    except Exception as e:
        js_logger.error(f"WebSocket notification failed: {e}")
