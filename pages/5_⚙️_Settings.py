import streamlit as st
from services.supabase_client import db

if "user_id" not in st.session_state:
    st.warning("Secure session missing. Redirecting to main login...")
    st.switch_page("app.py")
    st.stop()

st.title("System Settings & Profile")

res = db.table("user_profiles").select("*").eq("user_id", st.session_state.user_id).execute()
if res.data:
    profile = res.data[0]
    st.info("The AI updates these fields autonomously, but you can manually override them here.")
    
    with st.form("profile_settings"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Name", value=profile.get("name") or "")
            occ = st.text_input("Occupation", value=profile.get("occupation") or "")
            lang = st.text_input("Preferred Language", value=profile.get("preferred_language") or "English")
        with c2:
            tz = st.text_input("Timezone", value=profile.get("timezone") or "UTC")
            style = st.selectbox("Communication Style", ["Concise", "Detailed", "Casual", "Direct"])
            
        if st.form_submit_button("Save Override"):
            db.table("user_profiles").update({"name": name, "occupation": occ, "preferred_language": lang, "timezone": tz, "communication_style": style}).eq("user_id", st.session_state.user_id).execute()
            st.success("Profile manually updated.")

st.divider()
if st.button("Log Out / Lock System", type="primary"):
    st.session_state.clear()
    st.rerun()
