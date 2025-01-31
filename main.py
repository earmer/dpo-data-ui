import streamlit as st
import pandas as pd
import sqlite3
import json
from datetime import datetime
import os
from openai import OpenAI

# Initialize OpenAI client
def init_openai():
    api_key = st.secrets["openai"]["api_key"] if "openai" in st.secrets else st.session_state.get('openai_api_key')
    if api_key:
        return OpenAI(api_key=api_key, base_url="https://api.openai-hk.com/v1")
    return None

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect('dpo_data.db')
    c = conn.cursor()
    
    # Create necessary tables if they don't exist
    c.executescript('''
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            created_at TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY,
            dataset_id INTEGER,
            question TEXT,
            response_a TEXT,
            response_b TEXT,
            preferred TEXT,
            status TEXT,
            created_at TIMESTAMP,
            FOREIGN KEY (dataset_id) REFERENCES datasets(id)
        );
        
        CREATE TABLE IF NOT EXISTS quick_responses (
            id INTEGER PRIMARY KEY,
            text TEXT,
            created_at TIMESTAMP
        );
    ''')
    conn.commit()
    return conn

# Page configurations
st.set_page_config(page_title="DPO Data Generation", layout="wide")

# Initialize session state
if 'current_dataset' not in st.session_state:
    st.session_state.current_dataset = None
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = None

# Initialize database
conn = init_db()

# Sidebar for dataset selection and management
with st.sidebar:
    st.title("DPO Data Generator")
    
    # OpenAI API Key Input
    api_key = st.text_input("OpenAI API Key", type="password")
    if api_key:
        st.session_state.openai_api_key = api_key
        st.success("API Key set!")
    
    # Dataset Management
    st.header("Dataset Management")
    
    dataset_action = st.radio(
        "Action",
        ["Select Dataset", "Create New Dataset", "View Entries"]
    )
    
    if dataset_action == "Select Dataset":
        # Load existing datasets
        datasets = pd.read_sql("SELECT * FROM datasets", conn)
        if not datasets.empty:
            selected_dataset = st.selectbox(
                "Choose Dataset",
                datasets['name'].tolist()
            )
            if st.button("Load Dataset"):
                st.session_state.current_dataset = selected_dataset
                st.success(f"Loaded dataset: {selected_dataset}")
        else:
            st.info("No datasets available. Create one first!")
            
    elif dataset_action == "Create New Dataset":
        # Create new dataset
        new_dataset_name = st.text_input("Dataset Name")
        if st.button("Create Dataset"):
            if new_dataset_name:
                try:
                    c = conn.cursor()
                    c.execute(
                        "INSERT INTO datasets (name, created_at) VALUES (?, ?)",
                        (new_dataset_name, datetime.now())
                    )
                    conn.commit()
                    st.success("Dataset created successfully!")
                except sqlite3.IntegrityError:
                    st.error("Dataset name already exists!")
            else:
                st.error("Please enter a dataset name!")
    
    else:  # View Entries
        if st.session_state.current_dataset:
            entries = pd.read_sql(
                """
                SELECT question, response_a, response_b, preferred, created_at
                FROM entries e
                JOIN datasets d ON e.dataset_id = d.id
                WHERE d.name = ?
                ORDER BY e.created_at DESC
                """,
                conn,
                params=(st.session_state.current_dataset,)
            )
            if not entries.empty:
                st.dataframe(entries)
            else:
                st.info("No entries in this dataset yet!")
        else:
            st.warning("Please select a dataset first!")

# Main content
if st.session_state.current_dataset:
    tabs = st.tabs(["Data Generation", "Quick Responses", "Export"])
    
    # Data Generation Tab
    with tabs[0]:
        st.header("Data Generation")
        
        # Question Input
        st.subheader("Question/Prompt")
        question = st.text_area("Enter the question or prompt", height=100)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Response A (Better Response)")
            generation_method_a = st.radio(
                "Generation Method A",
                ["AI Generate", "Human Input", "Quick Response"],
                key="gen_method_a"
            )
            
            if generation_method_a == "Human Input":
                response_a = st.text_area("Enter Response A", height=200)
            elif generation_method_a == "Quick Response":
                # Load quick responses
                quick_responses = pd.read_sql("SELECT * FROM quick_responses", conn)
                if not quick_responses.empty:
                    response_a = st.selectbox(
                        "Select Quick Response",
                        quick_responses['text'].tolist(),
                        key="quick_a"
                    )
                else:
                    st.warning("No quick responses available")
                    response_a = ""
            else:  # AI Generate
                if st.session_state.openai_api_key:
                    if st.button("Generate Response A"):
                        client = init_openai()
                        if client:
                            try:
                                response = client.chat.completions.create(
                                    model="gpt-4-turbo-preview",
                                    messages=[
                                        {"role": "system", "content": "You are a helpful AI assistant. Generate a high-quality response to the user's question."},
                                        {"role": "user", "content": question}
                                    ]
                                )
                                response_a = response.choices[0].message.content
                                st.text_area("Generated Response A", response_a, height=200)
                            except Exception as e:
                                st.error(f"Error generating response: {str(e)}")
                else:
                    st.warning("Please set your OpenAI API key in the sidebar")
                    response_a = ""
        
        with col2:
            st.subheader("Response B (Worse Response)")
            generation_method_b = st.radio(
                "Generation Method B",
                ["AI Generate", "Human Input", "Quick Response"],
                key="gen_method_b"
            )
            
            if generation_method_b == "Human Input":
                response_b = st.text_area("Enter Response B", height=200)
            elif generation_method_b == "Quick Response":
                if not quick_responses.empty:
                    response_b = st.selectbox(
                        "Select Quick Response",
                        quick_responses['text'].tolist(),
                        key="quick_b"
                    )
                else:
                    st.warning("No quick responses available")
                    response_b = ""
            else:  # AI Generate
                if st.session_state.openai_api_key:
                    if st.button("Generate Response B"):
                        client = init_openai()
                        if client:
                            try:
                                response = client.chat.completions.create(
                                    model="gpt-3.5-turbo",  # Using 3.5 for worse responses
                                    messages=[
                                        {"role": "system", "content": "Generate a less detailed or lower quality response to the user's question."},
                                        {"role": "user", "content": question}
                                    ]
                                )
                                response_b = response.choices[0].message.content
                                st.text_area("Generated Response B", response_b, height=200)
                            except Exception as e:
                                st.error(f"Error generating response: {str(e)}")
                else:
                    st.warning("Please set your OpenAI API key in the sidebar")
                    response_b = ""
        
        # Save entry
        if st.button("Save DPO Entry"):
            if question and response_a and response_b:
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO entries 
                    (dataset_id, question, response_a, response_b, preferred, status, created_at)
                    VALUES (
                        (SELECT id FROM datasets WHERE name = ?),
                        ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        st.session_state.current_dataset,
                        question,
                        response_a,
                        response_b,
                        "A",  # Always prefer A as it's the better response
                        "active",
                        datetime.now()
                    )
                )
                conn.commit()
                st.success("DPO entry saved successfully!")
            else:
                st.error("Please fill in all fields (question and both responses)!")
    
    # Quick Responses Tab
    with tabs[1]:
        st.header("Quick Responses Management")
        
        # Add new quick response
        st.subheader("Add New Quick Response")
        qr_text = st.text_area("Response Text")
        
        if st.button("Add Quick Response"):
            if qr_text:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO quick_responses (text, created_at) VALUES (?, ?)",
                    (qr_text, datetime.now())
                )
                conn.commit()
                st.success("Quick response added!")
            else:
                st.error("Please enter response text!")
        
        # View existing quick responses
        st.subheader("Existing Quick Responses")
        quick_responses = pd.read_sql("SELECT * FROM quick_responses", conn)
        if not quick_responses.empty:
            st.dataframe(quick_responses[['text', 'created_at']])
            
            # Delete quick response
            if st.button("Delete Selected Quick Response"):
                selected_response = st.selectbox(
                    "Select response to delete",
                    quick_responses['text'].tolist()
                )
                if selected_response:
                    c = conn.cursor()
                    c.execute("DELETE FROM quick_responses WHERE text = ?", (selected_response,))
                    conn.commit()
                    st.success("Quick response deleted!")
    
    # Export Tab
    with tabs[2]:
        st.header("Export Dataset")
        
        export_format = st.selectbox(
            "Export Format",
            ["JSON", "CSV"]
        )
        
        if st.button("Export"):
            entries = pd.read_sql(
                """
                SELECT question, response_a as chosen, response_b as rejected
                FROM entries e
                JOIN datasets d ON e.dataset_id = d.id
                WHERE d.name = ?
                """,
                conn,
                params=(st.session_state.current_dataset,)
            )
            
            if not entries.empty:
                if export_format == "JSON":
                    st.download_button(
                        "Download JSON",
                        entries.to_json(orient='records'),
                        f"{st.session_state.current_dataset}.json",
                        "application/json"
                    )
                else:  # CSV
                    st.download_button(
                        "Download CSV",
                        entries.to_csv(index=False),
                        f"{st.session_state.current_dataset}.csv",
                        "text/csv"
                    )
            else:
                st.warning("No entries to export!")

else:
    st.info("Please select or create a dataset from the sidebar!")

# Cleanup
conn.close()