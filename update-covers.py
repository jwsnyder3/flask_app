from flask import Flask
from dotenv import load_dotenv
import mysql.connector
import requests
import os

# Load environment variables
load_dotenv()

# Database connection details
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

def update_book_data():
    # Connect to the database
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Query to select title and author from books
        query = 'SELECT title, author FROM books;'
        cursor.execute(query)

        # Fetch all results
        books = cursor.fetchall()
        print(f"Fetched {len(books)} books from the database.")

        # OpenLibrary API base URL
        base_url = "https://openlibrary.org/search.json"
        updates = []

        # Loop through each book and get data from OpenLibrary
        for book in books:
            try:
                # Search for the book in OpenLibrary API
                response = requests.get(base_url, params={"title": book[0], "author": book[1]})
                response.raise_for_status()  # Raise error for bad responses
                data = response.json()

                # If there are results, extract ISBN and cover URL
                if data["docs"]:
                    doc = data["docs"][0]  # Use the first result
                    isbn = doc.get("isbn", [None])[0]
                    cover_id = doc.get("cover_i")

                    if isbn and cover_id:
                        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
                        # Create the SQL update command
                        update_command = (
                            'UPDATE books SET isbn = %s, url = %s WHERE title = %s AND author = %s'
                        )
                        updates.append((isbn, cover_url, book[0], book[1]))
                        print(f"Prepared update for '{book[0]}' by {book[1]} with ISBN {isbn} and cover URL {cover_url}")
            except requests.RequestException as e:
                print(f"Error fetching data for '{book[0]}' by {book[1]}: {e}")

        # If there are updates, execute them in the database
        if updates:
            try:
                for update in updates:
                    cursor.execute(update_command, update)
                connection.commit()  # Commit the changes to the database
                print(f"Successfully updated {len(updates)} book entries.")
            except mysql.connector.Error as err:
                print(f"Error executing updates: {err}")
                connection.rollback()  # Rollback changes in case of error
        else:
            print("No updates to perform.")

    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")

    finally:
        # Close the connection
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()

# Run the book update script
if __name__ == "__main__":
    update_book_data()