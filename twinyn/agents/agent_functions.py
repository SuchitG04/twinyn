import os
import psycopg2
from autogen.coding.func_with_reqs import with_requirements

@with_requirements(python_packages=["psycopg2"], global_imports=["psycopg2", "os"])
def execute_sql(query: str) -> list:
    """Execute SQL statement and return a list of results. Does NOT print the results."""
    conn = psycopg2.connect(os.getenv("CONNECTION_URL"))
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                query
            )
            res = cursor.fetchall()
    except Exception as e:
        raise e
    else:
        print("TERMINATE")

    return res
