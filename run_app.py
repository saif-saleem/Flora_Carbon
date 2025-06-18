import streamlit as st
from app.rag_chat import get_answer

st.set_page_config(page_title="Carbon GPT", layout="wide")
st.title("🌿 Carbon GPT - Ask about carbon standards")

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_query" not in st.session_state:
    st.session_state.last_query = None
if "chat_mode" not in st.session_state:
    st.session_state.chat_mode = False
if "followup_input" not in st.session_state:
    st.session_state.followup_input = ""
if "main_query" not in st.session_state:
    st.session_state.main_query = ""

# Button to reset conversation
if st.button("🆕 New Chat"):
    st.session_state.chat_history = []
    st.session_state.last_query = None
    st.session_state.chat_mode = False
    st.session_state.followup_input = ""
    st.session_state.main_query = ""
    st.rerun()

# Main input
st.session_state.main_query = st.text_input("🔍 Ask your question:", st.session_state.main_query)

# Search button
if st.button("🔎 Search"):
    if st.session_state.main_query:
        with st.spinner("Generating answer..."):
            answer, sources, clarification = get_answer(st.session_state.main_query)
            if clarification:
                st.session_state.chat_history.append(("clarification", clarification))
                st.session_state.last_query = st.session_state.main_query
                st.session_state.chat_mode = True
            else:
                st.session_state.chat_history.append(("question", st.session_state.main_query))
                st.session_state.chat_history.append(("answer", answer))
                if sources:
                    st.session_state.chat_history.append(("sources", sources))
                st.session_state.last_query = st.session_state.main_query
                st.session_state.chat_mode = True

# Display conversation
for entry_type, entry in st.session_state.chat_history:
    if entry_type == "question":
        st.markdown(f"**🧑 You:** {entry}")
    elif entry_type == "clarification":
        st.warning(f"🔍 {entry}")
    elif entry_type == "followup":
        st.markdown(f"**🧑 Follow-up:** {entry}")
    elif entry_type == "answer":
        st.success(f"🧠 **Answer:**\n\n{entry}")
    elif entry_type == "sources":
        st.markdown("📄 **Significant Source Documents:**")
        for src in entry:
            source = f"📘 **File**: `{src['source']}`"
            clause = src.get("clause", "")
            if clause and clause.lower() != "unknown":
                source += f" | 🔢 **Clause**: `{clause}`"
            st.markdown(f"- {source}")

# Follow-up input
if st.session_state.chat_mode:
    st.markdown("---")
    st.session_state.followup_input = st.text_input("💬 Ask a follow-up question:", st.session_state.followup_input)
    if st.button("➡️ Send Follow-up"):
        if st.session_state.followup_input:
            with st.spinner("Generating refined answer..."):
                answer, sources, _ = get_answer(query=None, follow_up_answer=st.session_state.followup_input)
                st.session_state.chat_history.append(("followup", st.session_state.followup_input))
                st.session_state.chat_history.append(("answer", answer))
                if sources:
                    st.session_state.chat_history.append(("sources", sources))
            st.session_state.followup_input = ""
