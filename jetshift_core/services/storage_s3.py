from prefect import task as prefect_task


@prefect_task(cache_key_fn=lambda *args: None)
def merge_all_cdc_csv_from_s3(table_name, output_path):
    import os
    from jetshift import settings
    import boto3
    import pandas as pd
    import gzip
    from io import BytesIO
    from jetshift_core.helpers.common import create_data_directory
    from jetshift_core.js_logger import get_logger
    js_logger = get_logger()

    try:
        s3 = boto3.client('s3')
        backup_path = settings.JS_CDC_AWS_DMS_S3_PATH
        prefix = f"{backup_path}/{table_name}/merged/"
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        merged_df = pd.DataFrame()
        paginator = s3.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                if not key.endswith('.csv.gz'):
                    continue

                js_logger.info(f"Reading: {key}")
                s3_obj = s3.get_object(Bucket=bucket_name, Key=key)
                with gzip.GzipFile(fileobj=BytesIO(s3_obj['Body'].read())) as gz:
                    df = pd.read_csv(gz, usecols=[0, 1])  # first two columns only
                    df.columns = ["type", "id"]  # rename the columns
                    merged_df = pd.concat([merged_df, df], ignore_index=True)

        if merged_df.empty:
            js_logger.info("No data found. Skipping save.")
            return

        # Delete the file if it exists
        if os.path.exists(output_path):
            os.remove(output_path)

        # Save merged CSV
        create_data_directory()
        merged_df.to_csv(output_path, index=False)

        js_logger.info(f"CDC CSV saved to: {output_path}")
    except Exception as e:
        js_logger.error(f"CDC CSV save failed for table {table_name}: {str(e)}")


@prefect_task(cache_key_fn=lambda *args: None)
def delete_merged_csvs_from_s3(table_name):
    from jetshift import settings
    import boto3
    from jetshift_core.js_logger import get_logger
    js_logger = get_logger()

    try:
        s3 = boto3.client('s3')
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        backup_path = settings.JS_CDC_AWS_DMS_S3_PATH
        prefix = f"{backup_path}/{table_name}/merged/"

        # List all objects under the prefix
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

        # Check if there are contents to delete
        if 'Contents' in response:
            # Extract the object keys
            objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]

            # Delete the objects
            s3.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': objects_to_delete}
            )
            js_logger.info(f"Deleted {len(objects_to_delete)} objects from {prefix}")
        else:
            js_logger.info("No objects found under the specified prefix.")
    except Exception as e:
        js_logger.error(f"CDC CSV save failed for table {table_name}: {str(e)}")
