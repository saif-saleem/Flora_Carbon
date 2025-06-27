import streamlit as st
from app.rag_chat import get_answer
import base64

with open("app/assets/flora_carbon_logo.png", "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()

st.set_page_config(page_title="Flora Carbon GPT", layout="wide")

st.markdown(f"""
    <style>
        .header-container {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 1rem;
        }}
        .header-logo img {{
            height: 70px;
            border-radius: 10px;
        }}
        .header-text h1 {{
            margin: 0rem 0rem 0rem 0rem;
            font-size: 2.5rem;
            color: #81c784;
        }}
        .header-text p {{
            font-size: 1.15rem;
            color: #c8e6c9;
            margin-top: -10px;
        }}
        .stTextInput > div > input {{
            background-color: #1e1e1e;
            color: white;
        }}
        .stButton>button {{
            background-color: #388e3c;
            color: white;
            font-weight: bold;
            border-radius: 6px;
            padding: 0.5rem 1rem;
        }}
        .stButton>button:hover {{
            background-color: #2e7d32;
        }}
        .message-container {{
            background-color: #1b4332;
            padding: 1.2rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            color: white;
            font-size: 1.05rem;
            line-height: 1.6;
        }}
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="header-container">
    <div class="header-logo">
        <img src="data:image/png;base64,{img_base64}" alt="Flora Carbon Logo">
    </div>
    <div class="header-text">
        <h1>Flora Carbon GPT</h1>
        <p>Your expert assistant for carbon credit standards & certifications</p>
    </div>
</div>
""", unsafe_allow_html=True)

# State init
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chat_mode" not in st.session_state:
    st.session_state.chat_mode = False
if "clarification_needed" not in st.session_state:
    st.session_state.clarification_needed = False
if "clarification_text" not in st.session_state:
    st.session_state.clarification_text = ""
if "original_query" not in st.session_state:
    st.session_state.original_query = ""
if "main_query" not in st.session_state:
    st.session_state.main_query = ""
if "follow_up" not in st.session_state:
    st.session_state.follow_up = ""

if st.button("🆕 New Chat"):
    st.session_state.chat_history = []
    st.session_state.chat_mode = False
    st.session_state.clarification_needed = False
    st.session_state.clarification_text = ""
    st.session_state.original_query = ""
    st.session_state.main_query = ""
    st.session_state.follow_up = ""
    st.rerun()

st.session_state.main_query = st.text_input("🔍 Ask your question:", value=st.session_state.main_query)

if st.button("🔎 Search"):
    if st.session_state.main_query:
        with st.spinner("Generating answer..."):
            answer, sources, clarification = get_answer(st.session_state.main_query)
            st.session_state.original_query = st.session_state.main_query

            if clarification:
                st.session_state.clarification_needed = True
                st.session_state.clarification_text = clarification
            else:
                st.session_state.chat_history.append(("question", st.session_state.main_query))
                st.session_state.chat_history.append(("answer", answer))
                if sources != "web" and sources:
                    st.session_state.chat_history.append(("sources", sources))
                st.session_state.chat_mode = True

if st.session_state.clarification_needed:
    st.warning(f"🔍 {st.session_state.clarification_text}")
    cols = st.columns(3)
    for i, standard in enumerate(["VCS", "GS", "CDM"]):
        if cols[i].button(standard):
            st.session_state.clarification_needed = False
            st.session_state.clarification_text = ""
            st.session_state.selected_standard = standard
            st.rerun()

if "selected_standard" in st.session_state:
    standard = st.session_state.selected_standard
    with st.spinner(f"Answering for {standard}..."):
        query = st.session_state.original_query + f" for {standard}"
        answer, sources, _ = get_answer(query=query)
        st.session_state.chat_history.append(("question", query))
        st.session_state.chat_history.append(("answer", answer))
        if sources != "web" and sources:
            st.session_state.chat_history.append(("sources", sources))
        st.session_state.chat_mode = True
    del st.session_state.selected_standard

for entry_type, entry in st.session_state.chat_history:
    if entry_type == "question":
        st.markdown(f"🧑‍💬 **You:** {entry}", unsafe_allow_html=True)
    elif entry_type == "answer":
        st.markdown(f"""
        <div class="message-container">
            🌍 <b>Carbon GPT:</b><br><br>
            {entry}
        </div>
        """, unsafe_allow_html=True)
    elif entry_type == "sources":
        if entry:
            st.markdown("📄 **Significant Source Documents:**")
            for src in entry:
                source = f"📘 **File**: `{src['source']}`"
                clause = src.get("clause", "")
                if clause and clause.lower() != "unknown":
                    source += f" | 🔢 **Clause**: `{clause}`"
                st.markdown(f"- {source}")

if st.session_state.chat_mode:
    st.markdown("---")
    st.session_state.follow_up = st.text_input("💬 Ask a follow-up question:", value=st.session_state.follow_up)
    if st.button("➡️ Send Follow-up"):
        if st.session_state.follow_up:
            with st.spinner("Generating refined answer..."):
                answer, sources, _ = get_answer(query=None, follow_up_answer=st.session_state.follow_up)
                st.session_state.chat_history.append(("question", st.session_state.follow_up))
                st.session_state.chat_history.append(("answer", answer))
                if sources != "web" and sources:
                    st.session_state.chat_history.append(("sources", sources))
