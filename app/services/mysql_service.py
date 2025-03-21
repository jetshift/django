def fetch_mysql_schema(database, table):
    from app.services.database import get_db_connection_url
    from sqlalchemy import create_engine, text

    database_url = get_db_connection_url(database)
    engine = create_engine(database_url, future=True)

    query = text("""
        SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, COLUMN_KEY
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table
        ORDER BY ORDINAL_POSITION;
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {'db': database.database, 'table': table})
        columns = [dict(row._mapping) for row in result]
    return columns
