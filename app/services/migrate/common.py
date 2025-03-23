def migrate_supported_pairs(source, target, check=False):
    supported_pairs = [
        {
            'source': {'title': 'MySQL', 'dialect': 'mysql'},
            'target': {'title': 'ClickHouse', 'dialect': 'clickhouse'},
            'task_path': 'jetshift_core.tasks.mysql_clickhouse_insert.MysqlToClickhouse'
        },
        {
            'source': {'title': 'PostgreSQL', 'dialect': 'postgresql'},
            'target': {'title': 'ClickHouse', 'dialect': 'clickhouse'},
            'task_path': 'jetshift_core.tasks.postgres_clickhouse_insert.PostgreToClickhouse'
        },
        {
            'source': {'title': 'SQLite', 'dialect': 'sqlite'},
            'target': {'title': 'ClickHouse', 'dialect': 'clickhouse'},
            'task_path': 'jetshift_core.tasks.sqlite_clickhouse_insert.SqliteToClickhouse'
        },
    ]

    if not check:
        return supported_pairs

    # Check if the given source and target match any pair
    for pair in supported_pairs:
        if pair['source']['dialect'] == source and pair['target']['dialect'] == target:
            success = True
            message = f"The pair '{source} -> {target}' is supported by JetShift"
            return success, message, pair['task_path']

    success = False
    message = f"Unsupported migration pair: {source} -> {target}"
    return success, message, None
