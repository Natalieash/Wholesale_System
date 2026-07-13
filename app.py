import streamlit as st
import psycopg2
import pandas as pd
import time
import datetime
import plotly.express as px
import plotly.graph_objects as go
import re

# ==========================================
# 1. PAGE CONFIGURATION & BASE CSS
# ==========================================
st.set_page_config(
    page_title="Yarn ERP System", 
    page_icon="🧶", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Base CSS (Hides Streamlit branding and styles the layout)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    .block-container {
        padding-top: 2rem; 
        padding-bottom: 2rem; 
        max-width: 95%;
    }
    .streamlit-expanderHeader {
        background-color: #f1f3f5; 
        border-radius: 8px;
    }
    .login-box { 
        max-width: 400px; 
        margin: 0 auto; 
        padding: 2rem; 
        border-radius: 10px; 
        background-color: #ffffff; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION SETUP & LANGUAGE GATEWAY
# ==========================================
if "language" not in st.session_state: 
    st.session_state["language"] = None

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = ""
    st.session_state["username"] = ""

# --- THE LANGUAGE SELECTOR SCREEN ---
if st.session_state["language"] is None:
    st.markdown("<br><br><br><h1 style='text-align: center; color: #0c4063;'>Select System Language<br>اختر لغة النظام</h1><br>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
    with col2:
        if st.button("🇬🇧 English", use_container_width=True):
            st.session_state["language"] = "en"
            st.rerun()
    with col3:
        if st.button("🇪🇬 العربية", use_container_width=True):
            st.session_state["language"] = "ar"
            st.rerun()
            
    st.stop() # Pauses the app here until a language is chosen

lang = st.session_state["language"]

# --- DYNAMIC RTL (RIGHT-TO-LEFT) CSS FOR ARABIC ---
if lang == "ar":
    st.markdown("""
    <style>
        .stApp, .block-container, [data-testid="stSidebar"] { 
            direction: rtl; 
            text-align: right; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
        }
        .stTextInput>div>div>input, .stSelectbox>div>div>select, .stNumberInput>div>div>input { 
            text-align: right; 
            direction: rtl; 
        }
        [data-testid="stSidebar"] {
            border-left: 1px solid #e9ecef; 
            border-right: none;
        }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            border-right: 1px solid #e9ecef;
        }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. DATABASE CONNECTION (CLOUD SECURE)
# ==========================================
def get_connection():
    # This tells your app to look inside a secure vault for the link, 
    # instead of writing the password directly in the code!
    return psycopg2.connect(st.secrets["DATABASE_URL"])

# ==========================================
# 4. FLATTENED PAGE FUNCTIONS
# ==========================================

def render_inventory():
    st.header("📦 Manage Inventory" if lang == "en" else "📦 إدارة المخزون")
    
    # --- 1. RECEIVE INVENTORY ---
    with st.expander("➕ Receive New Product" if lang == "en" else "➕ استلام منتج جديد", expanded=True):
        st.write("Log incoming inventory from the factory." if lang == "en" else "تسجيل البضائع الواردة من المصنع وتصنيفها.")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            prod_id = st.text_input("Product ID" if lang == "en" else "كود المنتج")
            prod_name = st.text_input("Product Name" if lang == "en" else "اسم المنتج")
            category_options = ["Yarn", "Beads", "Zippers", "Fabric", "Other"] if lang == "en" else ["خيوط", "خرز", "سحابات/سوست", "قماش", "أخرى"]
            category = st.selectbox("Category" if lang == "en" else "الفئة", category_options)
        
        with c2:
            unit_price = st.number_input("Cost per Unit (EGP)" if lang == "en" else "تكلفة الوحدة (ج.م)", min_value=0.0, step=10.0)
            sell_unit_options = ["Kilo", "Cone", "Box", "Meter", "Piece", "Pack"] if lang == "en" else ["كيلو", "كونة", "علبة", "متر", "قطعة", "حزمة"]
            unit_type = st.selectbox("Selling Unit" if lang == "en" else "وحدة البيع", sell_unit_options)
            purch_unit_options = ["Kilo", "Cone", "Box", "Meter", "Piece", "Pack", "Pallet", "Ton", "Roll"] if lang == "en" else ["كيلو", "كونة", "علبة", "متر", "قطعة", "حزمة", "بالتة", "طن", "رول"]
            purchase_unit = st.selectbox("Purchased As" if lang == "en" else "وحدة الشراء", purch_unit_options)
        
        with c3:
            purchase_qty = st.number_input("Quantity Purchased" if lang == "en" else "الكمية المشتراة", min_value=0.0, step=1.0)
            
            if purchase_unit == unit_type:
                conv_factor = 1.0
                st.info("No conversion needed." if lang == "en" else "لا يوجد تحويل مطلوب.")
            else:
                conv_prompt = f"Units in 1 {purchase_unit}?" if lang == "en" else "كم عدد وحدات البيع في وحدة الشراء؟"
                conv_factor = st.number_input(conv_prompt, min_value=1.0, value=1.0, step=1.0)

        base_qty_to_stock = purchase_qty * conv_factor
        total_value = unit_price * base_qty_to_stock
        
        info_text = f"**Adding:** {base_qty_to_stock:,.0f} | **Total Value:** {total_value:,.2f} EGP" if lang == "en" else f"**الإضافة للمخزن:** {base_qty_to_stock:,.0f} | **القيمة الإجمالية:** {total_value:,.2f} ج.م"
        st.info(info_text)

        if st.button("Save to Inventory" if lang == "en" else "حفظ في المخزون", type="primary"):
            if prod_id and prod_name:
                conn = get_connection()
                cur = conn.cursor()
                try:
                    insert_query = """
                        INSERT INTO inventory_stock 
                        (product_id, product_name, category, unit_type, purchase_unit, conversion_factor, unit_price, stock_quantity, total_value) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cur.execute(insert_query, (prod_id, prod_name, category, unit_type, purchase_unit, conv_factor, unit_price, base_qty_to_stock, total_value))
                    conn.commit()
                    st.success("Added to stock!" if lang == "en" else "تمت الإضافة للمخزون بنجاح!")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error("Error: Product ID might already exist." if lang == "en" else "خطأ: كود المنتج موجود مسبقاً.")
                
                cur.close()
                conn.close()

    # --- 2. VIEW INVENTORY ---
    st.divider()
    st.subheader("Current Stock" if lang == "en" else "المخزون الحالي")
    
    conn = get_connection()
    query_inv = """
        SELECT product_id as "ID", product_name as "Name", category as "Category", 
               unit_type as "Unit", unit_price as "Price (EGP)", 
               stock_quantity as "Qty", total_value as "Total Value" 
        FROM inventory_stock 
        ORDER BY category, product_id
    """
    df_inv = pd.read_sql(query_inv, conn)
    
    if lang == "ar" and not df_inv.empty:
        df_inv.columns = ["الكود", "الاسم", "الفئة", "الوحدة", "السعر", "الكمية", "القيمة الإجمالية"]
        
    if not df_inv.empty: 
        st.dataframe(df_inv, use_container_width=True, hide_index=True)

    # --- 3. EDIT A MISTAKE (RESTORED & TRANSLATED) ---
    expander_title = "✏️ Edit a Product Mistake" if lang == "en" else "✏️ تعديل خطأ في منتج"
    with st.expander(expander_title):
        cur = conn.cursor()
        cur.execute("SELECT product_id, product_name, category, unit_type, unit_price, stock_quantity FROM inventory_stock")
        all_items = cur.fetchall()
        
        if all_items:
            edit_options = {f"{item[0]} - {item[1]}": item for item in all_items}
            sel_prompt = "Select product to fix:" if lang == "en" else "اختر المنتج لتعديله:"
            sel_item = st.selectbox(sel_prompt, list(edit_options.keys()))
            
            old_id, old_name, old_cat, old_unit, old_price, old_qty = edit_options[sel_item]
            
            with st.form("edit_product_form"):
                st.write("Type the correct information below:" if lang == "en" else "أدخل المعلومات الصحيحة أدناه:")
                e_col1, e_col2, e_col3 = st.columns(3)
                
                with e_col1:
                    new_id = st.text_input("Product ID" if lang == "en" else "كود المنتج", value=old_id)
                    new_name = st.text_input("Name" if lang == "en" else "اسم المنتج", value=old_name)
                    
                with e_col2:
                    # Match the old category intelligently across languages
                    cat_list_en = ["Yarn", "Beads", "Zippers", "Fabric", "Other"]
                    cat_list_ar = ["خيوط", "خرز", "سحابات/سوست", "قماش", "أخرى"]
                    cat_list = cat_list_en if lang == "en" else cat_list_ar
                    
                    try:
                        if old_cat in cat_list_en: cat_idx = cat_list_en.index(old_cat)
                        elif old_cat in cat_list_ar: cat_idx = cat_list_ar.index(old_cat)
                        else: cat_idx = 0
                    except ValueError: cat_idx = 0
                    
                    new_cat = st.selectbox("Category" if lang == "en" else "الفئة", cat_list, index=cat_idx)
                    
                    unit_list_en = ["Kilo", "Cone", "Box", "Meter", "Piece", "Pack"]
                    unit_list_ar = ["كيلو", "كونة", "علبة", "متر", "قطعة", "حزمة"]
                    unit_list = unit_list_en if lang == "en" else unit_list_ar
                    
                    try:
                        if old_unit in unit_list_en: unit_idx = unit_list_en.index(old_unit)
                        elif old_unit in unit_list_ar: unit_idx = unit_list_ar.index(old_unit)
                        else: unit_idx = 0
                    except ValueError: unit_idx = 0
                    
                    new_unit = st.selectbox("Measurement" if lang == "en" else "الوحدة", unit_list, index=unit_idx)
                    
                with e_col3:
                    new_price = st.number_input("Unit Price" if lang == "en" else "سعر الوحدة", value=float(old_price), step=1.0)
                    new_qty = st.number_input("Quantity in Stock" if lang == "en" else "الكمية في المخزن", value=float(old_qty), step=1.0)
                    
                submit_label = "Apply Corrections" if lang == "en" else "تطبيق التعديلات"
                if st.form_submit_button(submit_label):
                    new_total = new_price * new_qty
                    
                    update_query = """
                        UPDATE inventory_stock 
                        SET product_id = %s, product_name = %s, category = %s, 
                            unit_type = %s, unit_price = %s, stock_quantity = %s, total_value = %s 
                        WHERE product_id = %s
                    """
                    cur.execute(update_query, (new_id, new_name, new_cat, new_unit, new_price, new_qty, new_total, old_id))
                    conn.commit()
                    
                    st.success("✅ Product updated! Refreshing..." if lang == "en" else "✅ تم تحديث المنتج! جاري التحديث...")
                    time.sleep(1.5)
                    st.rerun()
                    
        cur.close()
    conn.close()

def render_sales(is_owner):
    st.header("💰 Record a Wholesale Transaction" if lang == "en" else "💰 تسجيل معاملة بيع جملة")
    
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT product_id, product_name, unit_price, stock_quantity FROM inventory_stock WHERE stock_quantity > 0")
    available_products = cur.fetchall()
    
    if not available_products: 
        st.warning("No inventory available to sell!" if lang == "en" else "لا يوجد مخزون متاح للبيع!")
    else:
        # Create dictionary for the dropdown
        if lang == "en":
            product_options = {f"{p[0]} | {p[1]} (Stock: {p[3]})": p for p in available_products}
        else:
            product_options = {f"{p[0]} | {p[1]} (المتاح: {p[3]})": p for p in available_products}
            
        selected_prod_label = st.selectbox("Select Product" if lang == "en" else "اختر المنتج", list(product_options.keys()))
        
        col_q, col_p = st.columns(2)
        with col_q: 
            qty_sold = st.number_input("Quantity to Sell" if lang == "en" else "الكمية المباعة", min_value=1.0, step=1.0)
        with col_p: 
            unit_sell_price = st.number_input("Selling Price per Unit (EGP)" if lang == "en" else "سعر البيع للوحدة (ج.م)", min_value=0.0, step=10.0)
        
        sale_amount = qty_sold * unit_sell_price
        
        if lang == "en":
            st.info(f"### Total Invoice Amount: {sale_amount:,.2f} EGP")
        else:
            st.info(f"### إجمالي الفاتورة: {sale_amount:,.2f} ج.م")
        
        if st.button("Record Sale" if lang == "en" else "تسجيل البيع", type="primary"):
            prod_data = product_options[selected_prod_label]
            p_id = prod_data[0]
            p_name = prod_data[1]
            p_cost_price = prod_data[2]
            p_stock = prod_data[3]
            
            if qty_sold > p_stock: 
                st.error("Not enough stock!" if lang == "en" else "الكمية غير كافية في المخزن!")
            else:
                cogs = float(qty_sold) * float(p_cost_price) 
                vat_amount = float(sale_amount) * 0.14
                total_cash = float(sale_amount) + vat_amount
                
                if lang == "en":
                    desc = f"Sold {qty_sold} of {p_id} @ {unit_sell_price}"
                else:
                    desc = f"بيع {qty_sold} من {p_id} بسعر {unit_sell_price}"
                    
                try:
                    # Update Inventory
                    cur.execute("UPDATE inventory_stock SET stock_quantity = stock_quantity - %s, total_value = total_value - %s WHERE product_id = %s", (qty_sold, cogs, p_id))
                    
                    # Accounting Journal Entries
                    cur.execute("INSERT INTO general_ledger (account_id, debit, description) VALUES (1000, %s, %s)", (total_cash, desc))
                    cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (4000, %s, %s)", (sale_amount, desc))
                    cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (2200, %s, %s)", (vat_amount, desc))
                    cur.execute("INSERT INTO general_ledger (account_id, debit, description) VALUES (5000, %s, %s)", (cogs, desc))
                    cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (1200, %s, %s)", (cogs, desc))
                    
                    conn.commit()
                    st.success("✅ Sale logged!" if lang == "en" else "✅ تم تسجيل البيع بنجاح!")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
                    conn.rollback()

        # --- ONLY SHOW HISTORY & UNDO BUTTON TO OWNERS ---
        if is_owner:
            st.divider()
            st.subheader("Recent Sales History & Corrections" if lang == "en" else "تاريخ المبيعات الحديثة وتصحيحها")
            
            query_sales = """
                SELECT DATE(transaction_date) as "Date", description as "Details", credit as "Revenue (EGP)" 
                FROM general_ledger 
                WHERE account_id = 4000 
                ORDER BY transaction_date DESC LIMIT 20
            """
            df_sales = pd.read_sql(query_sales, conn)
            
            if lang == "ar" and not df_sales.empty: 
                df_sales.columns = ["التاريخ", "التفاصيل", "الإيرادات (ج.م)"]
                
            if not df_sales.empty: 
                st.dataframe(df_sales, use_container_width=True, hide_index=True)
            
            with st.expander("🚨 Fix a Mistaken Sale (Undo)" if lang == "en" else "🚨 التراجع عن عملية بيع خاطئة"):
                cur.execute("SELECT description, credit FROM general_ledger WHERE account_id = 4000 ORDER BY transaction_date DESC LIMIT 20")
                recent_sales = cur.fetchall()
                
                if recent_sales:
                    sale_options = {f"{s[0]} | Revenue: {s[1]}": s[0] for s in recent_sales}
                    sale_to_delete = st.selectbox("Select sale to undo:" if lang == "en" else "اختر البيع للتراجع:", list(sale_options.keys()))
                    
                    if st.button("Undo this Sale" if lang == "en" else "إلغاء هذا البيع"):
                        desc_to_undo = sale_options[sale_to_delete]
                        cur.execute("DELETE FROM general_ledger WHERE description = %s", (desc_to_undo,))
                        
                        if lang == "en":
                            match = re.search(r"Sold (\d+\.?\d*) of (\S+)", desc_to_undo) 
                        else:
                            match = re.search(r"بيع (\d+\.?\d*) من (\S+)", desc_to_undo)
                            
                        if match:
                            qty_to_return = float(match.group(1))
                            p_id_to_return = match.group(2)
                            
                            cur.execute("SELECT unit_price FROM inventory_stock WHERE product_id = %s", (p_id_to_return,))
                            price_row = cur.fetchone()
                            
                            if price_row:
                                cogs_returned = qty_to_return * price_row[0]
                                cur.execute("UPDATE inventory_stock SET stock_quantity = stock_quantity + %s, total_value = total_value + %s WHERE product_id = %s", (qty_to_return, cogs_returned, p_id_to_return))
                                
                        conn.commit()
                        st.success("✅ Reversed!" if lang == "en" else "✅ تم التراجع!")
                        time.sleep(1.5)
                        st.rerun()
                        
    cur.close()
    conn.close()

def render_hr():
    st.header("👥 Human Resources & Payroll" if lang == "en" else "👥 الموارد البشرية والرواتب")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Auto-create tables if missing
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

    with st.expander("➕ Hire / Add New Employee" if lang == "en" else "➕ تعيين / إضافة موظف جديد", expanded=False):
        with st.form("add_employee_form"):
            c_name, c_role = st.columns(2)
            with c_name:
                emp_name = st.text_input("Full Name" if lang == "en" else "الاسم الكامل")
                emp_phone = st.text_input("Phone Number" if lang == "en" else "رقم الهاتف")
            with c_role:
                roles_en = ["Sales Representative", "Warehouse Staff", "Driver", "Manager", "Accountant", "Other"]
                roles_ar = ["مندوب مبيعات", "موظف مخزن", "سائق", "مدير", "محاسب", "أخرى"]
                emp_role = st.selectbox("Job Title" if lang == "en" else "المسمى الوظيفي", roles_en if lang == "en" else roles_ar)
                emp_salary = st.number_input("Monthly Base Salary (EGP)" if lang == "en" else "الراتب الأساسي (ج.م)", min_value=0.0, step=500.0)
            
            if st.form_submit_button("Add Employee" if lang == "en" else "إضافة الموظف"):
                if emp_name:
                    cur.execute("INSERT INTO employees (full_name, job_title, phone_number, base_salary) VALUES (%s, %s, %s, %s)", (emp_name, emp_role, emp_phone, emp_salary))
                    conn.commit()
                    st.success("Added to team!" if lang == "en" else "تمت إضافته للفريق!")
                    time.sleep(1.5)
                    st.rerun()

    st.subheader("Current Staff Directory" if lang == "en" else "دليل الموظفين الحاليين")
    query_emp = """
        SELECT employee_id as "ID", full_name as "Name", job_title as "Role", 
               phone_number as "Phone", base_salary as "Salary (EGP)", hire_date as "Hired On" 
        FROM employees ORDER BY employee_id
    """
    df_employees = pd.read_sql(query_emp, conn)
    
    if lang == "ar" and not df_employees.empty: 
        df_employees.columns = ["الكود", "الاسم", "الوظيفة", "الهاتف", "الراتب (ج.م)", "تاريخ التعيين"]
        
    if not df_employees.empty: 
        st.dataframe(df_employees, use_container_width=True, hide_index=True)

    st.divider()
    with st.expander("💸 Run Payroll (Issue Salaries)" if lang == "en" else "💸 صرف الرواتب", expanded=False):
        cur.execute("SELECT employee_id, full_name, base_salary FROM employees")
        staff_list = cur.fetchall()
        
        if staff_list:
            staff_options = {f"{s[1]} - Base: {s[2]:,.2f}": s for s in staff_list}
            with st.form("payroll_form"):
                selected_staff = st.selectbox("Select Employee" if lang == "en" else "اختر الموظف", list(staff_options.keys()))
                s_data = staff_options[selected_staff]
                
                pay_amount = st.number_input("Amount to Pay" if lang == "en" else "قيمة الصرف", value=float(s_data[2]), step=100.0)
                
                memo_default = f"Salary payment for {s_data[1]}" if lang == "en" else f"صرف راتب للموظف {s_data[1]}"
                pay_memo = st.text_input("Memo" if lang == "en" else "البيان", value=memo_default)
                
                if st.form_submit_button("Issue Payment" if lang == "en" else "تنفيذ الصرف", type="primary"):
                    # Check if payroll account exists
                    cur.execute("SELECT account_id FROM chart_of_accounts WHERE account_id = 5200")
                    if not cur.fetchone(): 
                        cur.execute("INSERT INTO chart_of_accounts (account_id, account_name, account_type) VALUES (5200, 'Payroll & Benefits', 'Expense')")
                    
                    cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (1000, %s, %s)", (pay_amount, pay_memo))
                    cur.execute("INSERT INTO general_ledger (account_id, debit, description) VALUES (5200, %s, %s)", (pay_amount, pay_memo))
                    
                    conn.commit()
                    st.success("✅ Payroll issued!" if lang == "en" else "✅ تم صرف الراتب بنجاح!")
                    time.sleep(1.5)
                    st.rerun()
                    
    conn.close()

def render_ledger(start_date, end_date):
    st.header("📖 System Ledger Records" if lang == "en" else "📖 سجلات دفتر الأستاذ العام")
    
    conn = get_connection()
    query = """
        SELECT * FROM general_ledger 
        WHERE DATE(transaction_date) >= %s AND DATE(transaction_date) <= %s 
        ORDER BY transaction_date DESC, entry_id DESC
    """
    df_ledger = pd.read_sql(query, conn, params=(start_date, end_date))
    
    if lang == "ar" and not df_ledger.empty: 
        df_ledger.columns = ["كود القيد", "تاريخ المعاملة", "كود الحساب", "مدين", "دائن", "البيان"]
        
    if not df_ledger.empty: 
        st.dataframe(df_ledger, use_container_width=True, hide_index=True)
        
    conn.close()

def render_financials(start_date, end_date):
    st.header("📑 Financial Statements" if lang == "en" else "📑 القوائم المالية")
    
    opt_is = "Income Statement (P&L)" if lang == "en" else "قائمة الدخل"
    opt_cf = "Cash Flow Statement" if lang == "en" else "التدفقات النقدية"
    opt_bs = "Balance Sheet" if lang == "en" else "الميزانية العمومية"
    
    statement_view = st.radio("Select Report:" if lang == "en" else "اختر التقرير:", [opt_is, opt_cf, opt_bs], horizontal=True)
    st.divider()
    
    conn = get_connection()
    
    # ---------------------------------------------
    # INCOME STATEMENT
    # ---------------------------------------------
    if statement_view == opt_is:
        st.subheader("Income Statement" if lang == "en" else "قائمة الدخل")
        
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
            rev_list = []
            exp_list = []
            tot_rev = 0.0
            tot_exp = 0.0
            
            for _, row in df_is.iterrows():
                acc_name_col = "Account" if lang == "en" else "الحساب"
                bal_col = "Balance" if lang == "en" else "الرصيد"
                
                if row['account_type'] == 'Revenue':
                    bal = row['total_credit'] - row['total_debit']
                    rev_list.append({acc_name_col: row['account_name'], bal_col: bal})
                    tot_rev += bal
                elif row['account_type'] == 'Expense':
                    bal = row['total_debit'] - row['total_credit']
                    exp_list.append({acc_name_col: row['account_name'], bal_col: bal})
                    tot_exp += bal
                    
            net_income = tot_rev - tot_exp
            
            st.write("### REVENUE" if lang == "en" else "### الإيرادات")
            st.dataframe(pd.DataFrame(rev_list), use_container_width=True)
            st.success(f"**Total Revenue:** {tot_rev:,.2f}" if lang == "en" else f"**إجمالي الإيرادات:** {tot_rev:,.2f}")
            
            st.write("### EXPENSES" if lang == "en" else "### المصروفات")
            st.dataframe(pd.DataFrame(exp_list), use_container_width=True)
            st.warning(f"**Total Expenses:** {tot_exp:,.2f}" if lang == "en" else f"**إجمالي المصروفات:** {tot_exp:,.2f}")
            
            if net_income >= 0: 
                st.info(f"### 🎯 NET INCOME: {net_income:,.2f}" if lang == "en" else f"### 🎯 صافي الربح: {net_income:,.2f}")
            else: 
                st.error(f"### 🔻 NET LOSS: {net_income:,.2f}" if lang == "en" else f"### 🔻 صافي الخسارة: {net_income:,.2f}")
        except Exception as e: 
            pass

    # ---------------------------------------------
    # CASH FLOW STATEMENT
    # ---------------------------------------------
    elif statement_view == opt_cf:
        st.subheader("Statement of Cash Flows (EGP)" if lang == "en" else "قائمة التدفقات النقدية (ج.م)")
        
        with st.expander("💳 Record New Cash Outflow" if lang == "en" else "💳 تسجيل مدفوعات نقدية جديدة", expanded=False):
            outflow_cats_en = { 
                "Rent & Facilities": [5100, "Expense"], 
                "Payroll & Benefits": [5200, "Expense"], 
                "Utilities": [5300, "Expense"], 
                "Taxes Paid": [5400, "Expense"], 
                "Logistics": [5500, "Expense"], 
                "Equipment": [1600, "Asset"] 
            }
            outflow_cats_ar = { 
                "الإيجار والمرافق": [5100, "Expense"], 
                "الرواتب والبدلات": [5200, "Expense"], 
                "المنافع (كهرباء، إنترنت)": [5300, "Expense"], 
                "ضرائب مدفوعة": [5400, "Expense"], 
                "شحن ولوجستيات": [5500, "Expense"], 
                "معدات وأصول": [1600, "Asset"] 
            }
            outflow_cats = outflow_cats_en if lang == "en" else outflow_cats_ar
            
            with st.form("outflow_form"):
                c_cat, c_amt = st.columns([2, 1])
                with c_cat:
                    sel_cat = st.selectbox("Category" if lang == "en" else "الفئة", list(outflow_cats.keys()))
                    desc = st.text_input("Memo" if lang == "en" else "البيان")
                with c_amt: 
                    amt = st.number_input("Amount (EGP)" if lang == "en" else "المبلغ (ج.م)", min_value=0.0, step=100.0)
                
                if st.form_submit_button("Record Payment" if lang == "en" else "تسجيل الدفع", type="primary"):
                    if amt > 0 and desc:
                        acc_id, acc_type = outflow_cats[sel_cat]
                        cur = conn.cursor()
                        
                        cur.execute("SELECT account_id FROM chart_of_accounts WHERE account_id = %s", (acc_id,))
                        if not cur.fetchone(): 
                            cur.execute("INSERT INTO chart_of_accounts (account_id, account_name, account_type) VALUES (%s, %s, %s)", (acc_id, sel_cat, acc_type))
                        
                        cur.execute("INSERT INTO general_ledger (account_id, credit, description) VALUES (1000, %s, %s)", (amt, desc))
                        cur.execute("INSERT INTO general_ledger (account_id, debit, description) VALUES (%s, %s, %s)", (acc_id, amt, desc))
                        
                        conn.commit()
                        st.rerun()
                        
        query_cf = """
            SELECT DATE(transaction_date) as date, description, debit AS cash_in, credit AS cash_out 
            FROM general_ledger 
            WHERE account_id = 1000 
            AND DATE(transaction_date) >= %s 
            AND DATE(transaction_date) <= %s 
            ORDER BY transaction_date DESC
        """
        df_cf = pd.read_sql(query_cf, conn, params=(start_date, end_date))
        
        if not df_cf.empty:
            c1, c2, c3 = st.columns(3)
            sum_in = df_cf['cash_in'].sum()
            sum_out = df_cf['cash_out'].sum()
            net_cf = sum_in - sum_out
            
            c1.success(f"**Cash In**\n### {sum_in:,.2f}" if lang == "en" else f"**نقد داخل**\n### {sum_in:,.2f}")
            c2.warning(f"**Cash Out**\n### {sum_out:,.2f}" if lang == "en" else f"**نقد خارج**\n### {sum_out:,.2f}")
            c3.info(f"**Net**\n### {net_cf:,.2f}" if lang == "en" else f"**الصافي**\n### {net_cf:,.2f}")
            
            def highlight_cash(col):
                if col.name == 'cash_in' or col.name == 'نقد داخل': 
                    return ['background-color: rgba(40, 167, 69, 0.2)' if val > 0 else '' for val in col]
                elif col.name == 'cash_out' or col.name == 'نقد خارج': 
                    return ['background-color: rgba(255, 193, 7, 0.2)' if val > 0 else '' for val in col]
                else: 
                    return ['' for val in col]
                    
            if lang == "ar": 
                df_cf.columns = ["التاريخ", "البيان", "نقد داخل", "نقد خارج"]
                
            styled_cf = df_cf.style.apply(highlight_cash, subset=['cash_in', 'cash_out'] if lang == 'en' else ['نقد داخل', 'نقد خارج'])
            st.dataframe(styled_cf, use_container_width=True, hide_index=True)

    # ---------------------------------------------
    # BALANCE SHEET
    # ---------------------------------------------
    elif statement_view == opt_bs:
        st.subheader("Real-Time Balance Sheet" if lang == "en" else "الميزانية العمومية الحالية")
        
        query_bs = """
            SELECT c.account_name, c.account_type, 
                   COALESCE(SUM(g.debit), 0) as total_debit, 
                   COALESCE(SUM(g.credit), 0) as total_credit 
            FROM chart_of_accounts c 
            LEFT JOIN general_ledger g ON c.account_id = g.account_id 
            AND DATE(g.transaction_date) <= %s 
            GROUP BY c.account_name, c.account_type
        """
        df_b = pd.read_sql(query_bs, conn, params=(end_date,))
        
        a_list = []
        l_list = []
        e_list = []
        
        t_a = 0
        t_l = 0
        t_e = 0
        rev = 0
        exp = 0
        
        for _, row in df_b.iterrows():
            acc_name_col = "Account" if lang == "en" else "الحساب"
            bal_col = "Balance" if lang == "en" else "الرصيد"
            
            if row['account_type'] == 'Asset': 
                bal = row['total_debit'] - row['total_credit']
                a_list.append({acc_name_col: row['account_name'], bal_col: bal})
                t_a += bal
            elif row['account_type'] == 'Liability': 
                bal = row['total_credit'] - row['total_debit']
                l_list.append({acc_name_col: row['account_name'], bal_col: bal})
                t_l += bal
            elif row['account_type'] == 'Equity': 
                bal = row['total_credit'] - row['total_debit']
                e_list.append({acc_name_col: row['account_name'], bal_col: bal})
                t_e += bal
            elif row['account_type'] == 'Revenue': 
                rev += (row['total_credit'] - row['total_debit'])
            elif row['account_type'] == 'Expense': 
                exp += (row['total_debit'] - row['total_credit'])
                
        # Calculate Retained Earnings
        ni = rev - exp
        retained_name = "Retained Earnings" if lang == "en" else "أرباح محتجزة"
        
        e_list.append({acc_name_col: retained_name, bal_col: ni})
        t_e += ni
        
        col_l, col_r = st.columns(2)
        with col_l: 
            st.write("### ASSETS" if lang == "en" else "### الأصول")
            st.dataframe(pd.DataFrame(a_list), hide_index=True)
            st.success(f"**Total: {t_a:,.2f}**" if lang == "en" else f"**الإجمالي: {t_a:,.2f}**")
        with col_r: 
            st.write("### LIAB & EQUITY" if lang == "en" else "### الخصوم وحقوق الملكية")
            st.dataframe(pd.DataFrame(l_list), hide_index=True)
            st.dataframe(pd.DataFrame(e_list), hide_index=True)
            st.warning(f"**Total: {t_l + t_e:,.2f}**" if lang == "en" else f"**الإجمالي: {t_l + t_e:,.2f}**")
            
    conn.close()

def render_analytics(start_date, end_date):
    st.header("📈 Master Analytics Dashboard" if lang == "en" else "📈 لوحة التحليلات الرئيسية")
    
    kpi_tab_name = "🎯 KPIs & Overview" if lang == "en" else "🎯 المؤشرات الرئيسية"
    growth_tab_name = "📊 Sales & Growth" if lang == "en" else "📊 المبيعات والنمو"
    heat_tab_name = "🔥 Activity Heatmap" if lang == "en" else "🔥 خريطة النشاط"
    
    dash_kpi, dash_growth, dash_heat = st.tabs([kpi_tab_name, growth_tab_name, heat_tab_name])
    conn = get_connection()
    
    with dash_kpi:
        COLOR_REVENUE = "#3b7285"
        COLOR_EXPENSE = "#f2b350"
        COLOR_PROFIT = "#ce4e5d"
        DONUT_COLORS = ["#2b6088", "#ce4e5d", "#013b5a", "#f2b350", "#21828f"]
        
        def create_sparkline_card(title, value, trend_data, bg_color):
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=trend_data, 
                mode='lines+markers', 
                line=dict(color='rgba(255,255,255,0.7)', width=2), 
                marker=dict(size=6, color='white')
            ))
            fig.add_trace(go.Indicator(
                mode="number", 
                value=value, 
                number={'font': {'color': 'white', 'size': 50}}, 
                title={'text': f"<span style='color:white; font-size:16px'>{title}</span>"}, 
                domain={'y': [0.2, 1], 'x': [0, 1]}
            ))
            fig.update_layout(
                paper_bgcolor=bg_color, 
                plot_bgcolor=bg_color, 
                height=220, 
                margin=dict(l=15, r=15, t=30, b=15), 
                xaxis=dict(showgrid=False, showticklabels=False), 
                yaxis=dict(showgrid=False, showticklabels=False)
            )
            return fig

        try:
            df_rev = pd.read_sql("SELECT DATE(transaction_date) as dt, SUM(credit) as total FROM general_ledger WHERE account_id = 4000 GROUP BY dt ORDER BY dt", conn)
            tot_rev = df_rev['total'].sum() if not df_rev.empty else 0.0
            rev_trend = df_rev['total'].tail(7).tolist() if not df_rev.empty else [0]
            
            df_exp = pd.read_sql("SELECT DATE(transaction_date) as dt, SUM(debit - credit) as total FROM general_ledger WHERE account_id >= 5000 GROUP BY dt ORDER BY dt", conn)
            tot_exp = df_exp['total'].sum() if not df_exp.empty else 0.0
            exp_trend = df_exp['total'].tail(7).tolist() if not df_exp.empty else [0]
            
            c1, c2, c3 = st.columns(3)
            with c1: 
                title = "Total Revenue" if lang == "en" else "إجمالي الإيرادات"
                st.plotly_chart(create_sparkline_card(title, tot_rev, rev_trend, COLOR_REVENUE), use_container_width=True)
            with c2: 
                title = "Total Expenses" if lang == "en" else "إجمالي المصروفات"
                st.plotly_chart(create_sparkline_card(title, tot_exp, exp_trend, COLOR_EXPENSE), use_container_width=True)
            with c3: 
                title = "Net Profit" if lang == "en" else "صافي الربح"
                st.plotly_chart(create_sparkline_card(title, tot_rev - tot_exp, rev_trend, COLOR_PROFIT), use_container_width=True)

            st.divider()
            c_scatter, c_pie = st.columns([2, 1]) 
            with c_scatter:
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
                        color_discrete_sequence=["#0c4063"], template="plotly_white", size_max=40
                    )
                    st.plotly_chart(fig_bubble, use_container_width=True)
            
            with c_pie:
                query_cat = """
                    SELECT category, SUM(total_value) as value 
                    FROM inventory_stock 
                    WHERE total_value > 0 
                    GROUP BY category
                """
                df_cat = pd.read_sql(query_cat, conn)
                if not df_cat.empty:
                    fig_donut = px.pie(
                        df_cat, names="category", values="value", hole=0.4, 
                        color_discrete_sequence=DONUT_COLORS
                    )
                    st.plotly_chart(fig_donut, use_container_width=True)
        except Exception as e: 
            pass

    with dash_growth:
        query_daily = """
            SELECT DATE(transaction_date) as "Date", SUM(credit) as "Revenue" 
            FROM general_ledger 
            WHERE account_id = 4000 
            GROUP BY DATE(transaction_date) 
            ORDER BY "Date"
        """
        df_daily = pd.read_sql(query_daily, conn)
        if not df_daily.empty: 
            fig_area = px.area(df_daily, x="Date", y="Revenue", template="plotly_white", color_discrete_sequence=[COLOR_REVENUE])
            st.plotly_chart(fig_area, use_container_width=True)

    with dash_heat:
        query_heat = """
            SELECT TRIM(TO_CHAR(g.transaction_date, 'Day')) as "Day", 
                   i.category as "Category", 
                   COUNT(g.entry_id) as "Vol" 
            FROM general_ledger g 
            JOIN inventory_stock i ON g.description LIKE '%' || i.product_id || '%' 
            WHERE g.account_id = 4000 
            GROUP BY "Day", i.category
        """
        df_heat = pd.read_sql(query_heat, conn)
        if not df_heat.empty: 
            fig_heat = px.density_heatmap(df_heat, x="Day", y="Category", z="Vol", color_continuous_scale="Blues")
            st.plotly_chart(fig_heat, use_container_width=True)
            
    conn.close()

def render_tax_center(start_date, end_date):
    st.header("🇪🇬 Comprehensive Tax Center" if lang == "en" else "🇪🇬 المركز الضريبي الشامل")
    
    conn = get_connection()
    try:
        df_rev = pd.read_sql("SELECT SUM(credit - debit) as total FROM general_ledger WHERE account_id = 4000 AND DATE(transaction_date) >= %s AND DATE(transaction_date) <= %s", conn, params=(start_date, end_date))
        total_revenue = df_rev['total'].iloc[0] if pd.notnull(df_rev['total'].iloc[0]) else 0.0
        
        df_exp = pd.read_sql("SELECT SUM(debit - credit) as total FROM general_ledger WHERE account_id >= 5000 AND DATE(transaction_date) >= %s AND DATE(transaction_date) <= %s", conn, params=(start_date, end_date))
        total_expenses = df_exp['total'].iloc[0] if pd.notnull(df_exp['total'].iloc[0]) else 0.0
        
        df_vat = pd.read_sql("SELECT SUM(credit - debit) as total FROM general_ledger WHERE account_id = 2200 AND DATE(transaction_date) >= %s AND DATE(transaction_date) <= %s", conn, params=(start_date, end_date))
        vat_collected = df_vat['total'].iloc[0] if pd.notnull(df_vat['total'].iloc[0]) else 0.0
        
        df_payroll = pd.read_sql("SELECT SUM(debit - credit) as total FROM general_ledger WHERE account_id = 5200 AND DATE(transaction_date) >= %s AND DATE(transaction_date) <= %s", conn, params=(start_date, end_date))
        total_payroll = df_payroll['total'].iloc[0] if pd.notnull(df_payroll['total'].iloc[0]) else 0.0

        net_profit = total_revenue - total_expenses
        corporate_tax_liability = (net_profit * 0.225) if net_profit > 0 else 0.0
        payroll_tax_liability = total_payroll * 0.10 
        wht_advance_paid = total_revenue * 0.01 

        tab_names = [
            "🛒 VAT (14%)" if lang == "en" else "🛒 القيمة المضافة", 
            "🏢 Corporate Tax" if lang == "en" else "🏢 أرباح تجارية", 
            "👥 Payroll Tax" if lang == "en" else "👥 كسب العمل",
            "✂️ Withholding (WHT)" if lang == "en" else "✂️ خصم المنبع",
            "📄 Declaration" if lang == "en" else "📄 الإقرار الموحد"
        ]
        tax_vat, tax_corp, tax_payroll, tax_wht, tax_master = st.tabs(tab_names)

        with tax_vat:
            st.metric("Total VAT Owed" if lang == "en" else "القيمة المضافة المستحقة", f"{vat_collected:,.2f} EGP")
            query_vat_details = """
                SELECT DATE(transaction_date) as "Date", description as "Detail", credit as "VAT (EGP)" 
                FROM general_ledger 
                WHERE account_id = 2200 AND credit > 0 
                AND DATE(transaction_date) >= %s AND DATE(transaction_date) <= %s 
                ORDER BY transaction_date DESC LIMIT 10
            """
            df_vat_details = pd.read_sql(query_vat_details, conn, params=(start_date, end_date))
            if lang == "ar" and not df_vat_details.empty: 
                df_vat_details.columns = ["التاريخ", "التفاصيل", "الضريبة (ج.م)"]
            if not df_vat_details.empty: 
                st.dataframe(df_vat_details, use_container_width=True, hide_index=True)

        with tax_corp:
            c1, c2, c3 = st.columns(3)
            c1.metric("Net Taxable Profit" if lang == "en" else "صافي الربح", f"{net_profit:,.2f} EGP")
            c2.metric("WHT Advance Credit" if lang == "en" else "رصيد خصم المنبع", f"({wht_advance_paid:,.2f}) EGP")
            final_corp_tax = corporate_tax_liability - wht_advance_paid
            c3.metric("Final Corp Tax Due" if lang == "en" else "الصافي المستحق للضرائب", f"{final_corp_tax if final_corp_tax > 0 else 0:,.2f} EGP")
            
            query_exp_details = """
                SELECT c.account_name as "Expense Category", SUM(g.debit - g.credit) as "Total Deducted" 
                FROM general_ledger g 
                JOIN chart_of_accounts c ON g.account_id = c.account_id 
                WHERE c.account_type = 'Expense' 
                AND DATE(g.transaction_date) >= %s 
                AND DATE(g.transaction_date) <= %s 
                GROUP BY c.account_name 
                ORDER BY "Total Deducted" DESC
            """
            df_exp_details = pd.read_sql(query_exp_details, conn, params=(start_date, end_date))
            if lang == "ar" and not df_exp_details.empty: 
                df_exp_details.columns = ["بند المصروف", "الإجمالي المخصوم"]
            if not df_exp_details.empty: 
                st.dataframe(df_exp_details, use_container_width=True, hide_index=True)

        with tax_payroll:
            p1, p2 = st.columns(2)
            p1.metric("Total Payroll" if lang == "en" else "إجمالي الرواتب", f"{total_payroll:,.2f} EGP")
            p2.metric("Est. Tax Withheld" if lang == "en" else "الضريبة المحتجزة", f"{payroll_tax_liability:,.2f} EGP")

        with tax_wht:
            w1, w2 = st.columns(2)
            w1.metric("Total Revenue" if lang == "en" else "إجمالي الإيرادات", f"{total_revenue:,.2f} EGP")
            w2.metric("WHT Credits (1%)" if lang == "en" else "رصيد خصم المنبع (1%)", f"{wht_advance_paid:,.2f} EGP")

        with tax_master:
            tax_report = pd.DataFrame({
                "Line Item" if lang == "en" else "البند": [
                    "Gross Revenue" if lang == "en" else "إجمالي الإيرادات", 
                    "Deductible Expenses" if lang == "en" else "المصروفات المعتمدة", 
                    "Net Profit" if lang == "en" else "صافي الربح", 
                    "VAT Collected" if lang == "en" else "ضريبة القيمة المضافة", 
                    "Gross Corporate Tax" if lang == "en" else "إجمالي ضريبة الأرباح", 
                    "Less: WHT Advance Paid" if lang == "en" else "يخصم: ضريبة الخصم من المنبع", 
                    "Net Corporate Tax Due" if lang == "en" else "صافي ضريبة الأرباح المستحقة", 
                    "Employee Payroll Tax" if lang == "en" else "ضريبة كسب العمل"
                ],
                "Amount" if lang == "en" else "القيمة": [
                    f"{total_revenue:,.2f}", 
                    f"({total_expenses:,.2f})", 
                    f"{net_profit:,.2f}", 
                    f"{vat_collected:,.2f}", 
                    f"{corporate_tax_liability:,.2f}", 
                    f"({wht_advance_paid:,.2f})", 
                    f"{(corporate_tax_liability - wht_advance_paid) if (corporate_tax_liability - wht_advance_paid) > 0 else 0:,.2f}", 
                    f"{payroll_tax_liability:,.2f}"
                ]
            })
            st.table(tax_report)
            
    except Exception as e: 
        pass
        
    conn.close()

def render_logistics():
    st.header("🚚 Supplier & Logistics Management" if lang == "en" else "🚚 إدارة الموردين واللوجستيات")
    
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id SERIAL PRIMARY KEY, 
            company_name VARCHAR(150), 
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
            freight_cost NUMERIC DEFAULT 0
        )
    """)
    conn.commit()

    tab_names = ["🏭 Factory Directory" if lang == "en" else "🏭 دليل المصانع", "🚢 Active Shipments" if lang == "en" else "🚢 الشحنات النشطة"]
    log_sup, log_ship = st.tabs(tab_names)
    
    with log_sup:
        with st.expander("➕ Add Supplier" if lang == "en" else "➕ إضافة مورد"):
            with st.form("sup_form"):
                s_name = st.text_input("Company Name" if lang == "en" else "اسم الشركة")
                if st.form_submit_button("Save" if lang == "en" else "حفظ"):
                    cur.execute("INSERT INTO suppliers (company_name) VALUES (%s)", (s_name,))
                    conn.commit()
                    st.rerun()
                    
        df_sup = pd.read_sql("SELECT supplier_id as ID, company_name as Company FROM suppliers", conn)
        if lang == "ar" and not df_sup.empty: 
            df_sup.columns = ["الكود", "اسم المصنع"]
        st.dataframe(df_sup, hide_index=True)

    with log_ship:
        cur.execute("SELECT supplier_id, company_name FROM suppliers")
        sups = cur.fetchall()
        
        with st.expander("🚢 Log Shipment" if lang == "en" else "🚢 تسجيل شحنة"):
            if sups:
                sup_dict = {s[1]: s[0] for s in sups}
                with st.form("ship_form"):
                    sel_sup = st.selectbox("Supplier" if lang == "en" else "المورد", list(sup_dict.keys()))
                    c_num = st.text_input("Container #" if lang == "en" else "رقم الحاوية/البوليصة")
                    status_options = ["In Customs", "In Transit", "Delivered"] if lang == "en" else ["في الجمارك", "في الطريق", "تم التسليم"]
                    stat = st.selectbox("Status" if lang == "en" else "الحالة", status_options)
                    
                    if st.form_submit_button("Log" if lang == "en" else "تسجيل"):
                        cur.execute("INSERT INTO shipments (supplier_id, container_number, status) VALUES (%s, %s, %s)", (sup_dict[sel_sup], c_num, stat))
                        conn.commit()
                        st.rerun()
                        
        query_ship = """
            SELECT s.company_name as Supplier, 
                   sh.container_number as Container, 
                   sh.status as Status 
            FROM shipments sh 
            JOIN suppliers s ON sh.supplier_id = s.supplier_id
        """
        df_ship = pd.read_sql(query_ship, conn)
        
        if lang == "ar" and not df_ship.empty: 
            df_ship.columns = ["المورد", "الحاوية", "الحالة"]
        st.dataframe(df_ship, hide_index=True)
        
    conn.close()


# ==========================================
# 5. MAIN ROUTING & LOGIN LOGIC
# ==========================================

if not st.session_state["logged_in"]:
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.title("🔒 System Login" if lang == "en" else "🔒 تسجيل الدخول")
    st.caption("Wholesale Enterprise Management" if lang == "en" else "نظام إدارة تجارة الجملة")
    
    with st.form("login_form"):
        input_user = st.text_input("Username" if lang == "en" else "اسم المستخدم")
        input_pass = st.text_input("Password" if lang == "en" else "كلمة المرور", type="password")
        
        if st.form_submit_button("Login" if lang == "en" else "دخول", type="primary"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT role FROM system_users WHERE username = %s AND password = %s", (input_user, input_pass))
            user_data = cur.fetchone()
            
            if user_data:
                st.session_state["logged_in"] = True
                st.session_state["username"] = input_user
                st.session_state["role"] = user_data[0]
                st.rerun()
            else:
                st.error("Incorrect username or password." if lang == "en" else "خطأ في اسم المستخدم أو كلمة المرور.")
            conn.close()
    
    st.write("")
    if st.button("🌐 Switch Language / تغيير اللغة"):
        st.session_state["language"] = None
        st.rerun()
        
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # --- The Sidebar Navigation ---
    with st.sidebar:
        st.title("🧶 Wholesale ERP" if lang == "en" else "🧶 إدارة الجملة")
        st.caption(f"Welcome, {st.session_state['username']}" if lang == "en" else f"مرحباً، {st.session_state['username']}")
        
        if st.button("🚪 Logout" if lang == "en" else "🚪 تسجيل خروج"):
            st.session_state["logged_in"] = False
            st.session_state["role"] = ""
            st.session_state["username"] = ""
            st.rerun()
            
        st.divider()
        
        # Bilingual Navigation Mapping
        if st.session_state["role"] == "Owner":
            menu_en = [
                "📈 Analytics Dashboard", 
                "📦 Inventory Management", 
                "💰 Sales & Invoicing", 
                "🚚 Suppliers & Logistics", 
                "👥 HR & Payroll", 
                "📖 General Ledger", 
                "📑 Financial Statements", 
                "🇪🇬 Tax Center"
            ]
            menu_ar = [
                "📈 لوحة التحليلات", 
                "📦 إدارة المخزون", 
                "💰 المبيعات والفواتير", 
                "🚚 إدارة الموردين", 
                "👥 الموارد البشرية", 
                "📖 دفتر الأستاذ العام", 
                "📑 القوائم المالية", 
                "🇪🇬 المركز الضريبي"
            ]
        else:
            menu_en = ["💰 Sales & Invoicing"]
            menu_ar = ["💰 المبيعات والفواتير"]
            
        active_menu = menu_en if lang == "en" else menu_ar
        page = st.radio("Navigation Menu" if lang == "en" else "قائمة التنقل", active_menu)
        
        st.divider()
        st.write("**📅 Time Filter**" if lang == "en" else "**📅 تصفية الوقت**")
        today = datetime.date.today()
        first_day_of_month = today.replace(day=1)
        start_date = st.date_input("Start Date" if lang == "en" else "تاريخ البدء", first_day_of_month)
        end_date = st.date_input("End Date" if lang == "en" else "تاريخ الانتهاء", today)

    # --- Page Routing ---
    page_index = active_menu.index(page)
    
    if st.session_state["role"] == "Owner":
        if page_index == 0:
            render_analytics(start_date, end_date)
        elif page_index == 1:
            render_inventory()
        elif page_index == 2:
            render_sales(is_owner=True)
        elif page_index == 3:
            render_logistics()
        elif page_index == 4:
            render_hr()
        elif page_index == 5:
            render_ledger(start_date, end_date)
        elif page_index == 6:
            render_financials(start_date, end_date)
        elif page_index == 7:
            render_tax_center(start_date, end_date)
    else:
        if page_index == 0:
            render_sales(is_owner=False)