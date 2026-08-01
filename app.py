import streamlit as st
import requests
import os

# 1. Use Environment Variables for production readiness
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000")

st.set_page_config(
    page_title="Company AI Portal",
    page_icon="🏢",
    layout="centered"
)

st.title("🏢 Company Internal AI Portal")
st.markdown("Ask questions about company policies, guidelines, and internal documents.")

# 2. Add a sidebar with a Clear Chat button
with st.sidebar:
    st.header("Settings")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# Navigation tabs
tab1, tab2 = st.tabs(["💬 Ask AI", "📁 Add Document"])

with tab1:
    st.header("Chat with Company AI")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 3. Display chat messages AND sources from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Render sources if they exist for this message
            if message.get("sources"):
                with st.expander("View Sources & References"):
                    for src in message["sources"]:
                        st.json(src)

    # Accept user input
    if prompt := st.chat_input("What is our remote work policy?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Send request to FastAPI backend
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # 4. Send chat history to backend for context awareness
                    payload = {
                        "question": prompt,
                        "chat_history": [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
                    }
                    
                    # 5. Add a timeout to prevent infinite hanging
                    response = requests.post(
                        f"{BACKEND_URL}/ask",
                        json=payload,
                        timeout=30 
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        answer = data.get("answer", "No answer provided.")
                        sources = data.get("sources", [])
                        
                        st.markdown(answer)
                        
                        if sources:
                            with st.expander("View Sources & References"):
                                for idx, src in enumerate(sources):
                                    st.json(src)
                        
                        # 6. Save BOTH answer and sources to chat history
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": answer,
                            "sources": sources
                        })
                    else:
                        st.error(f"Error from server: {response.status_code} - {response.text}")
                        
                except requests.exceptions.Timeout:
                    st.error("The server took too long to respond. Please try again.")
                except Exception as e:
                    st.error(f"Could not connect to backend server. Make sure FastAPI is running. Error: {str(e)}")

with tab2:
    st.header("Add New Company Document")
    st.markdown("Upload a file or paste text to make it searchable by the AI.")
    
    # 7. Add File Uploader for better UX
    uploaded_file = st.file_uploader("Upload Document (PDF, TXT, DOCX)", type=["pdf", "txt", "docx"])
    
    st.markdown("--- OR ---")
    
    doc_content = st.text_area("Paste Document Content", height=150, placeholder="Type or paste company policy text here...")
    doc_title = st.text_input("Document Title / Reference", placeholder="e.g., Remote Work Policy 2026")
    
    if st.button("Upload & Vectorize"):
        if uploaded_file is not None:
            with st.spinner("Uploading and processing file..."):
                try:
                    # Note: Your FastAPI backend needs an endpoint that accepts multipart/form-data for this to work
                    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                    data = {"title": doc_title if doc_title else uploaded_file.name}
                    
                    res = requests.post(f"{BACKEND_URL}/upload-document", files=files, data=data, timeout=60)
                    if res.status_code == 200:
                        st.success(f"File '{uploaded_file.name}' vectorized successfully!")
                    else:
                        st.error(f"Failed to upload file: {res.text}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
                    
        elif doc_content.strip():
            with st.spinner("Processing and vectorizing text..."):
                try:
                    payload = {
                        "content": doc_content,
                        "metadata": {"title": doc_title if doc_title else "Untitled Policy"}
                    }
                    res = requests.post(f"{BACKEND_URL}/add-document", json=payload, timeout=30)
                    
                    if res.status_code == 200:
                        st.success("Text document added and vectorized successfully!")
                        # Optional: Clear the text area after success using st.rerun() or session state
                    else:
                        st.error(f"Failed to add document: {res.text}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
        else:
            st.warning("Please upload a file or enter some text before submitting.")