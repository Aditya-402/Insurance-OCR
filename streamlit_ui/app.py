import streamlit as st

# Use relative imports since all UI files are in the same package
from .ui_extract_map import render_extract_map_page
from .ui_check_rules import render_check_rules_page

def run_app():
    """Sets up the page configuration, CSS, and sidebar, and routes to the selected page."""
    st.set_page_config(
        page_title="Insurance Claims Reviewer Assistant - Home",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown("<h1>Insurance Claims Reviewer Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p class='small-subtitle'>GenAI Powered</p>", unsafe_allow_html=True)
    #Req:255
    st.markdown("""
    <style>
        /* Targeting all text input fields */
        .stTextInput input {
            font-size: 0.9rem; /* Smaller font size */
            height: 2.5rem;    /* Reduced height */
            padding: 0.5rem;   /* Adjust padding if necessary */
        }
        /* Targeting all text area fields */
        .stTextArea textarea {
            font-size: 0.9rem; /* Smaller font size for text area */
            min-height: 50px;  /* Minimum height for text area */
        }
        /* General button styling */
        .stButton>button {
            font-size: 0.9rem;
            padding: 0.5rem 1rem;
        }
        .stDownloadButton>button {
            font-size: 0.9rem;
            padding: 0.5rem 1rem;
        }
        h1 {
            font-size: 1.8rem; /* Slightly smaller main title */
        }
    </style>
    """, unsafe_allow_html=True)

    # Custom Sidebar Navigation
    page_options = ["Intro", "Extract Map", "Check Rules"]

    with st.sidebar:
        st.markdown("## Navigation")
        selected_page = st.radio(
            "Go to",
            page_options,
            key="custom_nav_radio",
        )

    # Page routing
    if selected_page == "Intro":
        st.markdown("### Welcome!")
        st.markdown("This application assists with reviewing insurance claims. Use the navigation panel to:")
        st.markdown("- **Extract Map**: Upload claim documents (PDFs) to extract data and map it to structured fields.")
        st.markdown("- **Check Rules**: Evaluate business rules against the claims database or specific claim IDs.")
    elif selected_page == "Extract Map":
        render_extract_map_page()
    elif selected_page == "Check Rules":
        render_check_rules_page()
