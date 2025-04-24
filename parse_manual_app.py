import os
import re
import io
import tempfile
import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import pandas as pd
import base64


st.set_page_config(page_title="Patient Form Processor", layout="wide")

# Function to display PDF (without using st.pdf)
def display_pdf(file_path):
    # Read PDF file
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
    
    # Create a download link for the current page
    st.download_button(
        label="📄 Download this page for viewing",
        data=pdf_bytes,
        file_name=f"page_{st.session_state.current_form + 1}.pdf",
        mime="application/pdf"
    )
    
    st.warning("PDF preview is not available directly in the app. Please download the page to view it.")

# Step 1: Split multi-page PDF into individual pages
def split_pdf(input_file, output_dir):
    pdf = PdfReader(input_file)
    temp_files = []
    
    for i in range(len(pdf.pages)):
        output = PdfWriter()
        output.add_page(pdf.pages[i])
        temp_path = os.path.join(output_dir, f"temp_page_{i+1}.pdf")
        with open(temp_path, "wb") as out_file:
            output.write(out_file)
        temp_files.append(temp_path)
    
    return temp_files, len(pdf.pages)

# Function to process forms through streamlit interface
def process_forms(temp_files, output_dir, progress_bar):
    data = []
    form_states = {}
    
    # Initialize session state for form tracking
    if 'current_form' not in st.session_state:
        st.session_state.current_form = 0
    
    if 'forms_completed' not in st.session_state:
        st.session_state.forms_completed = False
    
    if st.session_state.forms_completed:
        return pd.DataFrame(st.session_state.saved_data)
    
    if 'saved_data' not in st.session_state:
        st.session_state.saved_data = []
    
    i = st.session_state.current_form
    
    if i < len(temp_files):
        # Update progress
        progress_bar.progress((i + 1) / len(temp_files))
        st.subheader(f"Form {i+1} of {len(temp_files)}")
        

        
        # Get patient name with Streamlit inputs
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input(f"First Name for Form {i+1}", key=f"first_{i}")
        with col2:
            last_name = st.text_input(f"Last Name for Form {i+1}", key=f"last_{i}")
        
        # Submit button
        if st.button(f"Save and Continue", key=f"continue_{i}"):
            # If no name entered, use placeholder
            if not first_name and not last_name:
                first_name = f"Unknown"
                last_name = f"Patient_{i+1}"
            
            # Create the final filename
            full_name = f"{first_name} {last_name}".strip()
            safe_filename = re.sub(r'[^\w\s-]', '', full_name).replace(' ', '_')
            new_filename = f"{safe_filename}.pdf"
            new_path = os.path.join(output_dir, new_filename)
            
            # Copy the file with the new name
            with open(temp_files[i], 'rb') as src_file:
                pdf_content = src_file.read()
                with open(new_path, 'wb') as dest_file:
                    dest_file.write(pdf_content)
            
            # Add to saved data
            st.session_state.saved_data.append({
                "First Name": first_name,
                "Last Name": last_name,
                "PDF Path": new_path
            })
            
            # Move to next form
            st.session_state.current_form += 1
            st.experimental_rerun()
    
    # All forms processed
    if st.session_state.current_form >= len(temp_files):
        st.session_state.forms_completed = True
        st.success("All forms processed successfully!")
        return pd.DataFrame(st.session_state.saved_data)
    
    return None

def main():
    st.title("Patient Form Processor")
    st.write("Upload a multi-page PDF with patient forms to process")
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", key="file_uploader")
    
    if uploaded_file is not None:
        # Create temp directory
        if 'temp_dir' not in st.session_state:
            st.session_state.temp_dir = tempfile.mkdtemp()
        
        if 'output_dir' not in st.session_state:
            st.session_state.output_dir = tempfile.mkdtemp()
        
        # Save the uploaded file temporarily
        temp_input_path = os.path.join(st.session_state.temp_dir, "input.pdf")
        with open(temp_input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Split PDF
        if 'temp_files' not in st.session_state:
            with st.spinner("Splitting PDF into individual pages..."):
                temp_files, num_pages = split_pdf(temp_input_path, st.session_state.temp_dir)
                st.session_state.temp_files = temp_files
                st.session_state.num_pages = num_pages
                st.success(f"Successfully split PDF into {num_pages} pages")
        
        # Process forms
        st.write("### Process Patient Forms")
        st.write("Enter patient information for each form:")
        
        progress_bar = st.progress(0)
        patient_data = process_forms(st.session_state.temp_files, st.session_state.output_dir, progress_bar)
        
        if patient_data is not None:
            # Save data to CSV
            csv_data = patient_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Patient Data CSV",
                data=csv_data,
                file_name="patient_data.csv",
                mime="text/csv"
            )
            
            # Create a ZIP file of all processed PDFs
            import zipfile
            zip_path = os.path.join(st.session_state.temp_dir, "patient_forms.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for _, row in patient_data.iterrows():
                    pdf_path = row["PDF Path"]
                    pdf_filename = os.path.basename(pdf_path)
                    zipf.write(pdf_path, arcname=pdf_filename)
            
            # Allow downloading the ZIP file
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="Download All Processed PDFs",
                    data=f,
                    file_name="patient_forms.zip",
                    mime="application/zip"
                )
            
            # Reset button
            if st.button("Process Another PDF"):
                # Clear session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.experimental_rerun()

if __name__ == "__main__":
    main()
