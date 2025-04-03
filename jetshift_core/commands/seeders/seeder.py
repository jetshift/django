import glob
import sys
import os
import click
from jetshift_core.commands.seeders.mysql import seed_mysql
from jetshift_core.commands.seeders.clickhouse import seed_clickhouse
from jetshift_core.commands.seeders.csv import seed_csv
from jetshift_core.helpers.cli.common import find_database_dialect


def run_seeder(database, seeder_name, records, dependent_records, skip_dependencies, skip_dependencies_if_data_exists):
    try:
        click.echo(f"Running seeder: {seeder_name}")

        # Find dialect
        dialect = find_database_dialect(database)

        if dialect == "mysql":
            seed_mysql(database, seeder_name, records, dependent_records, skip_dependencies, skip_dependencies_if_data_exists)

        elif dialect == "clickhouse":
            seed_clickhouse(database, seeder_name, records, dependent_records, skip_dependencies, skip_dependencies_if_data_exists)

        elif dialect == "csv":
            seed_csv(database, seeder_name, records, dependent_records, skip_dependencies, skip_dependencies_if_data_exists)

        else:
            click.echo(f"Seeder engine '{database}' is not supported.", err=True)
            sys.exit(1)

    except ModuleNotFoundError:
        click.echo(f"Seeder '{seeder_name}' not found. Please check the seeder engine.", err=True)
        sys.exit(1)

    except AttributeError:
        click.echo(f"The seeder '{seeder_name}' does not have a 'main' function.", err=True)
        sys.exit(1)


@click.command(help="Run seeders for a specified engine. You can run a specific seeder or all seeders in a engine.")
@click.argument("seeder", required=False, default=None)
@click.option(
    "-db", "--database", required=True, help="Name of the database (databases.yml)"
)
@click.option("-n", default=10, help="Number of records to seed. Default is 10.")
@click.option("-nd", default=5, help="Number of records to seed for dependencies. Default is 5.")
@click.option(
    "-sd", is_flag=True, default=False, help="Skip dependent seeders. Default is False."
)
@click.option(
    "-sde", is_flag=True, default=False, help="Skip dependent seeders if data already exists. Default is False."
)
def main(database, seeder, n, nd, sd, sde):
    if seeder is None:
        seeder_list = [os.path.splitext(os.path.basename(file))[0] for file in glob.glob('play/migrations/*.yml')]
        if not seeder_list:
            click.echo("No seeders found.")
            return

        for seeder_name in seeder_list:
            run_seeder(database, seeder_name, n, nd, sd, sde)
    else:
        run_seeder(database, seeder, n, nd, sd, sde)


if __name__ == "__main__":
    main()
