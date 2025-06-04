import click
from jetshift_core.js_logger import get_logger
from jetshift_core.commands.migrations.common import generate_fake_data
from jetshift_core.commands.seeders.common import find_dependencies, table_has_data
from jetshift_core.helpers.clickhouse import insert_into_clickhouse, get_last_id_from_clickhouse
from jetshift_core.helpers.mysql import get_mysql_table_definition, get_last_id

logger = get_logger(__name__)


def seed_clickhouse(database, table_name, num_records, dependent_records, skip_dependencies, skip_dependencies_if_data_exists):
    try:
        if skip_dependencies is False:
            tables = find_dependencies(database, table_name, dependent_records)
            reversed_dependency_order = dict(reversed(tables.items()))

            for index, (the_table_name, details) in enumerate(reversed_dependency_order.items()):
                if index == len(reversed_dependency_order) - 1:
                    seed(database, table_name, num_records)
                else:
                    seed(database, the_table_name, details['dependent_records'], skip_dependencies_if_data_exists)
        else:
            seed(database, table_name, num_records)
    except Exception as e:
        logger.error("%s", e)


def seed(database, table_name, num_records, skip_if_data_exists=False):
    from jetshift_core.helpers.cli.common import read_database_from_id, read_database_from_yml_file
    from sqlalchemy import create_engine
    import pandas as pd

    try:
        table = get_mysql_table_definition(table_name)
        fields = [(col.name, col.type.python_type) for col in table.columns]
        table_fields = [field[0] for field in fields]

        # check if data is available in the table
        check_table_has_data = table_has_data(database, table_name)
        if check_table_has_data is True and skip_if_data_exists is True:
            return True

        # Get connection URL
        if isinstance(database, int):
            database_url = read_database_from_id(database, 'connection_url')
        else:
            database_url = read_database_from_yml_file(database, 'connection_url')

        target_engine = create_engine(database_url, future=True)

        # from csv
        data_info = table.info.get('data', False)
        if data_info is True:
            fields, data = generate_fake_data(database, table, fields)

            # Convert to panda frame
            df_data = pd.DataFrame(data, columns=table_fields)

            # Insert
            success, last_inserted_id = insert_into_clickhouse(target_engine, table_name, df_data)
            if success:
                click.echo(f"Seeded {len(data)} records in the table: {table_name}. Last inserted ID: {last_inserted_id}")

            return True

        # generate fake data
        last_id = get_last_id(database, table_name, 'id')

        data = []
        inserted = 0
        primary_id = last_id + 1
        for i in range(1, num_records + 1):

            row = generate_fake_data(database, table, fields)
            row = (primary_id,) + row
            # print(data)
            data.append(row)

            primary_id += 1
            inserted += 1

            if inserted % 10000 == 0:
                success, last_inserted_id = insert_into_clickhouse(target_engine, table_name, data)
                if success:
                    data = []
                    click.echo(f"Inserted {inserted} records. Remaining: {num_records - i}")

        # Convert to panda frame
        df_data = pd.DataFrame(data, columns=table_fields)

        # Insert
        success, last_inserted_id = insert_into_clickhouse(target_engine, table_name, df_data)
        if success:
            click.echo(f"Seeded {inserted} records in the table: {table_name}. Last inserted ID: {last_inserted_id}")
    except Exception as e:
        logger.error("An error occurred while seeding the table: %s", e)
