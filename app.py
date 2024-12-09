from flask import Flask, request, redirect, render_template, flash, session, url_for, send_file, abort
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import mysql.connector
from datetime import datetime
import requests
import boto3
import os
import io

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

# S3 bucket name
BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

# Initialize S3 client
s3_client = boto3.client('s3')


def fetch_static_file(filename):
    """
    Fetches a static file (CSS, JS, Image) from S3 and returns it as a file-like object.
    """
    try:
        # Get the object from S3
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=filename)
        file_content = io.BytesIO(response['Body'].read())
        return file_content, response['ContentType']
    except Exception as e:
        print(f"Error fetching static file '{filename}': {e}")
        return None, None


@app.route('/static/<path:filename>')
def serve_static(filename):
    """
    Serves static files like images, CSS, and JavaScript from the S3 bucket.
    """
    file_content, content_type = fetch_static_file(filename)
    if file_content:
        return send_file(file_content, mimetype=content_type)
    else:
        abort(404, description=f"Static file '{filename}' not found in S3.")

@app.route("/covers", methods=["GET"])
def covers():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query to fetch the image URLs from the books table
        cursor.execute("SELECT url FROM books WHERE url IS NOT NULL AND url != ''")
        covers = cursor.fetchall()

        # Close the connection
        cursor.close()
        conn.close()

        if covers:
            flash(f"Found {len(covers)} book covers.", "success")
        else:
            flash("No book covers found.", "info")
        
        return render_template("covers.html", covers=covers)
    
    except mysql.connector.Error as err:
        flash(f"Database error: {err}", "danger")
        return redirect(url_for("home"))
    except Exception as err:
        flash(f"An unexpected error occurred: {err}", "danger")
        return redirect(url_for("home"))
    
@app.route("/update_books", methods=["POST"])
def update_books():
    try:
        # Database connection
        connection = get_db_connection()
        cursor = connection.cursor()

        # Query to select title and author from books
        query = 'SELECT title, author FROM books;'
        cursor.execute(query)
        books = cursor.fetchall()

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
                print(f"Error fetching data for {book[0]} by {book[1]}: {e}")

        # If there are updates, execute them in the database
        if updates:
            try:
                for update in updates:
                    cursor.execute(update)
                connection.commit()  # Commit the changes to the database
                flash(f"Successfully updated {len(updates)} book entries.", "success")
            except mysql.connector.Error as err:
                print(f"Error executing update: {err}")
                connection.rollback()  # Rollback changes in case of error

        # Close the connection
        cursor.close()
        connection.close()
        return redirect(url_for('covers'))  # Redirect back to the covers page

    except Exception as err:
        flash(f"An unexpected error occurred: {err}", "danger")
        return redirect(url_for('covers'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch user data from the database
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    conn.close()

    # Check if user exists and if the password matches
    if user and check_password_hash(user['password_hash'], password):
        # Store user data in the session
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['is_admin'] = user['is_admin']
        session['first_name'] = user['first_name']  # Store first name

        flash("Login successful!", "success")

        # Redirect based on user role (admin or regular user)
        if user['is_admin']:
            return redirect('/admin')  # Redirect to admin page if admin
        return redirect('/bookstore')  # Redirect to bookstore page if regular user

    flash("Invalid credentials, please try again!", "danger")
    return redirect('/')  # Redirect back to login page

@app.route('/logout')
def logout():
    # Clear the session to log out the user
    session.clear()
    flash("You have been logged out.", "success")
    return redirect('/')  # Redirect to the login page

@app.route('/create_account', methods=['POST'])
def create_account():
    # Fetch form data
    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    phone_number = request.form.get('phone_number')

    # Hash the password
    password_hash = generate_password_hash(password)

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Insert the new user into the database
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, first_name, last_name, phone_number)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (username, email, password_hash, first_name, last_name, phone_number)
        )
        conn.commit()

        # Provide feedback to the user
        flash("Account created successfully! Please log in.", "success")
        return redirect('/')

    except mysql.connector.Error as err:
        # Handle errors, such as duplicate usernames or emails
        flash(f"Error creating account: {err}", "danger")
        return redirect('/')

    finally:
        # Close the database connection
        cursor.close()
        conn.close()

@app.route('/bookstore', methods=['GET', 'POST'])
def bookstore():
    if 'user_id' not in session:  # Ensure the user is logged in
        flash("Please log in to access this page.", "warning")
        return redirect('/')

    first_name = session.get('first_name', 'Guest')

    if request.method == 'POST':
        book_id = request.form.get('book_id')
        if book_id:
            # Get user ID from session
            user_id = session['user_id']

            # Check if the user already has a cart, if not, create one
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT cart_id FROM carts WHERE user_id = %s
            """, (user_id,))
            cart = cursor.fetchone()

            if not cart:  # No existing cart, create one
                cursor.execute("""
                    INSERT INTO carts (user_id) VALUES (%s)
                """, (user_id,))
                conn.commit()
                cart_id = cursor.lastrowid  # Get the newly created cart_id
            else:
                cart_id = cart['cart_id']  # Existing cart

            # Add the book to the cart_items table (or update quantity if book already exists)
            cursor.execute("""
                SELECT quantity FROM cart_items WHERE cart_id = %s AND book_id = %s
            """, (cart_id, book_id))
            existing_item = cursor.fetchone()

            if existing_item:
                # Update quantity if the book already exists in the cart
                cursor.execute("""
                    UPDATE cart_items
                    SET quantity = quantity + 1
                    WHERE cart_id = %s AND book_id = %s
                """, (cart_id, book_id))
            else:
                # Add new book to the cart_items table
                cursor.execute("""
                    INSERT INTO cart_items (cart_id, book_id, quantity)
                    VALUES (%s, %s, 1)
                """, (cart_id, book_id))

            conn.commit()
            conn.close()

            flash("Book added to cart!", "success")
            return redirect(url_for('bookstore'))  # Redirect back to the bookstore

    # Fetch books with their special types and stock quantities
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT b.book_id, b.title, b.author, b.price, b.url, 
               s.special_type, i.stock_quantity, s.discount_percent
        FROM books b
        LEFT JOIN inventory i ON b.book_id = i.book_id
        LEFT JOIN specials s ON b.book_id = s.book_id
    """)
    books_with_inventory_and_specials = cursor.fetchall()
    conn.close()

    # Calculate discounted prices and handle books' availability
    for book in books_with_inventory_and_specials:
        if book['discount_percent']:  # If there is a discount
            discount_decimal = book['discount_percent'] / 100  # Convert to decimal
            book['discounted_price'] = book['price'] * (1 - discount_decimal)
        else:
            book['discounted_price'] = book['price']  # No discount, regular price

        if book['stock_quantity'] is None:
            book['stock_quantity'] = 0
    
    return render_template('bookstore.html', books=books_with_inventory_and_specials, first_name=first_name)

# Function to add a book to the cart (for example, adding to the cart_items table)
def add_to_cart(user_id, book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Insert into cart_items table
    cursor.execute("""
        INSERT INTO cart_items (user_id, book_id)
        VALUES (%s, %s)
    """, (user_id, book_id))
    conn.commit()
    conn.close()


@app.route('/')
def index():
    if 'user_id' in session:  # Check if the user is already logged in
        if session.get('is_admin'):
            return redirect('/admin')
        return redirect('/bookstore')
    
    return render_template('login.html')  # Render the login page

@app.route('/admin')
def admin():
    if 'user_id' not in session or not session.get('is_admin'):  # Ensure the user is logged in and is an admin
        flash("Access denied. Admins only.", "danger")
        return redirect('/')

    # Fetch the first_name from the session
    first_name = session.get('first_name')

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch all contact messages
        cursor.execute("SELECT contact_id, user_id, message, submitted_at FROM contacts")
        contacts = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template('admin.html', first_name=first_name, contacts=contacts)

@app.route('/home')
def home():
    return render_template('bookstore.html')

@app.route('/search', methods=['GET', 'POST'])
def search():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all distinct genres from the books table
    cursor.execute("SELECT DISTINCT genre FROM books WHERE genre IS NOT NULL")
    genres = cursor.fetchall()

    books_with_specials = []
    params = []

    # Handle POST requests for detailed filtering
    if request.method == 'POST':
        # Handling book addition to cart
        book_id_to_add = request.form.get('book_id')  # Get book_id from form to add to cart

        if book_id_to_add and 'user_id' in session:
            user_id = session['user_id']

            # Check if the user already has a cart, if not, create one
            cursor.execute("""
                SELECT cart_id FROM carts WHERE user_id = %s
            """, (user_id,))
            cart = cursor.fetchone()

            if not cart:  # No existing cart, create one
                cursor.execute("""
                    INSERT INTO carts (user_id) VALUES (%s)
                """, (user_id,))
                conn.commit()
                cart_id = cursor.lastrowid  # Get the newly created cart_id
            else:
                cart_id = cart['cart_id']  # Existing cart

            # Check if the book already exists in the cart_items table
            cursor.execute("""
                SELECT quantity FROM cart_items WHERE cart_id = %s AND book_id = %s
            """, (cart_id, book_id_to_add))
            existing_item = cursor.fetchone()

            if existing_item:
                # Update quantity if the book already exists in the cart
                cursor.execute("""
                    UPDATE cart_items
                    SET quantity = quantity + 1
                    WHERE cart_id = %s AND book_id = %s
                """, (cart_id, book_id_to_add))
            else:
                # Add new book to the cart_items table
                cursor.execute("""
                    INSERT INTO cart_items (cart_id, book_id, quantity)
                    VALUES (%s, %s, 1)
                """, (cart_id, book_id_to_add))

            # Update inventory: decrement stock_quantity by 1
            cursor.execute("""
                SELECT stock_quantity FROM inventory WHERE book_id = %s
            """, (book_id_to_add,))
            inventory = cursor.fetchone()

            if inventory and inventory['stock_quantity'] > 0:
                new_stock_quantity = inventory['stock_quantity'] - 1
                cursor.execute("""
                    UPDATE inventory SET stock_quantity = %s WHERE book_id = %s
                """, (new_stock_quantity, book_id_to_add))
                conn.commit()
                flash("Book added to cart!", "success")
            else:
                flash("Sorry, this book is out of stock!", "danger")
            
            return redirect(url_for('search'))  # Redirect back to search results after adding the book

        # Build the query dynamically based on filters
        title = request.form.get('title')
        author = request.form.get('author')
        publisher = request.form.get('publisher')
        genre = request.form.get('genre')
        min_price = request.form.get('min_price')
        max_price = request.form.get('max_price')

        query = """
            SELECT b.book_id, b.title, b.author, b.publisher, b.price, b.genre, b.url,
                   i.stock_quantity, s.discount_percent
            FROM books b
            LEFT JOIN inventory i ON b.book_id = i.book_id
            LEFT JOIN specials s ON b.book_id = s.book_id
            WHERE 1
        """

        # Add conditions for each filter, only if they are not None
        if title:
            query += " AND b.title LIKE %s"
            params.append(f'%{title}%')
        if author:
            query += " AND b.author LIKE %s"
            params.append(f'%{author}%')
        if publisher:
            query += " AND b.publisher LIKE %s"
            params.append(f'%{publisher}%')
        if genre:
            query += " AND b.genre = %s"
            params.append(genre)
        if min_price:
            query += " AND b.price >= %s"
            params.append(min_price)
        if max_price:
            query += " AND b.price <= %s"
            params.append(max_price)

        # Execute the query with the appropriate parameters
        cursor.execute(query, tuple(params))
        books_with_specials = cursor.fetchall()
    else:
        # Handle GET requests for navbar search bar
        search_key = request.args.get('search_key')

        if search_key:
            query = """
                SELECT b.book_id, b.title, b.author, b.publisher, b.price, b.genre, b.url,
                       i.stock_quantity, s.discount_percent
                FROM books b
                LEFT JOIN inventory i ON b.book_id = i.book_id
                LEFT JOIN specials s ON b.book_id = s.book_id
                WHERE b.title LIKE %s
                   OR b.author LIKE %s
                   OR b.publisher LIKE %s
                   OR b.genre LIKE %s
            """
            wildcard_key = f"%{search_key}%"
            params.extend([wildcard_key] * 4)  # Match placeholders for all attributes

            cursor.execute(query, tuple(params))
            books_with_specials = cursor.fetchall()
        else:
            # If no search_key, fetch all books
            cursor.execute("""
                SELECT b.book_id, b.title, b.author, b.publisher, b.price, b.genre, b.url,
                       i.stock_quantity, s.discount_percent
                FROM books b
                LEFT JOIN inventory i ON b.book_id = i.book_id
                LEFT JOIN specials s ON b.book_id = s.book_id
            """)
            books_with_specials = cursor.fetchall()

    # Calculate discounted prices if there are any specials
    for book in books_with_specials:
        if book['discount_percent']:
            discount_decimal = book['discount_percent'] / 100
            book['discounted_price'] = book['price'] * (1 - discount_decimal)
        else:
            book['discounted_price'] = book['price']

    conn.close()

    # Fetch first name from session to greet the user
    first_name = session.get('first_name', 'Guest')

    return render_template('search.html', books=books_with_specials, genres=genres, first_name=first_name)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if 'user_id' not in session:
        flash("Please log in to contact support.", "error")
        return redirect('/')
    
    if request.method == 'POST':
        # Fetch form data
        message = request.form.get('message')
        user_id = session['user_id']
        submitted_at = datetime.now()

        # Save contact request to the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                INSERT INTO contacts (user_id, message, submitted_at)
                VALUES (%s, %s, %s)
                """,
                (user_id, message, submitted_at)
            )
            conn.commit()
            flash("Your message has been submitted successfully!", "success")
        except mysql.connector.Error as err:
            flash(f"Error submitting message: {err}", "danger")
        finally:
            cursor.close()
            conn.close()
        
        return redirect('/contact')
    
    return render_template('contact.html')


@app.route('/respond/<int:contact_id>', methods=['GET', 'POST'])
def respond_to_contact(contact_id):
    # Check if user is logged in and is an admin
    if 'user_id' not in session or not session.get('is_admin'):
        flash("You must be an admin to respond.", "danger")
        return redirect('/')

    # Fetch the contact message by ID
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT contact_id, user_id, message, submitted_at FROM contacts WHERE contact_id = %s", (contact_id,))
        contact = cursor.fetchone()

        if not contact:
            flash("Contact message not found.", "danger")
            return redirect('/admin')

    finally:
        cursor.close()

    if request.method == 'POST':
        response = request.form['response']
        responded_at = datetime.now()

        # Save the admin's response
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                INSERT INTO responses (contact_id, admin_response, responded_at)
                VALUES (%s, %s, %s)
                """,
                (contact_id, response, responded_at)
            )
            conn.commit()
            flash("Response submitted successfully!", "success")
        except mysql.connector.Error as err:
            flash(f"Error responding: {err}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin'))
    
    return render_template('respond.html', contact=contact)

@app.route('/admin/contact')
def admin_contact():
    if 'user_id' not in session or not session.get('is_admin'):
        flash("Access denied. Admins only.", "danger")
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM contacts")
        contacts = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    
    return render_template('admin_contact.html', contacts=contacts)

@app.route('/account', methods=['GET'])
def account():
    if 'user_id' not in session:
        flash("Please log in to access your account.", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch first_name, last_name, email, and phone from the users table
    cursor.execute("SELECT first_name, last_name, email, phone_number FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    # Fetch user's address
    cursor.execute("SELECT * FROM address WHERE user_id = %s", (user_id,))
    address = cursor.fetchone()

    conn.close()
    
    return render_template('account.html', user=user, address=address)

@app.route('/account/order-history', methods=['GET'])
def order_history():
    if 'user_id' not in session:
        flash("Please log in to access your order history.", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the order history for the user
    cursor.execute("""
        SELECT o.order_id, o.order_date, o.status, GROUP_CONCAT(b.title) AS books
        FROM order_history o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN books b ON oi.book_id = b.book_id
        WHERE o.user_id = %s
        GROUP BY o.order_id
        ORDER BY o.order_date DESC
    """, (user_id,))
    order_history = cursor.fetchall()

    cursor.close()
    conn.close()
    
    return render_template('order_history.html', order_history=order_history)

@app.route('/account/reviews', methods=['GET'])
def reviews():
    if 'user_id' not in session:
        flash("Please log in to access your reviews.", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT r.review_id, r.review_text, r.rating, r.review_date, b.title AS title
        FROM reviews r
        JOIN books b ON r.book_id = b.book_id
        WHERE r.user_id = %s
        ORDER BY r.review_date DESC
    """, (user_id,))
    reviews = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('reviews.html', reviews=reviews)

@app.route('/account/contact-messages', methods=['GET'])
def contact_messages():
    if 'user_id' not in session:
        flash("Please log in to access your contact messages.", "error")
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT c.contact_id, c.message, c.submitted_at, r.admin_response, r.responded_at
        FROM contacts c
        LEFT JOIN responses r ON c.contact_id = r.contact_id
        WHERE c.user_id = %s
    """, (user_id,))
    contacts = cursor.fetchall()

    cursor.close()
    conn.close()
    
    return render_template('contact_messages.html', contacts=contacts)

@app.route('/cart')
def cart():
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash("Please log in to view your cart.", "warning")
        return redirect('/')

    user_id = session['user_id']  # Get logged-in user ID

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all cart items for the logged-in user, joining with the carts, books, and specials tables
    cursor.execute("""
        SELECT ci.cart_item_id, ci.quantity, b.book_id, b.title, b.author, b.price, b.url,
               IFNULL(s.discount_percent, 0) AS discount_percent
        FROM cart_items ci
        JOIN carts c ON ci.cart_id = c.cart_id  -- Join with carts table to get the user_id
        JOIN books b ON ci.book_id = b.book_id
        LEFT JOIN specials s ON b.book_id = s.book_id
        WHERE c.user_id = %s  -- Filter by the user_id from the carts table
    """, (user_id,))
    cart_items = cursor.fetchall()
    conn.close()

    # Calculate total price and apply discounts if any
    total_price = 0
    for item in cart_items:
        # Apply discount if available
        if item['discount_percent']:
            discount_decimal = item['discount_percent'] / 100  # Convert to decimal
            discounted_price = item['price'] * (1 - discount_decimal)
            item['discounted_price'] = discounted_price
        else:
            item['discounted_price'] = item['price']  # No discount, regular price

        total_price += item['discounted_price'] * item['quantity']  # Add to total price

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/update_cart', methods=['POST'])
def update_cart():
    item_id = request.form['item_id']
    action = request.form['action']
    
    # Perform the necessary logic based on the action (add or deduct)
    # Use item_id to fetch the cart item and update its quantity
    
    # Example logic to update the cart
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT quantity, cart_id, book_id FROM cart_items WHERE cart_item_id = %s
    """, (item_id,))
    cart_item = cursor.fetchone()

    if not cart_item:
        return redirect(url_for('cart'))  # Handle if cart item doesn't exist

    current_quantity = cart_item['quantity']
    cart_id = cart_item['cart_id']
    book_id = cart_item['book_id']

    cursor.execute("""
        SELECT stock_quantity FROM inventory WHERE book_id = %s
    """, (book_id,))
    inventory = cursor.fetchone()

    if not inventory:
        return redirect(url_for('cart'))  # Handle missing inventory

    current_stock = inventory['stock_quantity']

    if action == 'add' and current_stock > 0:
        new_quantity = current_quantity + 1
        new_stock = current_stock - 1  # Decrease stock
    elif action == 'deduct' and current_quantity > 1:
        new_quantity = current_quantity - 1
        new_stock = current_stock + 1  # Increase stock
    else:
        return redirect(url_for('cart'))  # Invalid action or insufficient stock

    cursor.execute("""
        UPDATE cart_items SET quantity = %s WHERE cart_item_id = %s
    """, (new_quantity, item_id))

    cursor.execute("""
        UPDATE inventory SET stock_quantity = %s WHERE book_id = %s
    """, (new_stock, book_id))

    conn.commit()
    conn.close()

    return redirect(url_for('cart'))

@app.route('/remove_item', methods=['POST'])
def remove_item():
    item_id = request.form['item_id']
    
    # Perform logic to remove the item from the cart
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Ensure the cursor returns dictionaries
    
    cursor.execute("""
        SELECT cart_id, book_id, quantity FROM cart_items WHERE cart_item_id = %s
    """, (item_id,))
    cart_item = cursor.fetchone()

    if not cart_item:
        return redirect(url_for('cart'))  # Handle if cart item doesn't exist

    cart_id = cart_item['cart_id']  # Now cart_item is a dictionary
    book_id = cart_item['book_id']
    quantity = cart_item['quantity']

    # Return stock to inventory
    cursor.execute("""
        SELECT stock_quantity FROM inventory WHERE book_id = %s
    """, (book_id,))
    inventory = cursor.fetchone()

    if inventory:
        new_stock = inventory['stock_quantity'] + quantity
        cursor.execute("""
            UPDATE inventory SET stock_quantity = %s WHERE book_id = %s
        """, (new_stock, book_id))

    cursor.execute("""
        DELETE FROM cart_items WHERE cart_item_id = %s
    """, (item_id,))

    conn.commit()
    conn.close()

    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash("Please log in to complete your purchase.", "error")
        return redirect('/')

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Handle POST request (payment processing)
        address_id = request.form.get('address_id')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        street = request.form.get('street')
        city = request.form.get('city')
        state = request.form.get('state')
        zip_code = request.form.get('zip_code')
        country = request.form.get('country')  # New country field
        payment_method = request.form.get('payment_method', 'Credit Card')  # Default to 'Credit Card'

        # Check if user selected an existing address
        if not address_id:  # Use new address if not selected
            cursor.execute(
                """
                INSERT INTO address (user_id, street_address, city, state, zip_code, country)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, street, city, state, zip_code, country)
            )
            conn.commit()
            address_id = cursor.lastrowid  # Get the newly inserted address ID

        # Fetch the user's cart items with discount check from the specials table
        cursor.execute("""
            SELECT ci.cart_item_id, ci.quantity, b.book_id, b.title, b.price, 
                   COALESCE(
                       CASE 
                           WHEN s.special_type = 'Discount' AND CURDATE() BETWEEN s.special_start_date AND s.special_end_date
                           THEN b.price * (1 - s.discount_percent / 100)
                           ELSE b.price
                       END, b.price) AS final_price
            FROM cart_items ci
            JOIN books b ON ci.book_id = b.book_id
            LEFT JOIN specials s ON b.book_id = s.book_id  -- Join with the specials table to apply discounts
            JOIN carts c ON ci.cart_id = c.cart_id
            WHERE c.user_id = %s
        """, (user_id,))
        cart_items = cursor.fetchall()

        if not cart_items:
            flash("Your cart is empty. Add items to your cart before proceeding.", "warning")
            return redirect('/cart')

        # Calculate total price of cart items
        total_amount = sum(item['final_price'] * item['quantity'] for item in cart_items)

        # Step 1: Insert into order_history (only status, no address_id)
        cursor.execute(
            """
            INSERT INTO order_history (user_id, order_date, status)
            VALUES (%s, NOW(), 'Pending')
            """,
            (user_id,)
        )
        conn.commit()
        order_id = cursor.lastrowid  # Get the newly created order ID

        # Step 2: Insert into order_items
        for item in cart_items:
            cursor.execute(
                """
                INSERT INTO order_items (order_id, book_id, quantity)
                VALUES (%s, %s, %s)
                """,
                (order_id, item['book_id'], item['quantity'])
            )
            conn.commit()

            # Step 3: Update Inventory and Insert into inventory_transactions
            cursor.execute(
                """
                UPDATE inventory
                SET stock_quantity = stock_quantity - %s
                WHERE book_id = %s
                """,
                (item['quantity'], item['book_id'])
            )
            cursor.execute(
                """
                INSERT INTO inventory_transactions (book_id, transaction_type, quantity)
                VALUES (%s, 'Sale', %s)
                """,
                (item['book_id'], item['quantity'])
            )
            conn.commit()

        # Step 4: Insert into payments (store total_amount here)
        cursor.execute(
            """
            INSERT INTO payments (order_id, payment_amount, payment_method, payment_status)
            VALUES (%s, %s, %s, 'Completed')
            """,
            (order_id, total_amount, payment_method)
        )
        conn.commit()

        # Step 5: Empty the user's cart after purchase
        cursor.execute("""
            DELETE FROM cart_items
            WHERE cart_id = (SELECT cart_id FROM carts WHERE user_id = %s)
        """, (user_id,))
        conn.commit()

        cursor.close()
        flash("Order successfully placed! Thank you for shopping with us.", "success")
        return redirect('/order_confirmation')  # Redirect to order confirmation page

    else:
        # Handle the GET request and display the checkout form
        # Fetch saved addresses for the user
        cursor.execute(
            """
            SELECT address_id, CONCAT(street_address, ', ', city, ', ', state, ', ', zip_code, ', ', country) AS full_address
            FROM address
            WHERE user_id = %s
            """, (user_id,)
        )
        saved_addresses = cursor.fetchall()

        # Fetch user's cart items to display in the order review, with discount prices
        cursor.execute("""
            SELECT ci.cart_item_id, ci.quantity, b.book_id, b.title, b.price, 
                   COALESCE(
                       CASE 
                           WHEN s.special_type = 'Discount' AND CURDATE() BETWEEN s.special_start_date AND s.special_end_date
                           THEN b.price * (1 - s.discount_percent / 100)
                           ELSE b.price
                       END, b.price) AS final_price
            FROM cart_items ci
            JOIN books b ON ci.book_id = b.book_id
            LEFT JOIN specials s ON b.book_id = s.book_id  -- Join with the specials table to apply discounts
            JOIN carts c ON ci.cart_id = c.cart_id
            WHERE c.user_id = %s
        """, (user_id,))
        cart_items = cursor.fetchall()

        if not cart_items:
            flash("Your cart is empty. Add items to your cart before proceeding.", "warning")
            return redirect('/cart')

        # Calculate total price of cart items
        total_price = sum(item['final_price'] * item['quantity'] for item in cart_items)

        cursor.close()
        return render_template('checkout.html', saved_addresses=saved_addresses, cart_items=cart_items, total_price=total_price)

@app.route('/order_confirmation')
def order_confirmation():
    if 'user_id' not in session:
        flash("Please log in to view your order confirmation.", "error")
        return redirect('/')

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the latest order for the user
    cursor.execute("""
        SELECT * FROM order_history
        WHERE user_id = %s
        ORDER BY order_date DESC
        LIMIT 1
    """, (user_id,))
    order = cursor.fetchone()

    if not order:
        flash("No order found. Please try again.", "error")
        return redirect('/')

    # Fetch order items
    cursor.execute("""
        SELECT b.title, oi.quantity, b.price, (oi.quantity * b.price) AS total_price
        FROM order_items oi
        JOIN books b ON oi.book_id = b.book_id
        WHERE oi.order_id = %s
    """, (order['order_id'],))
    order_items = cursor.fetchall()

    # Calculate total price
    total_price = sum(item['total_price'] for item in order_items)

    cursor.close()
    return render_template('order_confirmation.html', order=order, order_items=order_items, total_price=total_price)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
