import streamlit as st
import sqlite3
import pandas as pd
import hashlib

# Initialize database connection
def get_db_connection():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row  # Allows fetching rows as dictionaries
    return conn

# Create tables if they don't exist
def initialize_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'employee'))
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL CHECK(stock >= 0)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            total_price REAL NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

initialize_db()

# User Authentication Functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    return user

def register_user(username, password, role="employee"):  # Default role set to 'employee'
    if role not in ["admin", "employee"]:
        raise ValueError("Invalid role. Allowed roles are 'admin' and 'employee'.")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)", 
                       (username, hash_password(password), role))
        conn.commit()
    except sqlite3.IntegrityError:
        st.sidebar.error("Username already exists. Please choose a different username.")
    finally:
        conn.close()

# Streamlit app configuration
st.set_page_config(page_title="Inventory Management System", layout="wide")


# Sidebar for authentication
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.username = ""


if not st.session_state.logged_in:
    st.sidebar.title("Inventory Management System")
    st.sidebar.subheader("Authentication")
    auth_option = st.sidebar.radio("Select an option", ["Login", "Signup"])

    if auth_option == "Login":
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        login_button = st.sidebar.button("Login")
        st.title("Welcome to Inventory Management System")
        st.write("Use the sidebar to navigate.")
        
        if login_button and username and password:
            user = authenticate_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_role = user["role"]
                st.session_state.username = user["username"]
                st.rerun()
            else:
                st.sidebar.error("Invalid credentials. Try again.")
    
    elif auth_option == "Signup":
        new_username = st.sidebar.text_input("New Username")
        new_password = st.sidebar.text_input("New Password", type="password")
        role = st.sidebar.selectbox("Select Role", ["admin", "employee"])
        signup_button = st.sidebar.button("Signup")
        st.title("Welcome to Inventory Management System")
        st.write("Use the sidebar to navigate.")
        
        if signup_button and new_username and new_password:
            try:
                register_user(new_username, new_password, role)
                st.sidebar.success("Signup successful! You can now log in.")
            except ValueError as e:
                st.sidebar.error(str(e))
        else:
            st.sidebar.error("Please enter a valid username and password.")
else:
    st.sidebar.write(f"Logged in as: {st.session_state.username} ({st.session_state.user_role})")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.username = ""
        st.rerun()
        
# Main content only if logged in
if st.session_state.logged_in:
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Manage Inventory", "Record Sale", "Reports", "Settings"])

    # Home Page
    if page == "Home":
        st.title(f"Welcome {st.session_state.username}!")
        st.write("Overview of Inventory System")
        conn = get_db_connection()
        total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        total_stock = conn.execute("SELECT SUM(stock) FROM products").fetchone()[0] or 0
        conn.close()
        st.metric("Total Products", total_products)
        st.metric("Total Stock", total_stock)

    # Manage Inventory Page
    elif page == "Manage Inventory" and st.session_state.user_role == "admin":
        st.title("Manage Inventory")
        conn = get_db_connection()
        products = pd.read_sql_query("SELECT * FROM products", conn)
        conn.close()
        st.dataframe(products)
        
        # Add New Product
        with st.form("add_product_form"):
            st.subheader("Add New Product")
            name = st.text_input("Product Name")
            description = st.text_area("Description")
            price = st.number_input("Price", min_value=0.0, format="%.2f")
            stock = st.number_input("Stock", min_value=0, step=1)
            submit = st.form_submit_button("Add Product")

            if submit and name:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)",
                               (name, description, price, stock))
                conn.commit()
                conn.close()
                st.success("Product added successfully!")
                st.rerun()
        
        # Delete Product
        st.subheader("Delete Product")
        product_id = st.number_input("Enter Product ID to delete", min_value=1, step=1)
        delete_button = st.button("Delete Product")

        if delete_button:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()
            conn.close()
            st.success("Product deleted successfully!")
            st.rerun()
            
    # Record Sale Page
    elif page == "Record Sale":
        st.title("Record Sale")
        conn = get_db_connection()
        products = pd.read_sql_query("SELECT * FROM products", conn)
        conn.close()
        product_options = {row['id']: row['name'] for _, row in products.iterrows()}
        product_id = st.selectbox("Select Product", options=product_options.keys(), format_func=lambda x: product_options[x])
        quantity = st.number_input("Quantity", min_value=1, step=1)
        submit_sale = st.button("Record Sale")

        if submit_sale:
            conn = get_db_connection()
            cursor = conn.cursor()
            price = conn.execute("SELECT price FROM products WHERE id = ?", (product_id,)).fetchone()[0]
            total_price = price * quantity
            cursor.execute("INSERT INTO sales (product_id, quantity, total_price) VALUES (?, ?, ?)",
                           (product_id, quantity, total_price))
            cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
            conn.commit()
            conn.close()
            st.success("Sale recorded successfully!")
            st.rerun()

    # Reports Page
    elif page == "Reports":
        st.title("Sales Reports")
        conn = get_db_connection()
        sales = pd.read_sql_query("SELECT * FROM sales", conn)
        conn.close()
        st.dataframe(sales)

    # Settings Page
    elif page == "Settings":
        st.title("Settings")
        st.subheader("Change Password")
        new_password = st.text_input("Enter new password", type="password")
        confirm_password = st.text_input("Confirm new password", type="password")
        update_btn = st.button("Update Password")
        
        if update_btn and new_password and confirm_password:
            if new_password == confirm_password:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET password_hash = ? WHERE username = ?", (hash_password(new_password), st.session_state.username))
                conn.commit()
                conn.close()
                st.success("Password updated successfully!")
            else:
                st.error("Passwords do not match!")
