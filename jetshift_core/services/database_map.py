import re


def map_mysql_to_clickhouse(mysql_type: str, is_nullable: bool = False, precision: int = 18, scale: int = 4) -> str:
    mysql_type = mysql_type.lower()

    # Extract base type and parameters like varchar(191)
    match = re.match(r'(\w+)(\((\d+)(,\s*(\d+))?\))?', mysql_type)
    base = match.group(1) if match else mysql_type
    length = int(match.group(3)) if match and match.group(3) else None
    scale_value = int(match.group(5)) if match and match.group(5) else scale

    ch_type = {
        'int': 'Int32',
        'integer': 'Int32',
        'bigint': 'Int64',
        'smallint': 'Int16',
        'mediumint': 'Int32',
        'tinyint': 'UInt8',
        'bit': 'UInt8',

        'float': 'Float32',
        'double': 'Float64',
        'decimal': f'Decimal({precision}, {scale_value})',

        'varchar': 'String',
        'char': 'String',
        'text': 'String',
        'tinytext': 'String',
        'mediumtext': 'String',
        'longtext': 'String',
        'enum': 'String',
        'json': 'String',

        'datetime': 'DateTime',
        'timestamp': 'DateTime',
        'date': 'Date',
        'time': 'String',  # ClickHouse has no time-only type

        'blob': 'String',
        'binary': 'String',
    }.get(base, 'String')

    return f'Nullable({ch_type})' if is_nullable else ch_type


def map_mysql_to_postgres(mysql_type: str, is_nullable: bool = False, precision: int = 18, scale: int = 4) -> str:
    mysql_type = mysql_type.lower()

    # Extract base type and parameters like varchar(191), decimal(10,2)
    match = re.match(r'(\w+)(\((\d+)(,\s*(\d+))?\))?', mysql_type)
    base = match.group(1) if match else mysql_type
    length = int(match.group(3)) if match and match.group(3) else None
    scale_value = int(match.group(5)) if match and match.group(5) else scale

    pg_type = {
        'int': 'INTEGER',
        'integer': 'INTEGER',
        'bigint': 'BIGINT',
        'smallint': 'SMALLINT',
        'mediumint': 'INTEGER',
        'tinyint': 'SMALLINT',  # Optionally BOOLEAN

        'float': 'REAL',
        'double': 'DOUBLE PRECISION',
        'decimal': f'NUMERIC({precision}, {scale_value})',

        'varchar': f'VARCHAR({length})' if length else 'VARCHAR',
        'char': f'CHAR({length})' if length else 'CHAR',
        'text': 'TEXT',
        'tinytext': 'TEXT',
        'mediumtext': 'TEXT',
        'longtext': 'TEXT',
        'enum': 'TEXT',
        'json': 'JSON',

        'datetime': 'TIMESTAMP',
        'timestamp': 'TIMESTAMP',
        'date': 'DATE',
        'time': 'TIME',

        'blob': 'BYTEA',
        'binary': 'BYTEA',
    }.get(base, 'TEXT')

    return pg_type if is_nullable else f'{pg_type} NOT NULL'
