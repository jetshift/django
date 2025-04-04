import glob
import sys
import os
import click

from jetshift_core.helpers.cli.common import find_database_dialect
from jetshift_core.commands.migrations.mysql import migrate as migrate_mysql
from jetshift_core.commands.migrations.clickhouse import migrate as migrate_clickhouse


def run_migration(database, migration_name, fresh, drop):
    try:
        app_path = os.environ.get('APP_PATH', '')
        file_path = f'{app_path}play/migrations/{migration_name}.yml'
        if not os.path.exists(file_path):
            click.echo(f"Migration '{file_path}' does not exist.", err=True)
            sys.exit(1)

        click.echo(f"Migrating table: {migration_name}")

        # Find dialect
        dialect = find_database_dialect(database)

        # Create table
        if dialect == "mysql":
            migrate_mysql(database, file_path, fresh, drop)

        elif dialect == "clickhouse":
            migrate_clickhouse(database, file_path, fresh, drop)

        else:
            click.echo(f"Dialect '{dialect}' is not supported.", err=True)
            sys.exit(1)

        click.echo(f"Migrated table: {migration_name}")
        click.echo("-----")

    except Exception as e:
        click.echo(f"Error migrating table '{migration_name}': {e}", err=True)
        sys.exit(1)


def list_available_migrations():
    package_path = f"play/migrations"

    if not os.path.exists(package_path):
        click.echo(f"Migration directory '{package_path}' does not exist.", err=True)
        sys.exit(1)

    available_migrations = glob.glob(os.path.join(package_path, '*.yml'))
    migration_names = [os.path.splitext(os.path.basename(migration))[0] for migration in available_migrations]

    return migration_names


def run_all_migrations(database, fresh, drop):
    available_migrations = list_available_migrations()
    if not available_migrations:
        click.echo("No migrations found.", err=True)
        sys.exit(1)

    for migration_name in available_migrations:
        run_migration(database, migration_name, fresh, drop)


@click.command(help="Run migrations for a specified database.")
@click.argument("migration", required=False, default=None)
@click.option(
    "-db", "--database", required=True, help="Name of the database (databases.yml)"
)
@click.option(
    "-f", "--fresh", is_flag=True, help="Truncate the table before running the migration."
)
@click.option(
    "-d", "--drop", is_flag=True, help="Drop the table from the database."
)
def migration_command(migration, database, fresh, drop):
    click.echo(f"Running migrations for database '{database}'")
    click.echo("----------")

    if migration:
        run_migration(database, migration, fresh, drop)
    else:
        run_all_migrations(database, fresh, drop)
