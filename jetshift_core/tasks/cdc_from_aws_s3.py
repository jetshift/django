import os
from prefect import flow
from pathlib import Path
from datetime import datetime, timezone

from jetshift_core.utils.init_django import setup_django
from jetshift_core.helpers.clcikhouse import prepare_params
from jetshift_core.helpers.database import create_database_engine
from jetshift_core.helpers.subtask import extract_cdc_data_from_database
from jetshift_core.services.clickhouse import load_data
from jetshift_core.services.storage_s3 import merge_all_cdc_csv_from_s3, delete_merged_csvs_from_s3
from jetshift_core.js_logger import get_logger

js_logger = get_logger()


def cdc_from_s3_csv_flow_deploy(subtask):
    try:
        name = f"CDC S3 CSV: {subtask.source_table} Deployment"
        flow_function_name = f"cdc_from_s3_csv_flow"
        flow_function = globals()[flow_function_name]
        source_dir = Path(__file__).parent.resolve()

        deployment_id = flow_function.from_source(
            source=str(source_dir),
            entrypoint=f"{Path(__file__).name}:{flow_function_name}"
        ).deploy(
            name=name,
            parameters={
                "subtask_id": subtask.id
            },
            work_pool_name="default-agent-pool",
            tags=["cdc-s3"],
            cron=subtask.cron
        )

        js_logger.info(f"CDC Deployment {deployment_id} registered.")

        subtask.status = "syncing"
        subtask.deployment_id = deployment_id
        subtask.save()

        return True, "CDC from S3 CSV flow run successfully"

    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


@flow(name="CDC from S3 CSV Flow")
def cdc_from_s3_csv_flow(subtask_id):
    setup_django()
    from app.models import JSSubTask, JSTask

    subtask = JSSubTask.objects.get(id=subtask_id)
    table_name = subtask.target_table
    now = datetime.now(timezone.utc)
    current_time_prefix = now.strftime("%Y%m%d_%H%M")

    # Setup output dir
    output_filename = f"cdc_{table_name}_{current_time_prefix}.csv"
    output_path = os.path.join('data', output_filename)
    # output_path = "data/cdc_orders_20250603_1917.csv"

    # Task 1
    merge_all_cdc_csv_from_s3(subtask.target_table, output_path)

    task_obj = JSTask.objects.get(id=subtask.task_id)
    source_engine = create_database_engine(task_obj.source_db)
    target_engine = create_database_engine(task_obj.target_db)
    params = prepare_params(task_obj, subtask, source_engine, target_engine)

    # Task 2
    extract_cdc_data_from_database(params, output_path)

    # Task 3
    total_updated_items = load_data(params)
    js_logger.info(f"Total updated items this time: {total_updated_items}")

    # Task 4
    if total_updated_items > 0:
        delete_merged_csvs_from_s3(subtask.target_table)

    # Final: delete the merged scv
    if os.path.exists(output_path):
        os.remove(output_path)
