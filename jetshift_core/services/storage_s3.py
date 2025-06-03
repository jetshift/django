def merge_all_cdc_csv_from_s3(table_name, output_path):
    from jetshift import settings
    import boto3
    import pandas as pd
    import gzip
    from io import BytesIO
    from jetshift_core.js_logger import get_logger
    js_logger = get_logger()

    try:
        s3 = boto3.client('s3')
        backup_path = 'aws-dms/electronicfirst'
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

        # Save merged CSV
        merged_df.to_csv(output_path, index=False)

        js_logger.info(f"CDC CSV saved to: {output_path}")
    except Exception as e:
        js_logger.error(f"CDC CSV save failed for table {table_name}: {str(e)}")
