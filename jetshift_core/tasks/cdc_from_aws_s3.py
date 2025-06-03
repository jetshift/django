import os
from prefect import flow
from datetime import datetime, timezone
from app.models import JSTask
from jetshift_core.helpers.clcikhouse import prepare_params
from jetshift_core.helpers.database import create_database_engine
from jetshift_core.helpers.subtask import extract_cdc_data_from_database
from jetshift_core.services.clickhouse import load_data
from jetshift_core.services.storage_s3 import merge_all_cdc_csv_from_s3
from jetshift_core.js_logger import get_logger

js_logger = get_logger()


def cdc_from_s3_csv_flow_deploy(subtask):
    try:
        cdc_from_s3_csv_flow(subtask)

        # Return immediately after starting the thread
        return True, "CDC from CSV flow run successfully"

    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


# @flow(name="CDC from S3 CSV Flow")
def cdc_from_s3_csv_flow(subtask):
    # Task 1
    table_name = subtask.target_table
    now = datetime.now(timezone.utc)
    current_time_prefix = now.strftime("%Y%m%d_%H%M")

    output_filename = f"cdc_{table_name}_{current_time_prefix}.csv"
    output_path = os.path.join('data', output_filename)
    print(output_path)

    merge_all_cdc_csv_from_s3(subtask.target_table, output_path)

    # Task 2
    task_obj = JSTask.objects.get(id=subtask.task_id)

    # Create sqlalchemy engines
    source_engine = create_database_engine(task_obj.source_db)
    target_engine = create_database_engine(task_obj.target_db)

    # Prepare parameters
    params = prepare_params(task_obj, subtask, source_engine, target_engine)

    extract_cdc_data_from_database(params, output_path)

    # Task 3
    # total_updated_items = load_data(params)
    # js_logger.info(f"Total updated items this time: {total_updated_items}")
