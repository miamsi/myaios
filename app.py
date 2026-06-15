import streamlit as st
from services.supabase_client import db

st.set_page_config(page_title="AI OS", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("System Login")
    st.info("Please enter your master password to access the OS.")
    with st.form("login"):
        pwd = st.text_input("Password", type="password")
        if st.form_submit_button("Unlock"):
            if pwd == "letmein":
                st.session_state.authenticated = True
                # Fetch or create the Master user
                master_email = "admin@ai-os.local"
                res = db.table("users").select("id").eq("email", master_email).execute()
                if res.data:
                    st.session_state.user_id = res.data[0]["id"]
                else:
                    new_user = db.table("users").insert({"email": master_email}).execute()
                    uid = new_user.data[0]["id"]
                    db.table("user_profiles").insert({"user_id": uid, "name": "Admin"}).execute()
                    st.session_state.user_id = uid
                st.rerun()
            else:
                st.error("Access Denied.")
    st.stop()

pg = st.navigation([
    st.Page("pages/1_💬_Chat.py", title="Interface"),
    st.Page("pages/2_📚_Knowledge.py", title="Knowledge"),
    st.Page("pages/3_✅_Tasks.py", title="Tasks"),
    st.Page("pages/4_🧠_Memory.py", title="Memory"),
    st.Page("pages/5_⚙️_Settings.py", title="Settings")
])
pg.run()
