from db_config import get_db_connection

connection = None

try:
    connection = get_db_connection()

    if connection.is_connected():
        print("Successfully connected to Project Kashi database!")

except Exception as error:
    print("Database connection failed.")
    print("Error:", error)

finally:
    if connection is not None and connection.is_connected():
        connection.close()
        print("Database connection closed.")
