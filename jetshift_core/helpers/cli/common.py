def read_database_from_id(database, field=None):
    from jetshift_core.utils.init_django import setup_django
    setup_django()
    from app.models import JSDatabase
    from jetshift_core.helpers.database import get_db_connection_url
    db = JSDatabase.objects.filter(id=database).first()

    if field == 'connection_url':
        return get_db_connection_url(db)

    if field is not None:
        return getattr(db, field, None)

    return db


def read_database_from_yml_file(database, field=None):
    import yaml
    import os
    app_path = os.environ.get('APP_PATH', '')
    database_path = f'{app_path}play/databases.yml'
    with open(database_path, 'r') as file:
        config = yaml.safe_load(file)

    db = config.get(database)

    if field is not None:
        field_value = db.get(field) if db else None
        return field_value

    return db


def find_database_dialect(database):
    # Check integer in string
    if isinstance(database, str) and database.isdigit():
        database = int(database)

    # Find dialect
    if isinstance(database, str):
        dialect = read_database_from_yml_file(database, 'dialect')
    elif isinstance(database, int):
        dialect = read_database_from_id(database, 'dialect')
    else:
        dialect = None

    return dialect


def create_table(database, table, fresh=False, drop=False):
    from jetshift_core.helpers.common import jprint
    from sqlalchemy import create_engine
    from sqlalchemy.exc import SQLAlchemyError

    metadata = table.metadata  # Use table's own metadata

    # Get connection URL
    if isinstance(database, int):
        database_url = read_database_from_id(database, 'connection_url')
    else:
        database_url = read_database_from_yml_file(database, 'connection_url')

    engine = create_engine(database_url, future=True)

    # Drop table if required
    if fresh or drop:
        try:
            table.drop(engine, checkfirst=True)
        except Exception as e:
            jprint(f"Failed to drop table '{table.name}': {e}", 'error')

    # Create table
    if engine and not drop:
        try:
            metadata.create_all(engine)
            print(f"Created table: {table.name}")
        except SQLAlchemyError as e:
            jprint(f"SQLAlchemy error during table '{table.name}' creation: {e}", 'error')
        except Exception as e:
            jprint(f"Unexpected error during table '{table.name}' creation: {e}", 'error')
