import streamlit as st
import requests
import os
import pypdf
import docx

BACKEND_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000")
POSITIONS = ["HR", "IT", "Finance", "Sales", "Engineering"] # Define your positions here

st.set_page_config(page_title="Company AI Portal", page_icon="🏢", layout="centered")

# --- Session State Initialization ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "position" not in st.session_state:
    st.session_state.position = None
if "name" not in st.session_state:
    st.session_state.name = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Login Screen ---
if not st.session_state.logged_in:
    st.title("🏢 Company AI Portal Login")
    
    login_type = st.radio("Login As:", ["Employee", "Admin"], horizontal=True)
    
    with st.form("login_form"):
        if login_type == "Employee":
            username = st.text_input("Username / Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            payload = {
                "username": username if login_type == "Employee" else "admin",
                "password": password,
                "is_admin": login_type == "Admin"
            }
            try:
                res = requests.post(f"{BACKEND_URL}/login", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.logged_in = True
                    st.session_state.role = data["role"]
                    st.session_state.position = data["position"]
                    st.session_state.name = data["name"]
                    st.rerun()
                else:
                    try:
                        error_msg = res.json().get("detail", "Login failed")
                    except:
                        error_msg = res.text
                    st.error(f"Login Error: {error_msg}")
            except Exception as e:
                st.error("Could not connect to server. Is the backend running?")
    st.stop()

# --- Main App (Logged In) ---
with st.sidebar:
    st.write(f"👤 **Welcome, {st.session_state.name}**")
    st.write(f"🏷️ **Role:** {st.session_state.role}")
    if st.session_state.role == "Employee":
        st.write(f"💼 **Position:** {st.session_state.position}")
    
    st.divider()
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

st.title("🏢 Company Internal AI Portal")

# --- Determine Tabs based on Role ---
if st.session_state.role == "Admin":
    tabs = st.tabs(["💬 Ask AI", "📁 Add Document", "👥 Manage Employees"])
else:
    tabs = st.tabs(["💬 Ask AI"])

# --- TAB 1: Chat (For Both) ---
with tabs[0]:
    st.header("Chat with Company AI")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("View Sources & References"):
                    for src in message["sources"]:
                        st.json(src)

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    payload = {
                        "question": prompt,
                        "user_position": st.session_state.position
                    }
                    response = requests.post(f"{BACKEND_URL}/ask", json=payload, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        answer = data.get("answer", "No answer provided.")
                        sources = data.get("sources", [])
                        
                        st.markdown(answer)
                        if sources:
                            with st.expander("View Sources & References"):
                                for src in sources:
                                    st.json(src)
                        
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": answer,
                            "sources": sources
                        })
                    else:
                        st.error(f"Error {response.status_code}: {response.text}")
                except Exception as e:
                    st.error(f"Could not connect to backend server. Details: {str(e)}")

# --- TAB 2: Add Document (Admin Only) ---
if st.session_state.role == "Admin":
    with tabs[1]:
        st.header("Add New Company Document")
        
        # --- NEW: File Uploader Logic ---
        uploaded_file = st.file_uploader("Upload a document (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
        
        extracted_text = ""
        default_title = ""
        
        if uploaded_file is not None:
            default_title = uploaded_file.name
            try:
                if uploaded_file.name.endswith(".txt"):
                    extracted_text = uploaded_file.read().decode("utf-8")
                elif uploaded_file.name.endswith(".pdf"):
                    pdf_reader = pypdf.PdfReader(uploaded_file)
                    for page in pdf_reader.pages:
                        extracted_text += page.extract_text() + "\n"
                elif uploaded_file.name.endswith(".docx"):
                    doc = docx.Document(uploaded_file)
                    for para in doc.paragraphs:
                        extracted_text += para.text + "\n"
                st.success("File read successfully! You can review/edit the text below before uploading.")
            except Exception as e:
                st.error(f"Error reading file: {e}")
        # --------------------------------

        # The text area now defaults to the extracted text if a file was uploaded
        doc_content = st.text_area("Document Content (Paste text or review uploaded file)", value=extracted_text, height=200)
        doc_title = st.text_input("Document Title / Reference", value=default_title)
        
        allowed_roles = st.multiselect(
            "Who can view this policy?", 
            ["All"] + POSITIONS, 
            default=["All"]
        )
        
        if st.button("Upload & Vectorize"):
            if doc_content.strip():
                with st.spinner("Processing..."):
                    payload = {
                        "content": doc_content,
                        "metadata": {
                            "title": doc_title if doc_title else "Untitled Policy",
                            "allowed_positions": allowed_roles
                        }
                    }
                    res = requests.post(f"{BACKEND_URL}/add-document", json=payload)
                    if res.status_code == 200:
                        st.success("Document added successfully!")
                    else:
                        st.error(f"Failed to add document: {res.text}")
            else:
                st.warning("Please enter some text or upload a valid document.")

# --- TAB 3: Manage Employees (Admin Only) ---
if st.session_state.role == "Admin":
    with tabs[2]:
        st.header("👥 Employee Management")
        
        with st.expander("➕ Add New Employee", expanded=False):
            with st.form("add_user_form"):
                new_name = st.text_input("Full Name")
                new_username = st.text_input("Username / Email")
                new_password = st.text_input("Password", type="password")
                new_position = st.selectbox("Position", POSITIONS)
                
                if st.form_submit_button("Create Employee"):
                    res = requests.post(f"{BACKEND_URL}/admin/users", json={
                        "name": new_name, "username": new_username, 
                        "password": new_password, "position": new_position
                    })
                    if res.status_code == 200:
                        st.success("Employee created!")
                    else:
                        try:
                            error_msg = res.json().get("detail", "Unknown error")
                        except:
                            error_msg = res.text
                        st.error(f"Failed to create user: {error_msg}")

        st.divider()
        
        st.subheader("Employee List")
        search_query = st.text_input("🔍 Search by Employee Name")
        
        try:
            users_res = requests.get(f"{BACKEND_URL}/admin/users")
            if users_res.status_code == 200:
                users = users_res.json()
                
                if search_query:
                    users = [u for u in users if search_query.lower() in u["name"].lower()]
                
                for user in users:
                    col1, col2, col3 = st.columns([3, 2, 1])
                    col1.write(f"**{user['name']}** ({user['username']})")
                    col2.write(f"💼 {user['position']}")
                    if col3.button("❌ Delete", key=f"del_{user['id']}"):
                        del_res = requests.delete(f"{BACKEND_URL}/admin/users/{user['id']}")
                        if del_res.status_code == 200:
                            st.success("Deleted! Refreshing...")
                            st.rerun()
            else:
                st.error("Could not load employees.")
        except Exception as e:
            st.error("Backend connection error.")