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

# Function to process forms through streamlit interface
def process_forms(temp_files, output_dir, progress_bar):
    data = []
    
    for i, temp_file in enumerate(temp_files):
        # Update progress
        progress_bar.progress((i + 1) / len(temp_files))
        st.subheader(f"Form {i+1} of {len(temp_files)}")
        
        # Display PDF preview
        with open(temp_file, "rb") as f:
            pdf_bytes = f.read()
            st.pdf(pdf_bytes, width=700)
        
        # Get patient name with Streamlit inputs
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input(f"First Name for Form {i+1}", key=f"first_{i}")
        with col2:
            last_name = st.text_input(f"Last Name for Form {i+1}", key=f"last_{i}")
        
        # Continue button
        if not st.button(f"Save and Continue to Next Form", key=f"continue_{i}"):
            st.stop()
        
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
        with open(temp_file, 'rb') as src_file:
            pdf_content = src_file.read()
            with open(new_path, 'wb') as dest_file:
                dest_file.write(pdf_content)
        
        # Add to data list
        data.append({
            "First Name": first_name,
            "Last Name": last_name,
            "PDF Path": new_path
        })
    
    return pd.DataFrame(data)

def main():
    st.title("Patient Form Processor")
    st.write("Upload a multi-page PDF with patient forms to process")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        output_dir = tempfile.mkdtemp()
        
        # Save the uploaded file temporarily
        temp_input_path = os.path.join(temp_dir, "input.pdf")
        with open(temp_input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Split PDF
        with st.spinner("Splitting PDF into individual pages..."):
            temp_files, num_pages = split_pdf(temp_input_path, temp_dir)
            st.success(f"Successfully split PDF into {num_pages} pages")
        
        # Process forms
        st.write("### Process Patient Forms")
        st.write("Enter patient information for each form:")
        
        progress_bar = st.progress(0)
        patient_data = process_forms(temp_files, output_dir, progress_bar)
        
        # Save data to CSV
        csv_data = patient_data.to_csv(index=False)
        st.success("Processing complete!")
        
        # Allow downloading the CSV
        st.download_button(
            label="Download Patient Data CSV",
            data=csv_data,
            file_name="patient_data.csv",
            mime="text/csv"
        )
        
        # Create a ZIP file of all processed PDFs
        import zipfile
        zip_path = os.path.join(temp_dir, "patient_forms.zip")
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
        
        # Clean up
        import shutil
        shutil.rmtree(temp_dir)
        shutil.rmtree(output_dir)

if __name__ == "__main__":
    main()