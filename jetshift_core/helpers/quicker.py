import click
from click.testing import CliRunner

runner = CliRunner()


def parse_seeder_string(item):
    parts = item.split()
    seeder_info = {
        "seeder": None,
        "n": 10,  # Default for -n
        "nd": 5,  # Default for -nd
        "sd": False,  # Default for -sd
        "sde": False  # Default for -sde
    }

    # Parse each part of the command
    for index, part in enumerate(parts):
        if index == 0:
            seeder_info["seeder"] = part
        elif part == "-n" and index + 1 < len(parts):
            seeder_info["n"] = int(parts[index + 1])
        elif part == "-nd" and index + 1 < len(parts):
            seeder_info["nd"] = int(parts[index + 1])
        elif part == "-sd":
            seeder_info["sd"] = True
        elif part == "-sde":
            seeder_info["sde"] = True

    return seeder_info


def run_migrations(database, names, fresh):
    from jetshift_core.commands.migrations.migration import migration_command

    if names:
        for name in names:
            result = runner.invoke(migration_command, [name, '--database', database] + (['--fresh'] if fresh else []))
            click.echo(result.output)
    else:
        result = runner.invoke(migration_command, ['--database', database] + (['--fresh'] if fresh else []))
        click.echo(result.output)


def run_seeders(items, database='mysql'):
    from jetshift_core.commands.seeders.seeder import seed_command
    for item in items:
        parsed_info = parse_seeder_string(item)
        seeder = parsed_info.get("seeder")
        n = parsed_info.get("n", 10)
        nd = parsed_info.get("nd", 5)
        sd = parsed_info.get("sd", False)
        sde = parsed_info.get("sde", False)

        # Dynamically construct the command arguments
        args = [
            "--database", database,  # database
            seeder,  # Seeder name
            "-n", str(n),  # Number of records
            "-nd", str(nd),  # Dependent records
        ]

        # Add flags if they are set to True
        if sd:
            args.append("-sd")
        if sde:
            args.append("-sde")

        # Invoke the command using the runner
        result = runner.invoke(seed_command, args)

        click.echo(result.output)


def run_jobs(items):
    from jetshift_core.commands.job import main as run_job
    for item in items:
        result = runner.invoke(run_job, [item])
        click.echo(result.output)
