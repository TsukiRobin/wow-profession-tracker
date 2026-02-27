import streamlit as st
import mysql.connector

st.set_page_config(page_title="WoW Profession Tracker", page_icon="⚔️")

def connect_db():
    return mysql.connector.connect(
        host="wowfarming-professionfarmtracking.d.aivencloud.com",
        port=24201,
        user="avnadmin",
        password="AVNS_J77xD9NXMgJreUYsKKs", # Use the one from the Aiven dashboard
        database="defaultdb",           # Or WoW_Farming if you created it
        ssl_ca="ca.pem",                # Aiven requires SSL; see note below
        ssl_verify_cert=True
    )

# --- USER SYSTEM LOGIC ---
def init_user_progress(username):
    db = connect_db()
    cursor = db.cursor()
    # Check if user already exists in progress table
    cursor.execute("SELECT 1 FROM user_progress WHERE username = %s LIMIT 1", (username,))
    if not cursor.fetchone():
        # Copy master list to user progress
        cursor.execute("""
            INSERT INTO user_progress (username, item_id, quantity_collected)
            SELECT %s, id, 0 FROM profession_master
        """, (username,))
        db.commit()
    db.close()

# --- DATA FETCHING ---
def get_user_data(username, profession):
    db = connect_db()
    cursor = db.cursor(dictionary=True)
    query = """
        SELECT pm.item_name, pm.quantity_needed, up.quantity_collected, pm.id
        FROM profession_master pm
        JOIN user_progress up ON pm.id = up.item_id
        WHERE up.username = %s AND pm.profession = %s
    """
    cursor.execute(query, (username, profession))
    result = cursor.fetchall()
    db.close()
    return result

# --- SIDEBAR ---
st.sidebar.title("👤 User Session")
user = st.sidebar.text_input("Enter Username to load/save", placeholder="e.g. Thrall")

if user:
    init_user_progress(user)
    
    st.sidebar.divider()
    prof_list = ["Jewelcrafting", "Blacksmithing", "Alchemy", "Tailoring"]
    selected_prof = st.sidebar.selectbox("Profession", prof_list)
    
    items = get_user_data(user, selected_prof)
    
    st.sidebar.subheader("Log Progress")
    item_to_update = st.sidebar.selectbox("Item", [i['item_name'] for i in items])
    qty = st.sidebar.number_input("Amount", min_value=1)
    
    if st.sidebar.button("Add to Stash"):
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("""
            UPDATE user_progress up
            JOIN profession_master pm ON up.item_id = pm.id
            SET up.quantity_collected = up.quantity_collected + %s
            WHERE up.username = %s AND pm.item_name = %s AND pm.profession = %s
        """, (qty, user, item_to_update, selected_prof))
        db.commit()
        db.close()
        st.rerun()

    if st.sidebar.button("Reset My Progress"):
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("""
            UPDATE user_progress up
            JOIN profession_master pm ON up.item_id = pm.id
            SET up.quantity_collected = 0
            WHERE up.username = %s AND pm.profession = %s
        """, (user, selected_prof))
        db.commit()
        db.close()
        st.rerun()

    # --- MAIN UI ---
    st.title(f"⛏️ {user}'s {selected_prof} Progress")
    
    for row in items:
        percent = min(1.0, row['quantity_collected'] / row['quantity_needed'])
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{row['item_name']}** ({row['quantity_collected']}/{row['quantity_needed']})")
            st.progress(percent)
        with col2:
            remaining = row['quantity_needed'] - row['quantity_collected']
            if remaining <= 0: st.success("DONE")
            else: st.info(f"{remaining} left")

else:
    st.info("Please enter a username in the sidebar to start tracking.")