import streamlit as st
import sqlite3
import pandas as pd

# Initialize database connection
def get_db_connection():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row  # Allows fetching rows as dictionaries
    return conn

# Streamlit app configuration
st.set_page_config(page_title="Inventory Management System", layout="wide")
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Manage Inventory", "Reports", "Settings"])

# Home Page
if page == "Home":
    st.title("Welcome to Inventory Management System")
    st.write("Use the sidebar to navigate.")

# Manage Inventory Page
elif page == "Manage Inventory":
    st.title("Manage Inventory")
    
    # Database connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Form to Add Product
    with st.form("add_product_form"):
        st.subheader("Add New Product")
        name = st.text_input("Product Name")
        description = st.text_area("Description")
        price = st.number_input("Price", min_value=0.01, format="%.2f")
        stock = st.number_input("Stock Quantity", min_value=1, format="%d")
        submit = st.form_submit_button("Add Product")
        
        if submit and name and price and stock:
            cursor.execute("INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)", (name, description, price, stock))
            conn.commit()
            st.success(f"Product '{name}' added successfully!")
    
    # Filtering Options
    st.subheader("Filter Inventory")
    search_query = st.text_input("Search by Product Name")
    filter_stock = st.checkbox("Show Low Stock Items (Stock < 10)")
    
    query = "SELECT * FROM products"
    conditions = []
    params = []
    
    if search_query:
        conditions.append("name LIKE ?")
        params.append(f"%{search_query}%")
    
    if filter_stock:
        conditions.append("stock < 10")
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    df = pd.read_sql_query(query, conn, params=params)
    st.dataframe(df)
    
    # Edit a Product
    product_ids = df["id"].tolist() if not df.empty else []
    if product_ids:
        edit_id = st.selectbox("Select Product to Edit", product_ids)
        if edit_id:
            cursor.execute("SELECT * FROM products WHERE id = ?", (edit_id,))
            product = cursor.fetchone()
            
            if product:
                new_name = st.text_input("Product Name", product["name"])
                new_description = st.text_area("Description", product["description"])
                new_price = st.number_input("Price", min_value=0.01, value=product["price"], format="%.2f")
                new_stock = st.number_input("Stock Quantity", min_value=1, value=product["stock"], format="%d")
                
                if st.button("Update Product"):
                    cursor.execute("UPDATE products SET name = ?, description = ?, price = ?, stock = ? WHERE id = ?", (new_name, new_description, new_price, new_stock, edit_id))
                    conn.commit()
                    st.success("Product updated successfully!")
                    st.experimental_rerun()
    
    # Delete a Product
    if product_ids:
        delete_id = st.selectbox("Select Product to Delete", product_ids)
        if delete_id and st.button("Delete Product"):
            cursor.execute("DELETE FROM products WHERE id = ?", (delete_id,))
            conn.commit()
            st.success("Product deleted successfully!")
            st.experimental_rerun()
    
    conn.close()

# Reports Page
elif page == "Reports":
    st.title("Inventory Reports")
    
    conn = get_db_connection()
    df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
    df_products = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    
    st.subheader("Sales Summary")
    st.dataframe(df_sales)
    
    st.subheader("Stock Report")
    st.dataframe(df_products[["name", "stock"]])

# Settings Page
elif page == "Settings":
    st.title("Settings")
    st.write("User management and preferences.")
