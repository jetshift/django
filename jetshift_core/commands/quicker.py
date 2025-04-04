import glob
import os
import sys
import yaml
import click
from jetshift_core.helpers.quicker import run_migrations, run_seeders, run_jobs
from jetshift_core.helpers.common import jprint


def prepare_migration(config):
    migration_config = config.get('migrations', {})
    databases = migration_config.get('databases', ['mysql'])
    names = migration_config.get('names', [])
    fresh = migration_config.get('fresh', True)

    return databases, names, fresh


def prepare_seeders(config):
    seeder_config = config.get('seeders', [])
    databases = seeder_config.get('databases', ['mysql'])
    names = seeder_config.get('names', [])

    if any('all' in name for name in names):
        params = next(name for name in names if 'all' in name).split()[1:]
        names = [os.path.splitext(os.path.basename(file))[0] for file in glob.glob('play/migrations/*.yml')]
        names = [f"{name} {' '.join(params)}" for name in names]

    return databases, names


def prepare_jobs(config, seeder_list):
    job_list = config.get('jobs', [])

    if 'all' in job_list:
        job_list = [os.path.splitext(os.path.basename(file))[0] for file in glob.glob('play/jobs/*.yml')]

    if 'seeders' in job_list:
        job_list = [
            item.split()[0] for item in seeder_list
        ]

    return job_list


def run_quicker(quicker):
    file_path = f'play/quickers/{quicker}.yml'
    if not os.path.exists(file_path):
        click.echo(f"Quicker '{file_path}' does not exist.", err=True)
        sys.exit(1)

    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)

    if 'migrations' in config:
        databases, names, fresh = prepare_migration(config)

        for database in databases:
            run_migrations(database, names, fresh)

        jprint("✓ Migrations completed", 'success', True)

    seeder_list = []
    if 'seeders' in config:
        databases, seeder_list = prepare_seeders(config)

        for database in databases:
            run_seeders(seeder_list, database)

        jprint("✓ Seeders completed", 'success', True)

    if 'jobs' in config:
        the_jobs = prepare_jobs(config, seeder_list)
        run_jobs(the_jobs)
        jprint("✓ Jobs completed", 'success', True)


@click.command(help="Run the specified quicker by name.")
@click.argument("name")
def quicker_command(name):
    run_quicker(name)
