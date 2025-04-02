from datetime import timedelta

from prefect import flow
from pathlib import Path

from jetshift_core.utils.init_django import setup_django
from jetshift_core.utils.prefect_api import pause_prefect_deployment
from jetshift_core.helpers.clcikhouse import prepare_params
from jetshift_core.helpers.database import create_database_engine
from jetshift_core.services.clickhouse import extract_data, load_data
from jetshift_core.js_logger import get_logger


def mysql_to_clickhouse_flow_deploy(migrate_table_obj, migration_task):
    js_logger = get_logger()

    # Step 1: Determine the flow function name
    flow_function_name = "mysql_to_clickhouse_migration_flow"
    if migrate_table_obj.type == "etl":
        flow_function_name = "mysql_to_clickhouse_etl_flow"

    # Step 2: Get the actual function from the global scope
    flow_function = globals()[flow_function_name]
    source_dir = Path(__file__).parent.resolve()  # Gets the full directory path

    # Step 3: Deploy using the dynamically selected function
    deployment_id = flow_function.from_source(
        source=str(source_dir),  # must be a directory
        entrypoint=f"{Path(__file__).name}:{flow_function_name}"
    ).deploy(
        name=f"{migrate_table_obj.title} : Task {migration_task.id} ({migration_task.source_table} to {migration_task.target_table}) Deployment",
        parameters={
            "migrate_table_id": migrate_table_obj.id,
            "task_id": migration_task.id
        },
        work_pool_name="default-agent-pool",
        tags=["mysql", "clickhouse", "auto"],
        # cron="* * * * *",  # Cron expression for every minute
        interval=timedelta(minutes=1)  # Schedule to run every minute
    )

    js_logger.info(f"Deployment {deployment_id} registered.")

    # # Step 4: Run the flow
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
    migration_task.status = "syncing"
    migration_task.deployment_id = deployment_id
    migration_task.save()


@flow(name="MySQL to ClickHouse Migration")
def mysql_to_clickhouse_migration_flow(migrate_table_id, task_id):
    mysql_to_clickhouse_flow(migrate_table_id, task_id, 'migration')


@flow(name="MySQL to ClickHouse ETL")
def mysql_to_clickhouse_etl_flow(migrate_table_id, task_id):
    mysql_to_clickhouse_flow(migrate_table_id, task_id, 'etl')


# Main function
def mysql_to_clickhouse_flow(migrate_table_id, task_id, flow_type):
    setup_django()
    import asyncio
    from app.models import JSTask, JSSubTask
    from sqlalchemy import text

    js_logger = get_logger()

    migrate_table_obj = JSTask.objects.get(id=migrate_table_id)
    migration_task = JSSubTask.objects.get(id=task_id)

    js_logger.info(f"Started '{migrate_table_obj.title}' {flow_type} flow.")

    # Create sqlalchemy engines
    source_engine = create_database_engine(migrate_table_obj.source_db)
    target_engine = create_database_engine(migrate_table_obj.target_db)

    # Counting source table's rows
    with source_engine.connect() as connection:
        source_count_result = connection.execute(text(f"SELECT COUNT(*) FROM {migration_task.source_table}"))
    total_source_items = source_count_result.scalar() or 0
    js_logger.info(f"Total source items ({migration_task.source_table}): {total_source_items}")

    # Counting target table's rows
    with target_engine.connect() as connection:
        target_count_result = connection.execute(text(f"SELECT COUNT(*) FROM {migration_task.target_table}"))
    total_target_items = target_count_result.scalar() or 0
    js_logger.info(f"Total target items ({migration_task.target_table}): {total_target_items}")

    # Compare & pause migration (only for migration flow)
    if flow_type == "migration" and total_source_items == total_target_items:
        # Update task
        migration_task.status = 'completed'
        migration_task.stats['total_source_items'] = total_source_items
        migration_task.stats['total_target_items'] = total_target_items
        migration_task.save()

        # Pause it immediately after deploying
        asyncio.run(pause_prefect_deployment(migration_task.deployment_id))

        js_logger.info(f"Source and target tables match, skipping.")
        return True

    # Prepare parameters
    params = prepare_params(migrate_table_obj, migration_task, source_engine, target_engine)

    # Run tasks
    extract_data(params)
    total_loaded_items = load_data(params)

    js_logger.info(f"Total migrated items this time: {total_loaded_items}")

    total_migrated_items = total_target_items + total_loaded_items
    js_logger.info(f"Total migrated items: {total_migrated_items}")

    task_status = "syncing"

    # Compare & pause migration (only for migration flow)
    if flow_type == "migration" and total_source_items == total_target_items:
        # Pause it immediately after deploying
        asyncio.run(pause_prefect_deployment(migration_task.deployment_id))

        migration_task.status = 'completed'
        task_status = 'completed'

    # Update task
    migration_task.stats['total_source_items'] = total_source_items
    migration_task.stats['total_target_items'] = total_migrated_items
    migration_task.save()

    # Send WebSocket notification
    try:
        from app.utils.notify import trigger_websocket_notification
        trigger_websocket_notification({
            "migrate_table_id": migrate_table_obj.id,
            "task_id": migration_task.id,
            "status": task_status,
            "total_source_items": total_source_items,
            "total_target_items": total_migrated_items
        })
    except Exception as e:
        js_logger.error(f"WebSocket notification failed: {e}")
