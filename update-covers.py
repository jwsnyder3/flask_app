import mysql.connector
import requests

# Database connection details
connection = mysql.connector.connect(
    host="localhost",  # Database host (usually localhost)
    user="jwsnyder",  # Your MySQL username
    password="246857913",  # Your MySQL password
    database="bookstore"
)

cursor = connection.cursor()

# Query to select title and author from books
query = 'SELECT title, author FROM books;'
cursor.execute(query)

# Fetch all results
books = cursor.fetchall()

# Check the fetched data (for debugging)
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
                update_command = f'UPDATE books SET isbn = "{isbn}", url = "{cover_url}" ' \
                                 f'WHERE title = "{book[0]}" AND author = "{book[1]}";'
                updates.append(update_command)
                print(f"Added update for {book[0]} by {book[1]} with ISBN {isbn} and cover URL {cover_url}")
    except (requests.RequestException, KeyError) as e:
        #print(f"Error fetching data for {book[0]} by {book[1]}: {e}")

# If there are updates, execute them in the database
if updates:
    try:
        for update in updates:
            cursor.execute(update)
        connection.commit()  # Commit the changes to the database
        print(f"Successfully updated {len(updates)} book entries.")
    except mysql.connector.Error as err:
        print(f"Error executing update: {err}")
        connection.rollback()  # Rollback changes in case of error

# Close the connection
cursor.close()
connection.close()

