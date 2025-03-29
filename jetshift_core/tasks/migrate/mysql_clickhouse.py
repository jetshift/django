from prefect import flow, task
from jetshift_core.helpers.database import create_database_engine
from jetshift_core.js_logger import get_logger
from pathlib import Path

from jetshift_core.services.clickhouse import extract_data, load_data
from jetshift_core.utils.init_django import setup_django
from jetshift_core.utils.prefect_api import pause_prefect_deployment


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

    # Update table
    task.status = "migrating"
    task.deployment_id = deployment_id
    task.save()


@flow(name="MySQL to ClickHouse Migration")
def mysql_to_clickhouse_flow(migrate_table_id, task_id):
    setup_django()
    import asyncio
    from app.models import MigrateTable, MigrationTask
    from sqlalchemy import text
    from jetshift_core.helpers.migrations.common import AttrDict

    js_logger = get_logger()

    migrate_table_obj = MigrateTable.objects.get(id=migrate_table_id)
    task = MigrationTask.objects.get(id=task_id)

    js_logger.info(f"Started {migrate_table_obj.title} flow.")

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
        asyncio.run(pause_prefect_deployment(task.deployment_id))

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
        # Pause it immediately after deploying
        asyncio.run(pause_prefect_deployment(task.deployment_id))

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
