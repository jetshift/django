import click
import sys
from jetshift_core.js_logger import get_logger

from jetshift_core.commands.banners import banner
from jetshift_core.commands.version import show_version
from jetshift_core.commands.make import make_command
from jetshift_core.commands.migrations.migration import migration_command
from jetshift_core.commands.seeders.seeder import seed_command
from jetshift_core.commands.quicker import quicker_command

# from jetshift_core.commands.job import main as job
# from jetshift_core.commands.listener import main as listener
from jetshift_core.commands.dev import main as dev_main

js_logger = get_logger()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """A command-line interface for JetShift."""
    if ctx.invoked_subcommand is None:
        click.echo(banner())
        click.echo(show_version())

        #  Commands
        click.echo("Commands:")
        commands = ctx.command.list_commands(ctx)
        for command in commands:
            cmd = ctx.command.get_command(ctx, command)
            click.echo(f"  {command:<8} - {cmd.help}")
    else:
        pass


# Register Commands
# cli.add_command(dev_main, name="dev")
cli.add_command(make_command, name="make")
cli.add_command(migration_command, name="migrate")
cli.add_command(seed_command, name="seed")
cli.add_command(quicker_command, name="quick")


# cli.add_command(job, name="job")
# cli.add_command(listener, name="listen")

# Main entry point
def main():
    try:
        cli()
    except Exception as e:
        js_logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
