import psycopg2
import psycopg2.extras

database_session = psycopg2.connect(
    database='postgres',
    port=5432,
    host='localhost',
    user='postgres',
    password='nancy1234'
)
cursor = database_session.cursor(cursor_factory=psycopg2.extras.DictCursor)
