import os
import re
import io
import tempfile
import streamlit as st
from PyPDF2 import PdfReader, PdfWriter
import pandas as pd

st.set_page_config(page_title="Patient Form Processor", layout="wide")

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

def main():
    st.title("Patient Form Processor")
    st.write("Upload a multi-page PDF with patient forms to process")
    
    # Use a temporary directory
    if 'initialized' not in st.session_state:
        st.session_state.temp_dir = tempfile.mkdtemp()
        st.session_state.output_dir = tempfile.mkdtemp()
        st.session_state.initialized = True
        st.session_state.processing_complete = False
        st.session_state.patient_data = []
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None and not st.session_state.processing_complete:
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
                st.session_state.current_page = 0
                st.success(f"Successfully split PDF into {num_pages} pages")
        
        # Process forms
        if 'current_page' in st.session_state and st.session_state.current_page < len(st.session_state.temp_files):
            current_page = st.session_state.current_page
            
            st.write(f"### Processing Form {current_page + 1} of {len(st.session_state.temp_files)}")
            
            # Instead of preview, just give download option
            with open(st.session_state.temp_files[current_page], "rb") as f:
                pdf_bytes = f.read()
            
            st.download_button(
                label=f"📄 Download Form {current_page + 1} to view",
                data=pdf_bytes,
                file_name=f"form_{current_page + 1}.pdf",
                mime="application/pdf"
            )
            
            # Get patient info
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input(f"First Name", key=f"first_{current_page}")
            with col2:
                last_name = st.text_input(f"Last Name", key=f"last_{current_page}")
            
            # Save button
            if st.button("Save and Continue", key=f"save_{current_page}"):
                # If no name entered, use placeholder
                if not first_name and not last_name:
                    first_name = f"Unknown"
                    last_name = f"Patient_{current_page + 1}"
                
                # Create the final filename
                full_name = f"{first_name} {last_name}".strip()
                safe_filename = re.sub(r'[^\w\s-]', '', full_name).replace(' ', '_')
                new_filename = f"{safe_filename}.pdf"
                new_path = os.path.join(st.session_state.output_dir, new_filename)
                
                # Copy the file with the new name
                with open(st.session_state.temp_files[current_page], 'rb') as src_file:
                    pdf_content = src_file.read()
                    with open(new_path, 'wb') as dest_file:
                        dest_file.write(pdf_content)
                
                # Add to patient data
                st.session_state.patient_data.append({
                    "First Name": first_name,
                    "Last Name": last_name,
                    "PDF Path": new_path
                })
                
                # Move to next page or finish
                st.session_state.current_page += 1
                
                if st.session_state.current_page >= len(st.session_state.temp_files):
                    st.session_state.processing_complete = True
                
                st.info("Saved! Please refresh the page to continue.")
                
        elif st.session_state.processing_complete:
            st.success("All forms have been processed!")
            
            # Convert patient data to DataFrame
            if st.session_state.patient_data:
                df = pd.DataFrame(st.session_state.patient_data)
                
                # Save data to CSV
                csv_data = df.to_csv(index=False).encode('utf-8')
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
                    for _, row in df.iterrows():
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
                    # Clear session state for a new run
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]

if __name__ == "__main__":
    main()
