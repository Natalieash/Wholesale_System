import psycopg2

try:
    # Tell Python where the database is and how to log in
    connection = psycopg2.connect(
        host="localhost",
        database="yarn_erp",  # This should match the name you used in pgAdmin
        user="postgres",
        password="nat", # Keep the quotation marks!
        port="5432"
    )
    
    print("SUCCESS! Python is connected to your wholesale database.")
    
    # Close the connection politely
    connection.close()

except Exception as error:
    print("Uh oh, the connection failed. The error is:", error)