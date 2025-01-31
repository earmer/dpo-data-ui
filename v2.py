import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager
from services.openai_service import OpenAIService
from utils.config import init_session_state, set_page_config

def main():
    # Initialize configuration
    set_page_config()
    init_session_state()

    # Initialize database
    db = DatabaseManager()

    # Sidebar
    with st.sidebar:
        st.title("DPO Data Generator")
        
        # API Key Management
        saved_api_key = db.get_api_key()
        if saved_api_key:
            st.success("API Key is already set!")
            if st.button("Update API Key"):
                api_key = st.text_input("New OpenAI API Key", type="password")
                if api_key:
                    db.save_api_key(api_key)
                    st.session_state.openai_api_key = api_key
                    st.success("API Key updated!")
        else:
            api_key = st.text_input("OpenAI API Key", type="password")
            if api_key:
                db.save_api_key(api_key)
                st.session_state.openai_api_key = api_key
                st.success("API Key saved!")

        # Dataset Management
        handle_dataset_management(db)

    # Main Content
    if st.session_state.current_dataset:
        tabs = st.tabs(["Data Generation", "Quick Responses", "Export"])
        
        with tabs[0]:
            handle_data_generation(db)
        
        with tabs[1]:
            handle_quick_responses(db)
        
        with tabs[2]:
            handle_export(db)
    else:
        st.info("Please select or create a dataset from the sidebar!")

    # Cleanup
    db.close()

def handle_dataset_management(db):
    st.header("Dataset Management")
    
    dataset_action = st.radio(
        "Action",
        ["Select Dataset", "Create New Dataset", "View Entries"]
    )
    
    if dataset_action == "Select Dataset":
        datasets = db.get_datasets()
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
        new_dataset_name = st.text_input("Dataset Name")
        if st.button("Create Dataset"):
            if new_dataset_name:
                if db.create_dataset(new_dataset_name):
                    st.success("Dataset created successfully!")
                else:
                    st.error("Dataset name already exists!")
            else:
                st.error("Please enter a dataset name!")
    
    else:  # View Entries
        if st.session_state.current_dataset:
            entries = db.get_entries(st.session_state.current_dataset)
            if not entries.empty:
                st.dataframe(entries)
                
                # Add export selected entries option
                if st.button("Export Viewed Entries"):
                    export_format = st.selectbox("Export Format", ["CSV", "JSON"])
                    if export_format == "CSV":
                        st.download_button(
                            "Download CSV",
                            entries.to_csv(index=False),
                            f"{st.session_state.current_dataset}_selected.csv",
                            "text/csv"
                        )
                    else:
                        st.download_button(
                            "Download JSON",
                            entries.to_json(orient='records'),
                            f"{st.session_state.current_dataset}_selected.json",
                            "application/json"
                        )
            else:
                st.info("No entries in this dataset yet!")
        else:
            st.warning("Please select a dataset first!")

def handle_data_generation(db):
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
        
        response_a = ""
        if generation_method_a == "Human Input":
            response_a = st.text_area("Enter Response A", height=200)
        elif generation_method_a == "Quick Response":
            quick_responses = db.get_quick_responses()
            if not quick_responses.empty:
                response_a = st.selectbox(
                    "Select Quick Response",
                    quick_responses['text'].tolist(),
                    key="quick_a"
                )
            else:
                st.warning("No quick responses available")
        else:  # AI Generate
            api_key = db.get_api_key()
            if api_key:
                if st.button("Generate Response A"):
                    try:
                        openai_service = OpenAIService(api_key)
                        response_a = openai_service.generate_better_response(question)
                        st.text_area("Generated Response A", response_a, height=200)
                    except Exception as e:
                        st.error(f"Error generating response: {str(e)}")
            else:
                st.warning("Please set your OpenAI API key in the sidebar")
    
    with col2:
        st.subheader("Response B (Worse Response)")
        generation_method_b = st.radio(
            "Generation Method B",
            ["AI Generate", "Human Input", "Quick Response"],
            key="gen_method_b"
        )
        
        response_b = ""
        if generation_method_b == "Human Input":
            response_b = st.text_area("Enter Response B", height=200)
        elif generation_method_b == "Quick Response":
            quick_responses = db.get_quick_responses()
            if not quick_responses.empty:
                response_b = st.selectbox(
                    "Select Quick Response",
                    quick_responses['text'].tolist(),
                    key="quick_b"
                )
            else:
                st.warning("No quick responses available")
        else:  # AI Generate
            api_key = db.get_api_key()
            if api_key:
                if st.button("Generate Response B"):
                    try:
                        openai_service = OpenAIService(api_key)
                        response_b = openai_service.generate_worse_response(question)
                        st.text_area("Generated Response B", response_b, height=200)
                    except Exception as e:
                        st.error(f"Error generating response: {str(e)}")
            else:
                st.warning("Please set your OpenAI API key in the sidebar")
    
    # Preview and Save
    if question and response_a and response_b:
        st.subheader("Preview")
        preview_col1, preview_col2 = st.columns(2)
        with preview_col1:
            st.text_area("Response A Preview", response_a, height=150)
        with preview_col2:
            st.text_area("Response B Preview", response_b, height=150)
            
        if st.button("Save DPO Entry"):
            try:
                db.save_entry(st.session_state.current_dataset, question, response_a, response_b)
                st.success("DPO entry saved successfully!")
                # Clear the form
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error saving entry: {str(e)}")
    else:
        st.warning("Please fill in all fields (question and both responses) to save")

def handle_quick_responses(db):
    st.header("Quick Responses Management")
    
    # Add new quick response
    st.subheader("Add New Quick Response")
    qr_text = st.text_area("Response Text")
    
    if st.button("Add Quick Response"):
        if qr_text:
            if db.add_quick_response(qr_text):
                st.success("Quick response added!")
                st.experimental_rerun()
            else:
                st.error("Error adding quick response!")
        else:
            st.error("Please enter response text!")
    
    # View and manage existing quick responses
    st.subheader("Existing Quick Responses")
    quick_responses = db.get_quick_responses()
    if not quick_responses.empty:
        # Display with delete buttons
        for _, response in quick_responses.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text_area("", response['text'], height=100, key=f"qr_{response['id']}")
            with col2:
                if st.button("Delete", key=f"del_{response['id']}"):
                    if db.delete_quick_response(response['id']):
                        st.success("Quick response deleted!")
                        st.experimental_rerun()
                    else:
                        st.error("Error deleting quick response!")

def handle_export(db):
    st.header("Export Dataset")
    
    export_format = st.selectbox(
        "Export Format",
        ["JSON", "CSV"]
    )
    
    # Add export options
    export_options = st.multiselect(
        "Export Options",
        ["Include timestamps", "Include metadata", "Format for training"]
    )
    
    if st.button("Export"):
        entries = db.get_entries(st.session_state.current_dataset)
        
        if not entries.empty:
            # Process based on options
            if "Format for training" in export_options:
                entries = entries[['question', 'response_a', 'response_b']]
                entries.columns = ['question', 'chosen', 'rejected']
            
            if "Include timestamps" not in export_options:
                entries = entries.drop(columns=['created_at'], errors='ignore')
                
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

if __name__ == "__main__":
    main()
