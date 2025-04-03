import click
from jetshift_core.js_logger import get_logger
from jetshift_core.commands.migrations.common import generate_fake_data
from jetshift_core.commands.seeders.common import find_dependencies, table_has_data
from jetshift_core.helpers.mysql import get_mysql_table_definition, get_last_id

logger = get_logger(__name__)


def seed_mysql(database, table_name, num_records, dependent_records, skip_dependencies, skip_dependencies_if_data_exists):
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
    try:
        table = get_mysql_table_definition(table_name)
        fields = [(col.name, col.type.python_type) for col in table.columns]

        # check if data is available in the table
        check_table_has_data = table_has_data(database, table_name)
        if check_table_has_data is True and skip_if_data_exists is True:
            return True

        # from csv
        data_info = table.info.get('data', False)
        if data_info is True:
            fields, data = generate_fake_data(database, table, fields)

            insert(database, table_name, fields, data)

            click.echo(f"Seeded {len(data)} records in the table: {table_name}")

            return True

        # generate fake data
        # fields = [(field[0], convert_field_to_python(field[1])) for field in fields_data]
        table_fields = [field[0] for field in fields]
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
                click.echo(f"Inserted {inserted} records. Remaining: {num_records - i}")

        insert(database, table_name, table_fields, data)

        click.echo(f"Seeded {inserted} records in the table: {table_name}")

    except Exception as e:
        logger.error("An error occurred while seeding the table: %s", e)


def insert(database, table_name, fields, data):
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError
    from jetshift_core.helpers.cli.common import read_database_from_id, read_database_from_yml_file

    # Get connection URL
    if isinstance(database, int):
        database_url = read_database_from_id(database, 'connection_url')
    else:
        database_url = read_database_from_yml_file(database, 'connection_url')

    engine = create_engine(database_url, future=True)

    # Build SQL insert statement
    placeholders = ', '.join([f":{field}" for field in fields])
    sql = text(f"INSERT INTO `{table_name}` ({', '.join(fields)}) VALUES ({placeholders})")

    try:
        with engine.begin() as connection:
            connection.execute(sql, [dict(zip(fields, row)) for row in data])
    except SQLAlchemyError as e:
        logger.error(f"An error occurred while seeding the table: {e}")
