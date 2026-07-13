import psycopg2

try:
    # Connect to your local PostgreSQL database
    connection = psycopg2.connect(
        host="localhost", database="yarn_erp", user="postgres",
        password="nat", port="5432"
    )
    cursor = connection.cursor()

    # The Wholesale Sale Details (in EGP)
    sale_amount_egp = 50000.00  # Selling 50,000 EGP worth of yarn
    vat_rate = 0.14  # Standard 14% Egyptian VAT
    vat_amount_egp = sale_amount_egp * vat_rate
    total_cash_received_egp = sale_amount_egp + vat_amount_egp
    cost_of_goods_egp = 30000.00  # It cost you 30,000 EGP to manufacture/buy this batch
    description = "Wholesale Yarn Bulk Order - Invoice #002"

    # --- THE AUTOMATED JOURNAL ENTRIES (EGP) ---
    
    # 1. Debit Cash (Total received: 57,000 EGP)
    cursor.execute("""
        INSERT INTO general_ledger (account_id, debit, description)
        VALUES (1000, %s, %s)
    """, (total_cash_received_egp, description))

    # 2. Credit Sales Revenue (Base price: 50,000 EGP)
    cursor.execute("""
        INSERT INTO general_ledger (account_id, credit, description)
        VALUES (4000, %s, %s)
    """, (sale_amount_egp, description))

    # 3. Credit VAT Payable (The tax collected for the ETA: 7,000 EGP)
    cursor.execute("""
        INSERT INTO general_ledger (account_id, credit, description)
        VALUES (2200, %s, %s)
    """, (vat_amount_egp, description))

    # 4. Debit Cost of Goods Sold (COGS: 30,000 EGP)
    cursor.execute("""
        INSERT INTO general_ledger (account_id, debit, description)
        VALUES (5000, %s, %s)
    """, (cost_of_goods_egp, description))

    # 5. Credit Yarn Inventory (Reducing the asset by 30,000 EGP)
    cursor.execute("""
        INSERT INTO general_ledger (account_id, credit, description)
        VALUES (1200, %s, %s)
    """, (cost_of_goods_egp, description))

    # COMMIT THE TRANSACTION to save it to the database permanently
    connection.commit()
    print(f"Success! Sale recorded. {total_cash_received_egp} EGP deposited, journal entries balanced.")

    cursor.close()
    connection.close()

except Exception as error:
    print("Transaction failed:", error)