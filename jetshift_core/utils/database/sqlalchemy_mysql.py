from sqlalchemy import create_engine, MetaData, Table, Column, String, Float, DECIMAL, DateTime, func
from sqlalchemy.exc import SQLAlchemyError

# Initialize the SQLAlchemy metadata
metadata = MetaData()


def get_engine():
    from jetshift_core.helpers.common import jprint
    try:
        host, user, password, database = ()

        engine = create_engine(f'mysql+pymysql://{user}:{password}@{host}/{database}')
        return engine
    except SQLAlchemyError as e:
        jprint(f"MySQL SQLAlchemy error occurred: {e}", 'error')
    except Exception as e:
        jprint(f"An unexpected error occurred: {e}", 'error')
