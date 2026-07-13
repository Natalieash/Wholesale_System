import streamlit as st
import psycopg2
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
st.set_page_config(layout="wide")

# 1. Database Connection Helper
def get_connection():
    return psycopg2.connect(
        host="localhost", database="yarn_erp", user="postgres",
        password="nat", port="5432"
    )

# 2. Setup Session Memory
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = ""
    st.session_state["username"] = ""

# ==========================================
# LOGIN SCREEN (If not logged in)
# ==========================================
if not st.session_state["logged_in"]:
    st.title("🔒 System Login")
    
    with st.form("login_form"):
        input_user = st.text_input("Username")
        input_pass = st.text_input("Password", type="password") # Hides typing with stars
        login_btn = st.form_submit_button("Login")
        
        if login_btn:
            conn = get_connection()
            cur = conn.cursor()
            
            # Check the database for a match
            cur.execute("SELECT role FROM system_users WHERE username = %s AND password = %s", (input_user, input_pass))
            user_data = cur.fetchone()
            
            if user_data:
                # Success! Save the role to memory and refresh the page
                st.session_state["logged_in"] = True
                st.session_state["username"] = input_user
                st.session_state["role"] = user_data[0] # Will be 'Owner' or 'Employee'
                st.rerun() # Instantly reloads the page to show the dashboard
            else:
                st.error("Incorrect username or password.")
                
            cur.close()
            conn.close()

# ==========================================
# SECURE DASHBOARD (If logged in)
# ==========================================
else:
    import datetime

    # --- GLOBAL DATE FILTER (Sidebar) ---
    # Moved here so it ONLY shows after logging in!
    st.sidebar.header("📅 Time Filter")
    today = datetime.date.today()
    first_day_of_month = today.replace(day=1)
    start_date = st.sidebar.date_input("Start Date", first_day_of_month)
    end_date = st.sidebar.date_input("End Date", today)

    # Header with a Logout Button
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title(f"🧶 Wholesale ERP Dashboard")
        st.caption(f"Logged in as: {st.session_state['username']} ({st.session_state['role']})")
    with col2:
        if st.button("Logout"):
            st.session_state["logged_in"] = False
            st.session_state["role"] = ""
            st.session_state["username"] = ""
            st.rerun()

    st.divider()

    # --- IF THE USER IS AN OWNER ---
    if st.session_state["role"] == "Owner":
        # The updated 7-tab list including HR
        # The updated 8-tab list
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "📦 Manage Inventory", 
            "💰 Log a Sale", 
            "👥 HR Management", 
            "📊 View Ledger", 
            "📑 Financial Statements", 
            "📈 Analytics",
            "🇪🇬 Tax Center",
            "🚚 Suppliers & Logistics" # <-- NEW TAB
        ])
        # (Keep your existing tab1 and tab2 code here...)

      # OWNER TAB 1: INVENTORY & EDITS
        with tab1:
            st.header("📦 Manage Inventory")
            
            # --- 1. RECEIVE INVENTORY ---
            with st.expander("➕ Receive New Product", expanded=True):
                st.write("Log incoming inventory from the factory and categorize it.")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    prod_id = st.text_input("Product ID / Code (e.g., YRN-01, ZP-05)")
                    prod_name = st.text_input("Product Name")
                    # NEW: Category Selection
                    category = st.selectbox("Category", ["Yarn", "Beads", "Zippers", "Fabric", "Other"])
                with c2:
                    unit_price = st.number_input("Cost per Selling Unit (EGP)", min_value=0.0, step=10.0)
                    # NEW: Expanded Unit Types for Fabric and Hardware
                    unit_type = st.selectbox("Base Selling Unit", ["Kilo", "Cone", "Box", "Meter", "Piece", "Pack"])
                    purchase_unit = st.selectbox("Purchased As", ["Kilo", "Cone", "Box", "Meter", "Piece", "Pack", "Pallet", "Ton", "Roll"])
                with c3:
                    purchase_qty = st.number_input(f"Quantity Purchased", min_value=0.0, step=1.0)
                    if purchase_unit == unit_type:
                        conv_factor = 1.0
                        st.info("No conversion needed.")
                    else:
                        conv_factor = st.number_input(f"How many {unit_type}s in 1 {purchase_unit}?", min_value=1.0, value=1.0, step=1.0)
                        st.warning(f"1 {purchase_unit} = {conv_factor} {unit_type}s")

                base_qty_to_stock = purchase_qty * conv_factor
                total_value = unit_price * base_qty_to_stock
                
                st.info(f"**Adding to Shelf:** {base_qty_to_stock:,.0f} {unit_type}s | **Total Value:** {total_value:,.2f} EGP")

                if st.button("Save to Inventory"):
                    if prod_id and prod_name:
                        conn = get_connection()
                        cur = conn.cursor()
                        try:
                            # We now insert the category into the database
                            cur.execute("""
                                INSERT INTO inventory_stock 
                                (product_id, product_name, category, unit_type, purchase_unit, conversion_factor, unit_price, stock_quantity, total_value) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (prod_id, prod_name, category, unit_type, purchase_unit, conv_factor, unit_price, base_qty_to_stock, total_value))
                            conn.commit()
                            st.success(f"Added {base_qty_to_stock} {unit_type}s of {prod_name} to {category} stock!")
                            time.sleep(1.5)
                            st.rerun()
                        except:
                            st.error("Error: Product ID might already exist.")
                        conn.close()

            # --- 2. VIEW CURRENT INVENTORY ---
            st.divider()
            st.subheader("Current Stock")
            
            # NEW: The Category Filter Buttons
            category_filter = st.radio(
                "Filter by Category:", 
                ["All", "Yarn", "Beads", "Zippers", "Fabric", "Other"], 
                horizontal=True
            )
            
            conn = get_connection()
            try:
                # The query changes dynamically based on what button you click!
                if category_filter == "All":
                    query_inv = """
                    SELECT product_id as "ID", product_name as "Name", category as "Category", 
                           unit_type as "Unit", unit_price as "Price (EGP)", 
                           stock_quantity as "Qty", total_value as "Total Value" 
                    FROM inventory_stock ORDER BY category, product_id
                    """
                    df_inv = pd.read_sql(query_inv, conn)
                else:
                    query_inv = """
                    SELECT product_id as "ID", product_name as "Name", category as "Category", 
                           unit_type as "Unit", unit_price as "Price (EGP)", 
                           stock_quantity as "Qty", total_value as "Total Value" 
                    FROM inventory_stock WHERE category = %s ORDER BY product_id
                    """
                    df_inv = pd.read_sql(query_inv, conn, params=(category_filter,))
                    
                if not df_inv.empty:
                    st.dataframe(df_inv, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No stock found in the '{category_filter}' category.")
            except Exception as e:
                pass

            # --- 3. INLINE EDIT BUTTON ---
            with st.expander("✏️ Edit a Product Mistake"):
                cur = conn.cursor()
                cur.execute("SELECT product_id, product_name, category, unit_type, unit_price, stock_quantity FROM inventory_stock")
                all_items = cur.fetchall()
                
                if all_items:
                    edit_options = {f"{item[0]} - {item[1]}": item for item in all_items}
                    sel_item = st.selectbox("Select product to fix:", list(edit_options.keys()))
                    
                    old_id, old_name, old_cat, old_unit, old_price, old_qty = edit_options[sel_item]
                    
                    with st.form("edit_product_form"):
                        st.write("Type the correct information below:")
                        e_col1, e_col2, e_col3 = st.columns(3)
                        with e_col1:
                            new_id = st.text_input("Product ID", value=old_id)
                            new_name = st.text_input("Name", value=old_name)
                        with e_col2:
                            # Try to match the existing category, otherwise default to Yarn
                            cat_list = ["Yarn", "Beads", "Zippers", "Fabric", "Other"]
                            cat_idx = cat_list.index(old_cat) if old_cat in cat_list else 0
                            new_cat = st.selectbox("Category", cat_list, index=cat_idx)
                            
                            unit_list = ["Kilo", "Cone", "Box", "Meter", "Piece", "Pack"]
                            unit_idx = unit_list.index(old_unit) if old_unit in unit_list else 0
                            new_unit = st.selectbox("Measurement", unit_list, index=unit_idx)
                        with e_col3:
                            new_price = st.number_input("Unit Price", value=float(old_price), step=1.0)
                            new_qty = st.number_input("Quantity in Stock", value=float(old_qty), step=1.0)
                            
                        if st.form_submit_button("Apply Corrections"):
                            new_total = new_price * new_qty
                            cur.execute("""
                                UPDATE inventory_stock 
                                SET product_id = %s, product_name = %s, category = %s, unit_type = %s, unit_price = %s, stock_quantity = %s, total_value = %s
                                WHERE product_id = %s
                            """, (new_id, new_name, new_cat, new_unit, new_price, new_qty, new_total, old_id))
                            conn.commit()
                            st.success("✅ Product updated! Refreshing...")
                            time.sleep(1.5)
                            st.rerun()
                cur.close()
            conn.close()

        # OWNER TAB 2: SALES & HISTORY
        with tab2:
            st.header("Record a Wholesale Transaction")
            
            conn = get_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT product_id, product_name, unit_price, stock_quantity FROM inventory_stock WHERE stock_quantity > 0")
            available_products = cur.fetchall()
            
            if not available_products:
                st.warning("No inventory available to sell! Please add inventory first.")
            else:
                product_options = {f"{p[0]} | {p[1]} (Stock: {p[3]})": p for p in available_products}
                
                # We removed the st.form here so it updates live as you type!
                selected_prod_label = st.selectbox("Select Product to Sell", list(product_options.keys()), key="owner_sale_prod")
                
                col_q, col_p = st.columns(2)
                with col_q:
                    qty_sold = st.number_input("Quantity to Sell", min_value=1.0, step=1.0, key="owner_sale_qty")
                with col_p:
                    # New Input: Price Per Unit
                    unit_sell_price = st.number_input("Selling Price per Unit (EGP)", min_value=0.0, step=10.0, key="owner_sale_price")
                
                # LIVE CALCULATOR
                sale_amount = qty_sold * unit_sell_price
                st.info(f"### Total Invoice Amount: {sale_amount:,.2f} EGP")
                
                if st.button("Record Sale", type="primary", key="owner_record_btn"):
                    if sale_amount == 0:
                        st.error("Selling price cannot be zero!")
                    else:
                        prod_data = product_options[selected_prod_label]
                        p_id, p_name, p_cost_price, p_stock = prod_data[0], prod_data[1], prod_data[2], prod_data[3]
                        
                        if qty_sold > p_stock:
                            st.error(f"Not enough stock! You only have {p_stock} available.")
                        else:
                            # The system calculates your profit margins automatically
                            cogs = float(qty_sold) * float(p_cost_price) 
                            vat_amount = float(sale_amount) * 0.14
                            total_cash = float(sale_amount) + vat_amount
                            desc = f"Sold {qty_sold} of {p_id} ({p_name}) @ {unit_sell_price}/unit"
                            
                            try:
                                cur.execute("UPDATE inventory_stock SET stock_quantity = stock_quantity - %s, total_value = total_value - %s WHERE product_id = %s", (qty_sold, cogs, p_id))
                                cur.execute("INSERT INTO general_ledger (account_id, debit, description) VALUES (1000, %s, %s)", (total_cash, desc))
                                cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (4000, %s, %s)", (sale_amount, desc))
                                cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (2200, %s, %s)", (vat_amount, desc))
                                cur.execute("INSERT INTO general_ledger (account_id, debit, description) VALUES (5000, %s, %s)", (cogs, desc))
                                cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (1200, %s, %s)", (cogs, desc))
                                
                                conn.commit()
                                st.success(f"✅ Sale logged! Deducted {qty_sold} from stock.")
                                time.sleep(1.5)
                                st.rerun()
                               
                                
                            except Exception as e:
                                st.error(f"Error logging sale: {e}")
                                conn.rollback()
            cur.close()

            # --- RECENT SALES HISTORY TABLE & EDIT ---
            st.divider()
            st.subheader("Recent Sales History")
            try:
                query_sales = """
                SELECT DATE(transaction_date) as "Date", description as "Transaction Details", credit as "Revenue (EGP)"
                FROM general_ledger 
                WHERE account_id = 4000
                ORDER BY transaction_date DESC LIMIT 20
                """
                df_sales = pd.read_sql(query_sales, conn)
                
                if not df_sales.empty:
                    st.dataframe(df_sales, use_container_width=True, hide_index=True)
                else:
                    st.info("No sales transactions logged yet.")
                    
                with st.expander("✏️ Fix a Mistaken Sale (Undo)"):
                    cur = conn.cursor()
                    cur.execute("SELECT description, credit FROM general_ledger WHERE account_id = 4000 ORDER BY transaction_date DESC LIMIT 20")
                    recent_sales = cur.fetchall()
                    
                    if recent_sales:
                        sale_options = {f"{s[0]} | Revenue: {s[1]} EGP": s[0] for s in recent_sales}
                        sale_to_delete = st.selectbox("Select the wrong sale to undo:", list(sale_options.keys()))
                        
                        if st.button("🚨 Undo this Sale"):
                            desc_to_undo = sale_options[sale_to_delete]
                            cur.execute("DELETE FROM general_ledger WHERE description = %s", (desc_to_undo,))
                            
                            import re
                            match = re.search(r"Sold (\d+\.?\d*) of (\S+)", desc_to_undo)
                            if match:
                                qty_to_return = float(match.group(1))
                                p_id_to_return = match.group(2)
                                cur.execute("SELECT unit_price FROM inventory_stock WHERE product_id = %s", (p_id_to_return,))
                                price_row = cur.fetchone()
                                if price_row:
                                    cogs_returned = qty_to_return * price_row[0]
                                    cur.execute("UPDATE inventory_stock SET stock_quantity = stock_quantity + %s, total_value = total_value + %s WHERE product_id = %s", (qty_to_return, cogs_returned, p_id_to_return))
                            
                            conn.commit()
                            st.success("✅ Sale reversed! Inventory has been restored. Refresh the page.")
                            time.sleep(1.5)
                            st.rerun()
                    cur.close()
            except Exception as e:
                pass
            conn.close()

        # OWNER TAB 3: HUMAN RESOURCES MANAGEMENT
        with tab3:
            st.header("👥 Human Resources & Payroll")
            
            conn = get_connection()
            cur = conn.cursor()
            
            # --- AUTO-CREATE THE DATABASE TABLE ---
            # This safely creates the HR table if it doesn't exist yet!
            cur.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    employee_id SERIAL PRIMARY KEY,
                    full_name VARCHAR(100) NOT NULL,
                    job_title VARCHAR(50),
                    phone_number VARCHAR(20),
                    base_salary NUMERIC DEFAULT 0,
                    hire_date DATE DEFAULT CURRENT_DATE
                )
            """)
            conn.commit()

            # --- 1. HIRE A NEW EMPLOYEE ---
            with st.expander("➕ Hire / Add New Employee", expanded=False):
                with st.form("add_employee_form"):
                    c_name, c_role = st.columns(2)
                    with c_name:
                        emp_name = st.text_input("Full Name")
                        emp_phone = st.text_input("Phone Number")
                    with c_role:
                        emp_role = st.selectbox("Job Title", ["Sales Representative", "Warehouse Staff", "Driver", "Manager", "Accountant", "Other"])
                        emp_salary = st.number_input("Monthly Base Salary (EGP)", min_value=0.0, step=500.0)
                    
                    if st.form_submit_button("Add Employee to System"):
                        if emp_name:
                            try:
                                cur.execute("""
                                    INSERT INTO employees (full_name, job_title, phone_number, base_salary)
                                    VALUES (%s, %s, %s, %s)
                                """, (emp_name, emp_role, emp_phone, emp_salary))
                                conn.commit()
                                st.success(f"✅ {emp_name} added to the team!")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error saving employee: {e}")
                                conn.rollback()
                        else:
                            st.error("Employee Name is required.")

            # --- 2. STAFF ROSTER ---
            st.divider()
            st.subheader("Current Staff Directory")
            try:
                df_employees = pd.read_sql("""
                    SELECT employee_id as "ID", full_name as "Name", job_title as "Role", 
                           phone_number as "Phone", base_salary as "Salary (EGP)", hire_date as "Hired On"
                    FROM employees ORDER BY employee_id
                """, conn)
                
                if not df_employees.empty:
                    st.dataframe(df_employees, use_container_width=True, hide_index=True)
                else:
                    st.info("No employees added to the system yet.")
            except Exception as e:
                pass

            # --- 3. RUN PAYROLL (INTEGRATED WITH ACCOUNTING) ---
            st.divider()
            with st.expander("💸 Run Payroll (Issue Salaries)", expanded=False):
                st.write("Issue a salary payment. This will automatically deduct cash and log a Payroll Expense on your Income Statement.")
                
                cur.execute("SELECT employee_id, full_name, base_salary FROM employees")
                staff_list = cur.fetchall()
                
                if staff_list:
                    staff_options = {f"{s[1]} (Role/ID: {s[0]}) - Base: {s[2]:,.2f} EGP": s for s in staff_list}
                    
                    with st.form("payroll_form"):
                        selected_staff = st.selectbox("Select Employee to Pay", list(staff_options.keys()))
                        pay_data = staff_options[selected_staff]
                        s_id, s_name, s_base = pay_data[0], pay_data[1], pay_data[2]
                        
                        pay_amount = st.number_input("Amount to Pay (EGP)", value=float(s_base), step=100.0)
                        pay_memo = st.text_input("Memo / Description", value=f"Salary payment for {s_name}")
                        
                        if st.form_submit_button("Issue Payment", type="primary"):
                            if pay_amount > 0:
                                try:
                                    # Ensure the Payroll account (5200) exists
                                    cur.execute("SELECT account_id FROM chart_of_accounts WHERE account_id = 5200")
                                    if not cur.fetchone():
                                        cur.execute("INSERT INTO chart_of_accounts (account_id, account_name, account_type) VALUES (5200, 'Payroll & Benefits', 'Expense')")
                                    
                                    # Write to the general ledger (Credit Cash 1000, Debit Payroll 5200)
                                    cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (1000, %s, %s)", (pay_amount, pay_memo))
                                    cur.execute("INSERT INTO general_ledger (account_id, debit, description) VALUES (5200, %s, %s)", (pay_amount, pay_memo))
                                    conn.commit()
                                    
                                    st.success(f"✅ Payroll of {pay_amount:,.2f} EGP issued to {s_name}!")
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Database error: {e}")
                                    conn.rollback()
                            else:
                                st.error("Payment amount must be greater than zero.")
                else:
                    st.warning("Please add employees before running payroll.")
            
            cur.close()
            conn.close()
        # OWNER TAB 4: LEDGER
        with tab4:
            st.header("System Records")
            st.caption(f"Showing transactions from {start_date} to {end_date}")
            
            conn = get_connection()
            try:
                # The SQL filters by your Start and End dates
                query_ledger = """
                SELECT * FROM general_ledger 
                WHERE DATE(transaction_date) >= %s AND DATE(transaction_date) <= %s
                ORDER BY transaction_date DESC, entry_id DESC;
                """
                df_ledger = pd.read_sql(query_ledger, conn, params=(start_date, end_date))
                
                if not df_ledger.empty:
                    st.dataframe(df_ledger, use_container_width=True, hide_index=True)
                else:
                    st.info("No ledger entries found for these dates.")
            except Exception as e:
                st.write("Error loading ledger:", e)
            conn.close()

        # OWNER TAB 5: CONSOLIDATED FINANCIAL STATEMENTS
        with tab5:
            st.header("📑 Financial Statements")
            
            # --- SUB-NAVIGATION MENU ---
            statement_view = st.radio(
                "Select Report to View:", 
                ["Income Statement (P&L)", "Cash Flow Statement", "Balance Sheet"], 
                horizontal=True
            )
            st.divider()
            
            conn = get_connection()
            
            # ==========================================
            # 1. INCOME STATEMENT VIEW
            # ==========================================
            if statement_view == "Income Statement (P&L)":
                st.subheader("Income Statement")
                st.caption(f"Showing performance from {start_date} to {end_date}")
                
                query_is = """
                SELECT c.account_name, c.account_type, 
                       COALESCE(SUM(g.debit), 0) as total_debit, 
                       COALESCE(SUM(g.credit), 0) as total_credit
                FROM chart_of_accounts c
                JOIN general_ledger g ON c.account_id = g.account_id
                WHERE c.account_type IN ('Revenue', 'Expense')
                AND DATE(g.transaction_date) >= %s 
                AND DATE(g.transaction_date) <= %s
                GROUP BY c.account_name, c.account_type
                """
                try:
                    df_is = pd.read_sql(query_is, conn, params=(start_date, end_date))
                    revenue_list, expense_list = [], []
                    total_revenue, total_expenses = 0.0, 0.0
                    
                    for index, row in df_is.iterrows():
                        name = row['account_name']
                        if row['account_type'] == 'Revenue':
                            balance = row['total_credit'] - row['total_debit']
                            revenue_list.append({"Account": name, "Balance": balance})
                            total_revenue += balance
                        elif row['account_type'] == 'Expense':
                            balance = row['total_debit'] - row['total_credit']
                            expense_list.append({"Account": name, "Balance": balance})
                            total_expenses += balance
                    
                    net_income = total_revenue - total_expenses
                    
                    st.write("### REVENUE")
                    if revenue_list: st.dataframe(pd.DataFrame(revenue_list), use_container_width=True, hide_index=True)
                    st.success(f"**Total Revenue: {total_revenue:,.2f} EGP**")
                    
                    st.write("### EXPENSES (COGS)")
                    if expense_list: st.dataframe(pd.DataFrame(expense_list), use_container_width=True, hide_index=True)
                    st.warning(f"**Total Expenses: {total_expenses:,.2f} EGP**")
                    
                    st.divider()
                    if net_income >= 0:
                        st.info(f"### 🎯 NET INCOME: {net_income:,.2f} EGP")
                    else:
                        st.error(f"### 🔻 NET LOSS: {net_income:,.2f} EGP")
                except Exception as e:
                    st.write("Error:", e)

            # ==========================================
            # 2. CASH FLOW VIEW & EXPENSE ENTRY
            # ==========================================
            elif statement_view == "Cash Flow Statement":
                st.subheader("Statement of Cash Flows (EGP)")
                
                # --- NEW: INTEGRATED EXPENSE FORM ---
                with st.expander("💳 Record New Cash Outflow (Expenses & Assets)", expanded=False):
                    outflow_categories = {
                        "Rent & Facilities": {"type": "Expense", "id": 5100},
                        "Payroll & Benefits": {"type": "Expense", "id": 5200},
                        "Utilities (Electricity, Internet)": {"type": "Expense", "id": 5300},
                        "Taxes Paid to ETA": {"type": "Expense", "id": 5400},
                        "Logistics & Shipping": {"type": "Expense", "id": 5500},
                        "Other Overhead / Supplier Payment": {"type": "Expense", "id": 5900},
                        "Purchase: Real Estate / Property": {"type": "Asset", "id": 1500},
                        "Purchase: Machinery & Equipment": {"type": "Asset", "id": 1600},
                        "Purchase: Company Vehicles": {"type": "Asset", "id": 1700}
                    }

                    with st.form("outflow_form"):
                        c_cat, c_amt = st.columns([2, 1])
                        with c_cat:
                            selected_category = st.selectbox("Category", list(outflow_categories.keys()))
                            description = st.text_input("Description / Memo", placeholder="e.g., May Rent, Bought new delivery truck...")
                        with c_amt:
                            amount = st.number_input("Amount Paid (EGP)", min_value=0.0, step=100.0)
                        
                        if st.form_submit_button("Record Payment", type="primary"):
                            if amount <= 0 or not description:
                                st.error("Please provide a valid amount and description.")
                            else:
                                cur = conn.cursor()
                                try:
                                    acc_rules = outflow_categories[selected_category]
                                    acc_id = acc_rules["id"]
                                    acc_type = acc_rules["type"]
                                    acc_name = selected_category.replace("Purchase: ", "")
                                    
                                    cur.execute("SELECT account_id FROM chart_of_accounts WHERE account_id = %s", (acc_id,))
                                    if not cur.fetchone():
                                        cur.execute("INSERT INTO chart_of_accounts (account_id, account_name, account_type) VALUES (%s, %s, %s)", (acc_id, acc_name, acc_type))
                                    
                                    cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (1000, %s, %s)", (amount, description))
                                    cur.execute("INSERT INTO general_ledger (account_id, debit, description) VALUES (%s, %s, %s)", (acc_id, amount, description))
                                    
                                    conn.commit()
                                    st.success(f"✅ Payment recorded! {amount:,.2f} EGP applied to {acc_name}.")
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Database error: {e}")
                                    conn.rollback()
                                cur.close()

                # --- THE ACTUAL CASH FLOW REPORT ---
                st.divider()
                st.caption(f"Tracking cash movement from {start_date} to {end_date}")
                
                query_cf = """
                SELECT DATE(transaction_date) as date, description, debit AS cash_in, credit AS cash_out
                FROM general_ledger
                WHERE account_id = 1000
                AND DATE(transaction_date) >= %s 
                AND DATE(transaction_date) <= %s
                ORDER BY transaction_date DESC
                """
                try:
                    df_cf = pd.read_sql(query_cf, conn, params=(start_date, end_date))
                    total_inflows = df_cf['cash_in'].sum() if not df_cf.empty else 0.0
                    total_outflows = df_cf['cash_out'].sum() if not df_cf.empty else 0.0
                    net_cash_flow = total_inflows - total_outflows
                    
                    c1, c2, c3 = st.columns(3)
                    c1.success(f"**Cash In**\n### {total_inflows:,.2f} EGP")
                    c2.warning(f"**Cash Out**\n### {total_outflows:,.2f} EGP")
                    if net_cash_flow >= 0:
                        c3.info(f"**Net Cash**\n### +{net_cash_flow:,.2f} EGP")
                    else:
                        c3.error(f"**Net Cash**\n### {net_cash_flow:,.2f} EGP")
                    
                    if not df_cf.empty:
                        # 1. Define the coloring rules
                        def highlight_cash(col):
                            if col.name == 'cash_in':
                                # Soft green background for cash coming in
                                return ['background-color: rgba(40, 167, 69, 0.2)' if val > 0 else '' for val in col]
                            elif col.name == 'cash_out':
                                # Soft yellow background for cash going out
                                return ['background-color: rgba(255, 193, 7, 0.2)' if val > 0 else '' for val in col]
                            else:
                                # Leave date and description alone
                                return ['' for val in col]
                        
                        # 2. Apply the rules to the dataframe
                        styled_df = df_cf.style.apply(highlight_cash)
                        
                        # 3. Display the beautifully colored table!
                        st.dataframe(styled_df, use_container_width=True, hide_index=True)
                except Exception as e:
                    st.write("Error:", e)

            # ==========================================
            # 3. BALANCE SHEET VIEW
            # ==========================================
            elif statement_view == "Balance Sheet":
                st.subheader("Real-Time Balance Sheet (EGP)")
                st.caption(f"Snapshot As Of: {end_date}") # Balance sheets only use End Date!
                
                query_bs = """
                SELECT c.account_name, c.account_type, 
                       COALESCE(SUM(g.debit), 0) as total_debit, 
                       COALESCE(SUM(g.credit), 0) as total_credit
                FROM chart_of_accounts c
                LEFT JOIN general_ledger g ON c.account_id = g.account_id AND DATE(g.transaction_date) <= %s
                GROUP BY c.account_name, c.account_type
                """
                try:
                    df_b = pd.read_sql(query_bs, conn, params=(end_date,))
                    assets_list, liabilities_list, equity_list = [], [], []
                    total_assets, total_liabilities, total_equity = 0.0, 0.0, 0.0
                    revenue, expenses = 0.0, 0.0

                    for index, row in df_b.iterrows():
                        balance = 0
                        name = row['account_name']
                        if row['account_type'] == 'Asset':
                            balance = row['total_debit'] - row['total_credit']
                            if balance != 0: assets_list.append({"Account": name, "Balance": balance})
                            total_assets += balance
                        elif row['account_type'] == 'Liability':
                            balance = row['total_credit'] - row['total_debit']
                            if balance != 0: liabilities_list.append({"Account": name, "Balance": balance})
                            total_liabilities += balance
                        elif row['account_type'] == 'Equity':
                            balance = row['total_credit'] - row['total_debit']
                            if balance != 0: equity_list.append({"Account": name, "Balance": balance})
                            total_equity += balance
                        elif row['account_type'] == 'Revenue':
                            revenue += (row['total_credit'] - row['total_debit'])
                        elif row['account_type'] == 'Expense':
                            expenses += (row['total_debit'] - row['total_credit'])

                    net_income = revenue - expenses
                    if net_income != 0:
                        equity_list.append({"Account": "Retained Earnings (Net Income)", "Balance": net_income})
                    total_equity += net_income
                    
                    col_left, col_right = st.columns(2)
                    with col_left:
                        st.write("### ASSETS")
                        if assets_list: st.dataframe(pd.DataFrame(assets_list), use_container_width=True, hide_index=True)
                        st.success(f"**Total Assets: {total_assets:,.2f} EGP**")
                    with col_right:
                        st.write("### LIABILITIES")
                        if liabilities_list: st.dataframe(pd.DataFrame(liabilities_list), use_container_width=True, hide_index=True)
                        st.warning(f"**Total Liabilities: {total_liabilities:,.2f} EGP**")
                        st.write("### EQUITY")
                        if equity_list: st.dataframe(pd.DataFrame(equity_list), use_container_width=True, hide_index=True)
                        st.info(f"**Total Equity: {total_equity:,.2f} EGP**")
                    
                    st.divider()
                    total_L_and_E = total_liabilities + total_equity
                    if round(total_assets, 2) == round(total_L_and_E, 2):
                        st.success(f"✅ Your books are balanced! Assets ({total_assets:,.2f}) = Liabilities + Equity ({total_L_and_E:,.2f})")
                    else:
                        st.error(f"⚠️ Warning: Books are out of balance. Assets: {total_assets:,.2f} | L+E: {total_L_and_E:,.2f}")
                except Exception as e:
                    st.write("Error:", e)
            
            conn.close()

    # OWNER TAB 6: ADVANCED BUSINESS ANALYTICS
        with tab6:
            st.header("📈 Master Analytics Dashboard")
            
            # --- SUB-TABS FOR ANALYTICS ---
            # We use tabs inside of tabs to keep the UI incredibly clean!
            dash_kpi, dash_growth, dash_inventory, dash_heat = st.tabs([
                "🎯 KPIs & Overview", 
                "📊 Sales & Growth", 
                "📦 Inventory Breakdown", 
                "🔥 Activity Heatmap"
            ])
            
            conn = get_connection()
            
            
            # ==========================================
            # SUB-TAB 1: KPIs & OVERVIEW (YOUR DATA + YOUR THEME)
            # ==========================================
            with dash_kpi:
                
                # --- 🎨 SET YOUR COMPANY THEME COLORS HERE ---
                COLOR_REVENUE = "#99eaac"  # Currently Green
                COLOR_EXPENSE = "#FF2F05"  # Currently Red
                COLOR_PROFIT = "#8AA2E6"   # Currently Blue
                DONUT_COLORS = ["#007bff", "#17a2b8", "#28a745", "#ffc107", "#f3902d"] 
                BUBBLE_COLOR = "#007bff"
                
                # --- CUSTOM FUNCTION TO DRAW COLORED SPARKLINE CARDS ---
                def create_sparkline_card(title, value, delta_val, trend_data, bg_color):
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        y=trend_data, mode='lines+markers', 
                        line=dict(color='rgba(255,255,255,0.7)', width=2),
                        marker=dict(size=6, color='white')
                    ))
                    fig.add_trace(go.Indicator(
                        mode="number+delta", value=value,
                        delta={'reference': value - delta_val, 'position': "bottom", 'font': {'color': 'rgba(255,255,255,0.9)'}},
                        number={'font': {'color': 'white', 'size': 50}},
                        title={'text': f"<span style='color:white; font-size:16px'>{title}</span>"},
                        domain={'y': [0.2, 1], 'x': [0, 1]}
                    ))
                    fig.update_layout(
                        paper_bgcolor=bg_color, plot_bgcolor=bg_color, height=220,
                        margin=dict(l=15, r=15, t=30, b=15),
                        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                        showlegend=False
                    )
                    return fig

                st.subheader("Executive Overview")
                
                try:
                    # --- FETCH REAL KPI DATA ---
                    # 1. Revenue
                    df_rev = pd.read_sql("SELECT DATE(transaction_date) as dt, SUM(credit) as total FROM general_ledger WHERE account_id = 4000 GROUP BY dt ORDER BY dt", conn)
                    tot_rev = df_rev['total'].sum() if not df_rev.empty else 0.0
                    rev_trend = df_rev['total'].tail(7).tolist() if not df_rev.empty else [0]
                    rev_delta = rev_trend[-2] if len(rev_trend) > 1 else 0

                    # 2. Expenses
                    df_exp = pd.read_sql("SELECT DATE(transaction_date) as dt, SUM(debit - credit) as total FROM general_ledger WHERE account_id >= 5000 GROUP BY dt ORDER BY dt", conn)
                    tot_exp = df_exp['total'].sum() if not df_exp.empty else 0.0
                    exp_trend = df_exp['total'].tail(7).tolist() if not df_exp.empty else [0]
                    exp_delta = exp_trend[-2] if len(exp_trend) > 1 else 0
                    
                    # 3. Net Profit
                    net_profit = tot_rev - tot_exp
                    
                    # --- BUILD THE TOP CARDS ---
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        fig1 = create_sparkline_card("Total Revenue (EGP)", tot_rev, tot_rev - rev_delta, rev_trend, COLOR_REVENUE)
                        st.plotly_chart(fig1, use_container_width=True)
                    with col2:
                        fig2 = create_sparkline_card("Total Expenses (EGP)", tot_exp, tot_exp - exp_delta, exp_trend, COLOR_EXPENSE)
                        st.plotly_chart(fig2, use_container_width=True)
                    with col3:
                        # For profit trend, we just subtract the two trends if they align, or just show a flat line if data is sparse
                        fig3 = create_sparkline_card("Net Profit (EGP)", net_profit, 0, rev_trend, COLOR_PROFIT)
                        st.plotly_chart(fig3, use_container_width=True)

                    st.divider()
                    
                    # --- BOTTOM ROW: YOUR REAL BUBBLE & DONUT CHARTS ---
                    c_scatter, c_pie = st.columns([2, 1]) 
                    
                    with c_scatter:
                        st.write("**Sales Volume by Day (Bubble Chart)**")
                        # Query to get real sales frequency
                        query_bubble = """
                            SELECT TRIM(TO_CHAR(transaction_date, 'Day')) as "Day", 
                                   COUNT(entry_id) as "Transactions", 
                                   SUM(credit) as "Revenue"
                            FROM general_ledger 
                            WHERE account_id = 4000
                            GROUP BY "Day"
                        """
                        df_bubble = pd.read_sql(query_bubble, conn)
                        if not df_bubble.empty:
                            fig_bubble = px.scatter(
                                df_bubble, x="Day", y="Revenue", size="Transactions", 
                                color_discrete_sequence=[BUBBLE_COLOR], template="plotly_white", size_max=40
                            )
                            fig_bubble.update_xaxes(categoryorder='array', categoryarray=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], showgrid=False)
                            fig_bubble.update_yaxes(showgrid=False)
                            st.plotly_chart(fig_bubble, use_container_width=True)
                        else:
                            st.info("Log some sales to generate your bubble chart!")
                        
                    with c_pie:
                        st.write("**Inventory Value by Category**")
                        df_cat = pd.read_sql("SELECT category, SUM(total_value) as value FROM inventory_stock WHERE total_value > 0 GROUP BY category", conn)
                        if not df_cat.empty:
                            fig_donut = px.pie(
                                df_cat, names="category", values="value", hole=0.4,
                                color_discrete_sequence=DONUT_COLORS
                            )
                            fig_donut.update_traces(textposition='inside', textinfo='percent+label')
                            fig_donut.update_layout(showlegend=False)
                            st.plotly_chart(fig_donut, use_container_width=True)
                        else:
                            st.info("Add inventory to generate this chart.")

                except Exception as e:
                    st.error(f"Error loading dashboard data: {e}")

            # ==========================================
            # SUB-TAB 2: SALES & GROWTH (Line & Bar)
            # ==========================================
            with dash_growth:
                st.subheader("Revenue Growth Over Time")
                try:
                    query_daily_rev = """
                        SELECT DATE(transaction_date) as "Date", SUM(credit) as "Revenue"
                        FROM general_ledger 
                        WHERE account_id = 4000
                        GROUP BY DATE(transaction_date)
                        ORDER BY "Date"
                    """
                    df_daily = pd.read_sql(query_daily_rev, conn)
                    if not df_daily.empty:
                        # Plotly Area Chart (Looks very modern and corporate)
                        fig_growth = px.area(df_daily, x="Date", y="Revenue", title="Daily Revenue Trend", template="plotly_white", color_discrete_sequence=["#28a745"])
                        st.plotly_chart(fig_growth, use_container_width=True)
                    else:
                        st.info("Log some sales to see your growth chart!")
                except Exception as e:
                    pass

            # ==========================================
            # SUB-TAB 3: INVENTORY BREAKDOWN (Pie Chart)
            # ==========================================
            with dash_inventory:
                st.subheader("Inventory Distribution by Category")
                c_pie, c_data = st.columns([2, 1])
                try:
                    query_cat = """
                        SELECT category as "Category", SUM(total_value) as "Value"
                        FROM inventory_stock
                        WHERE total_value > 0
                        GROUP BY category
                    """
                    df_cat = pd.read_sql(query_cat, conn)
                    if not df_cat.empty:
                        with c_pie:
                            # Plotly Donut Chart (A modern pie chart with a hole in the middle)
                            fig_pie = px.pie(df_cat, names="Category", values="Value", hole=0.4, title="Capital Tied Up in Stock")
                            st.plotly_chart(fig_pie, use_container_width=True)
                        with c_data:
                            st.write("**Raw Data:**")
                            st.dataframe(df_cat, hide_index=True)
                    else:
                        st.info("No categorized inventory data available.")
                except Exception as e:
                    pass

            # ==========================================
            # SUB-TAB 4: ACTIVITY HEATMAP
            # ==========================================
            with dash_heat:
                st.subheader("Sales Activity Heatmap (Day vs. Category)")
                st.caption("See which days are your busiest, and what sells best on those days.")
                try:
                    # We look at the descriptions of your sales to figure out what category sold on what day
                    query_heat = """
                        SELECT 
                            TRIM(TO_CHAR(g.transaction_date, 'Day')) as "Day of Week",
                            i.category as "Category",
                            COUNT(g.entry_id) as "Sales Volume"
                        FROM general_ledger g
                        JOIN inventory_stock i ON g.description LIKE '%' || i.product_id || '%'
                        WHERE g.account_id = 4000
                        GROUP BY "Day of Week", i.category
                    """
                    df_heat = pd.read_sql(query_heat, conn)
                    if not df_heat.empty:
                        # Plotly Density Heatmap
                        fig_heat = px.density_heatmap(df_heat, x="Day of Week", y="Category", z="Sales Volume", 
                                                      color_continuous_scale="Blues", title="Busiest Sales Channels")
                        
                        # Reorder days logically instead of alphabetically
                        fig_heat.update_xaxes(categoryorder='array', categoryarray=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
                        st.plotly_chart(fig_heat, use_container_width=True)
                    else:
                        st.info("Not enough diverse sales data to generate a heatmap yet. Keep selling!")
                except Exception as e:
                    st.write("Heatmap requires specific product sales data to generate.")

            conn.close()

    # OWNER TAB 7: THE COMPLETE TAX CENTER (المركز الضريبي الشامل)
        with tab7:
            st.header("🇪🇬 Comprehensive Tax Center")
            st.write("Detailed, real-time tax liability calculations and tracking based on your ledger.")
            
            conn = get_connection()
            
            try:
                # --- 1. FETCH THE RAW FINANCIAL DATA ---
                df_rev = pd.read_sql("SELECT SUM(credit - debit) as total FROM general_ledger WHERE account_id = 4000 AND DATE(transaction_date) >= %s AND DATE(transaction_date) <= %s", conn, params=(start_date, end_date))
                total_revenue = df_rev['total'].iloc[0] if pd.notnull(df_rev['total'].iloc[0]) else 0.0
                
                df_exp = pd.read_sql("SELECT SUM(debit - credit) as total FROM general_ledger WHERE account_id >= 5000 AND DATE(transaction_date) >= %s AND DATE(transaction_date) <= %s", conn, params=(start_date, end_date))
                total_expenses = df_exp['total'].iloc[0] if pd.notnull(df_exp['total'].iloc[0]) else 0.0
                
                df_vat = pd.read_sql("SELECT SUM(credit - debit) as total FROM general_ledger WHERE account_id = 2200 AND DATE(transaction_date) >= %s AND DATE(transaction_date) <= %s", conn, params=(start_date, end_date))
                vat_collected = df_vat['total'].iloc[0] if pd.notnull(df_vat['total'].iloc[0]) else 0.0
                
                df_payroll = pd.read_sql("SELECT SUM(debit - credit) as total FROM general_ledger WHERE account_id = 5200 AND DATE(transaction_date) >= %s AND DATE(transaction_date) <= %s", conn, params=(start_date, end_date))
                total_payroll = df_payroll['total'].iloc[0] if pd.notnull(df_payroll['total'].iloc[0]) else 0.0

                # --- 2. CALCULATE TAX LIABILITIES ---
                net_profit = total_revenue - total_expenses
                corporate_tax_liability = (net_profit * 0.225) if net_profit > 0 else 0.0
                payroll_tax_liability = total_payroll * 0.10 
                wht_advance_paid = total_revenue * 0.01 
                
                total_eta_owed = vat_collected + corporate_tax_liability + payroll_tax_liability

                # --- 3. THE SUB-TABS ---
                tax_vat, tax_corp, tax_payroll, tax_wht, tax_master = st.tabs([
                    "🛒 VAT (14%)", 
                    "🏢 Corporate Tax", 
                    "👥 Payroll Tax",
                    "✂️ Withholding Tax (WHT)",
                    "📄 Master Declaration"
                ])

                with tax_vat:
                    st.subheader("Value Added Tax (VAT) - 14%")
                    v1, v2, v3 = st.columns(3)
                    v1.metric("Gross Sales", f"{total_revenue:,.2f} EGP")
                    v2.metric("Statutory VAT Rate", "14.0%")
                    v3.metric("Total VAT Owed", f"{vat_collected:,.2f} EGP")

                with tax_corp:
                    st.subheader("Corporate Income Tax (ضريبة الأرباح التجارية)")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Net Taxable Profit", f"{net_profit:,.2f} EGP")
                    c2.metric("WHT Advance Credit", f"({wht_advance_paid:,.2f}) EGP")
                    final_corp_tax = corporate_tax_liability - wht_advance_paid
                    c3.metric("Final Corp Tax Due", f"{final_corp_tax if final_corp_tax > 0 else 0:,.2f} EGP")
                    
                    st.divider()
                    st.write("**Expense Deductions Breakdown**")
                    query_exp_details = "SELECT c.account_name as \"Expense Category\", SUM(g.debit - g.credit) as \"Total Deducted (EGP)\" FROM general_ledger g JOIN chart_of_accounts c ON g.account_id = c.account_id WHERE c.account_type = 'Expense' AND DATE(g.transaction_date) >= %s AND DATE(g.transaction_date) <= %s GROUP BY c.account_name ORDER BY \"Total Deducted (EGP)\" DESC"
                    df_exp_details = pd.read_sql(query_exp_details, conn, params=(start_date, end_date))
                    if not df_exp_details.empty: st.dataframe(df_exp_details, use_container_width=True, hide_index=True)

                with tax_payroll:
                    st.subheader("Payroll Tax / Income Tax (ضريبة كسب العمل)")
                    p1, p2 = st.columns(2)
                    p1.metric("Total Gross Payroll Issued", f"{total_payroll:,.2f} EGP")
                    p2.metric("Estimated Tax Withheld (Due to ETA)", f"{payroll_tax_liability:,.2f} EGP")

                with tax_wht:
                    st.subheader("Withholding Tax - WHT (الخصم وتحصيل تحت حساب الضريبة)")
                    w1, w2 = st.columns(2)
                    w1.metric("Total Wholesale Revenue", f"{total_revenue:,.2f} EGP")
                    w2.metric("WHT Advance Credits (1%)", f"{wht_advance_paid:,.2f} EGP", "Reduces Corporate Tax!")
                    st.success(f"✅ You have accumulated **{wht_advance_paid:,.2f} EGP** in tax credits.")

                with tax_master:
                    c_report, c_actions = st.columns([2, 1])
                    with c_report:
                        st.subheader("📄 Consolidated Tax Declaration")
                        tax_report = pd.DataFrame({
                            "Line Item (البند)": ["1. Gross Revenue (إجمالي الإيرادات)", "2. Deductible Expenses (المصروفات المعتمدة)", "3. Net Commercial Profit (صافي الربح)", "4. VAT Collected @ 14% (ضريبة القيمة المضافة)", "5. Gross Corporate Tax @ 22.5% (ضريبة الأرباح التجارية)", "6. Less: WHT Advance Paid (يخصم: ضريبة الخصم من المنبع)", "7. Net Corporate Tax Due (صافي ضريبة الأرباح المستحقة)", "8. Employee Payroll Tax (ضريبة كسب العمل)"],
                            "Amount / EGP (القيمة)": [f"{total_revenue:,.2f}", f"({total_expenses:,.2f})", f"{net_profit:,.2f}", f"{vat_collected:,.2f}", f"{corporate_tax_liability:,.2f}", f"({wht_advance_paid:,.2f})", f"{(corporate_tax_liability - wht_advance_paid) if (corporate_tax_liability - wht_advance_paid) > 0 else 0:,.2f}", f"{payroll_tax_liability:,.2f}"]
                        })
                        st.table(tax_report)
                    
                    # --- RESTORED: ACTIONS SECTION ---
                    with c_actions:
                        st.write("**Tax Actions**")
                        st.info("💡 Use the 'Date Filter' on the left to run this for specific quarters.")
                        if st.button("💳 Log Tax Payment to ETA", type="primary"):
                            st.warning("Please switch to the **Cash Flow Statements** tab and use the 'Record New Cash Outflow' button. Select 'Taxes Paid to ETA' to officially clear these liabilities from your books!")

            except Exception as e:
                st.error(f"Could not calculate taxes. Ensure ledger data is intact. Error: {e}")
                
            conn.close()
    
    # OWNER TAB 8: SUPPLIERS & LOGISTICS
        with tab8:
            st.header("🚚 Supplier & Logistics Management")
            st.write("Manage factory relationships and track incoming shipments to your warehouses.")
            
            conn = get_connection()
            cur = conn.cursor()
            
            # --- AUTO-CREATE THE DATABASE TABLES ---
            cur.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    supplier_id SERIAL PRIMARY KEY,
                    company_name VARCHAR(150) NOT NULL,
                    contact_person VARCHAR(100),
                    phone VARCHAR(50),
                    primary_category VARCHAR(50),
                    payment_terms VARCHAR(50)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shipments (
                    shipment_id SERIAL PRIMARY KEY,
                    supplier_id INTEGER REFERENCES suppliers(supplier_id),
                    container_number VARCHAR(100),
                    status VARCHAR(50),
                    expected_arrival DATE,
                    freight_cost NUMERIC DEFAULT 0
                )
            """)
            conn.commit()

            # --- SUB-TABS FOR ORGANIZATION ---
            log_suppliers, log_shipments = st.tabs(["🏭 Factory & Supplier Directory", "🚢 Active Shipments & Freight"])

            # ==========================================
            # SUB-TAB 1: SUPPLIER DIRECTORY
            # ==========================================
            with log_suppliers:
                with st.expander("➕ Add New Supplier / Factory", expanded=False):
                    with st.form("add_supplier_form"):
                        s1, s2 = st.columns(2)
                        with s1:
                            sup_name = st.text_input("Company / Factory Name")
                            sup_contact = st.text_input("Contact Person")
                            sup_phone = st.text_input("Phone Number")
                        with s2:
                            sup_category = st.selectbox("Primary Good Supplied", ["Yarn", "Fabric", "Zippers", "Beads", "Mixed/Other"])
                            sup_terms = st.selectbox("Payment Terms", ["Cash on Delivery (COD)", "Net 30 Days", "Net 60 Days", "Advance Payment"])
                        
                        if st.form_submit_button("Save Supplier"):
                            if sup_name:
                                try:
                                    cur.execute("INSERT INTO suppliers (company_name, contact_person, phone, primary_category, payment_terms) VALUES (%s, %s, %s, %s, %s)", 
                                                (sup_name, sup_contact, sup_phone, sup_category, sup_terms))
                                    conn.commit()
                                    st.success(f"✅ {sup_name} added to directory!")
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                            else:
                                st.error("Company Name is required.")

                st.subheader("Approved Vendor List")
                try:
                    df_sup = pd.read_sql("SELECT supplier_id as \"ID\", company_name as \"Company\", contact_person as \"Contact\", phone as \"Phone\", primary_category as \"Category\", payment_terms as \"Terms\" FROM suppliers ORDER BY supplier_id", conn)
                    if not df_sup.empty:
                        st.dataframe(df_sup, use_container_width=True, hide_index=True)
                    else:
                        st.info("No suppliers registered yet.")
                except Exception as e:
                    pass

            # ==========================================
            # SUB-TAB 2: LOGISTICS & SHIPMENTS
            # ==========================================
            with log_shipments:
                # Fetch suppliers for the dropdown
                cur.execute("SELECT supplier_id, company_name FROM suppliers")
                sup_list = cur.fetchall()
                
                with st.expander("🚢 Register New Incoming Shipment", expanded=False):
                    if sup_list:
                        sup_dict = {f"{s[1]} (ID: {s[0]})": s[0] for s in sup_list}
                        
                        with st.form("add_shipment_form"):
                            st.write("Track a new container or delivery truck and log the freight costs.")
                            sh1, sh2 = st.columns(2)
                            with sh1:
                                selected_sup = st.selectbox("Originating Supplier", list(sup_dict.keys()))
                                container_no = st.text_input("Container / Waybill Number", placeholder="e.g., MSKU1234567")
                            with sh2:
                                ship_status = st.selectbox("Current Status", ["Departed Factory", "In Customs", "In Transit to Warehouse", "Delivered"])
                                freight_cost = st.number_input("Freight / Shipping Cost (EGP)", min_value=0.0, step=500.0)
                            
                            if st.form_submit_button("Log Shipment & Record Cost", type="primary"):
                                sup_id_val = sup_dict[selected_sup]
                                try:
                                    # 1. Log the shipment tracking
                                    cur.execute("INSERT INTO shipments (supplier_id, container_number, status, freight_cost) VALUES (%s, %s, %s, %s)", 
                                                (sup_id_val, container_no, ship_status, freight_cost))
                                    
                                    # 2. Automatically log the expense to the Ledger (Account 5500: Logistics & Shipping)
                                    if freight_cost > 0:
                                        cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (1000, %s, %s)", (freight_cost, f"Freight Payment: {container_no}"))
                                        cur.execute("INSERT INTO general_ledger (account_id, debit, description) VALUES (5500, %s, %s)", (freight_cost, f"Freight Expense: {container_no}"))
                                    
                                    conn.commit()
                                    st.success(f"✅ Shipment logged and {freight_cost:,.2f} EGP recorded in accounting!")
                                    time.sleep(1.5)
                                    st.rerun()
                                except Exception as e:
                                    conn.rollback()
                                    st.error(f"Database error: {e}")
                    else:
                        st.warning("Please add a supplier in the directory before logging a shipment.")

                st.subheader("Active Logistics Tracker")
                try:
                    query_ship = """
                        SELECT sh.shipment_id as "Tracking ID", su.company_name as "Supplier", 
                               sh.container_number as "Container Ref", sh.status as "Status", 
                               sh.freight_cost as "Freight (EGP)"
                        FROM shipments sh
                        JOIN suppliers su ON sh.supplier_id = su.supplier_id
                        ORDER BY sh.shipment_id DESC
                    """
                    df_ship = pd.read_sql(query_ship, conn)
                    if not df_ship.empty:
                        # Color coding the status for quick visual reference
                        def highlight_status(val):
                            if val == 'Delivered': return 'background-color: rgba(40, 167, 69, 0.2)'
                            elif val == 'In Customs': return 'background-color: rgba(220, 53, 69, 0.2)'
                            elif val == 'In Transit to Warehouse': return 'background-color: rgba(0, 123, 255, 0.2)'
                            return ''
                        
                        st.dataframe(df_ship.style.map(highlight_status, subset=['Status']), use_container_width=True, hide_index=True)
                    else:
                        st.info("No active shipments in transit.")
                except Exception as e:
                    pass
            
            cur.close()
            conn.close()
    

    # --- IF THE USER IS AN EMPLOYEE ---
    elif st.session_state["role"] == "Employee":
        tab1, = st.tabs(["💰 Log a Sale"])
        
        with tab1:
            st.header("Record a Wholesale Transaction")
            
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT product_id, product_name, unit_price, stock_quantity FROM inventory_stock WHERE stock_quantity > 0")
            available_products = cur.fetchall()
            
            if not available_products:
                st.warning("No inventory available to sell.")
            else:
                product_options = {f"{p[0]} | {p[1]} (Stock: {p[3]})": p for p in available_products}
                
                selected_prod_label = st.selectbox("Select Product to Sell", list(product_options.keys()), key="emp_sale_prod")
                
                col_q, col_p = st.columns(2)
                with col_q:
                    qty_sold = st.number_input("Quantity to Sell", min_value=1.0, step=1.0, key="emp_qty")
                with col_p:
                    unit_sell_price = st.number_input("Selling Price per Unit (EGP)", min_value=0.0, step=10.0, key="emp_price")
                
                sale_amount = qty_sold * unit_sell_price
                st.info(f"### Total Invoice Amount: {sale_amount:,.2f} EGP")
                
                if st.button("Record Sale", type="primary", key="emp_record_btn"):
                    if sale_amount == 0:
                        st.error("Selling price cannot be zero!")
                    else:
                        prod_data = product_options[selected_prod_label]
                        p_id, p_name, p_cost_price, p_stock = prod_data[0], prod_data[1], prod_data[2], prod_data[3]
                        
                        if qty_sold > p_stock:
                            st.error(f"Not enough stock! System shows {p_stock} available.")
                        else:
                            cogs = float(qty_sold) * float(p_cost_price)
                            vat_amount = float(sale_amount) * 0.14
                            total_cash = float(sale_amount) + vat_amount
                            desc = f"Sold {qty_sold} of {p_id} by Employee @ {unit_sell_price}/unit"
                            
                            try:
                                cur.execute("UPDATE inventory_stock SET stock_quantity = stock_quantity - %s, total_value = total_value - %s WHERE product_id = %s", (qty_sold, cogs, p_id))
                                cur.execute("INSERT INTO general_ledger (account_id, debit, description) VALUES (1000, %s, %s)", (total_cash, desc))
                                cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (4000, %s, %s)", (sale_amount, desc))
                                cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (2200, %s, %s)", (vat_amount, desc))
                                cur.execute("INSERT INTO general_ledger (account_id, debit, description) VALUES (5000, %s, %s)", (cogs, desc))
                                cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (1200, %s, %s)", (cogs, desc))
                                conn.commit()
                                st.success("✅ Sale successfully recorded and inventory updated!")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error("Database error.")
                                conn.rollback()
            cur.close()
            conn.close()