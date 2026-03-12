import streamlit as st
import requests
import json
import base64
from pdf2image import convert_from_path
import io
from PIL import Image
import pandas as pd
from datetime import datetime
import time

# IBM Watsonx Configuration
API_KEY = "kEYC-iaRZRuEb0AIck5x1iCDB32Zdb8MkC_3j6AzpIz3"
PROJECT_ID = "4152f31e-6a49-40aa-9b62-0ecf629aae42"
MODEL_ID = "meta-llama/llama-3-2-90b-vision-instruct"
IAM_URL = "https://iam.cloud.ibm.com/identity/token"
WATSONX_API_URL = "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29"

class WatsonxOCRExtractor:
    def __init__(self):
        self.access_token = None
        self.token_expiry = None
    
    def get_access_token(self):
        """Get IBM Cloud IAM access token"""
        if self.access_token and self.token_expiry and time.time() < self.token_expiry:
            return self.access_token
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": API_KEY
        }
        
        response = requests.post(IAM_URL, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        self.token_expiry = time.time() + token_data["expires_in"] - 300
        
        return self.access_token
    
    def image_to_base64(self, image):
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')
    
    def extract_fields_from_image(self, image):
        """Extract fields from a single image using Watsonx Vision model"""
        access_token = self.get_access_token()
        img_base64 = self.image_to_base64(image)
        
        prompt = """You are an expert medical form data extraction system. Extract information from this medical assessment form image with EXACT formatting.

⚠️ CRITICAL RULES - READ CAREFULLY:
1. Extract ONLY the sections that are VISIBLE on THIS specific page
2. DO NOT include sections that are not visible on this page
3. DO NOT show empty template structures for missing sections
4. DO NOT repeat section headers or field names multiple times
5. Each section header should appear ONLY ONCE at the top
6. Copy text EXACTLY as written - preserve capitalization, spacing, and formatting
7. For tables, extract in markdown table format with proper alignment
8. For checkmarks (✓), note which items are checked
9. For blank fields, use "___" or leave empty in tables
10. Add blank lines between major subsections for readability
11. Use proper indentation and spacing

OUTPUT FORMAT - Use section headers ONLY for sections visible on this page:

When you see a section on the page, format it like this:

## SECTION NAME

[Extract the data here]

---

AVAILABLE SECTION FORMATS (use ONLY if visible on this page):

## FAMILY CONSTELLATION

| RELATION | NAME          | AGE | EDUCATION    | OCCUPATION   | INCOME PM |
|----------|---------------|-----|--------------|--------------|-----------|
| FATHER   | [exact name]  | [#] | [exact text] | [exact text] | [amount]  |
| MOTHER   | [exact name]  | [#] | [exact text] | [exact text] | [amount]  |
| BROTHER  | [exact name]  | [#] | [exact text] | [exact text] | [amount]  |
| SISTER   | [exact name]  | [#] | [exact text] | [exact text] | [amount]  |

---

## CHIEF ASSESSMENT / OT/PT ASSESSMENT

**CHIEF COMPLAINTS:**  
[Extract exact text from form - use multiple lines if needed]

**PROBLEM AREA:**  
[Extract exact text from form]

---

## MEDICAL HISTORY

**A. PRE-NATAL CONDITION:**  
[Extract exact text - can be multiple lines]

**B. PERI-NATAL CONDITION:**  
[Extract exact text - can be multiple lines]

**C. POST-NATAL CONDITION:**  
[Extract exact text - can be multiple lines]

**D. TREATMENT HISTORY:**  
[Extract exact text - can be multiple lines]

**E. FAMILY HISTORY:**  
[Present/Not Present or exact details]

---

## DEVELOPMENTAL MILESTONES

| MILESTONE | AGE/TIMING   | DELAYED BY   |
|-----------|--------------|--------------|
| Sitting   | [exact text] | [exact text] |
| Crawling  | [exact text] | [exact text] |
| Standing  | [exact text] | [exact text] |
| Walking   | [exact text] | [exact text] |
| Speaking  | [exact text] | [exact text] |

---

## GEN EXAMINATION

**GENERAL APPEARANCE:**
- Head/Shape & Size: [exact finding]
- Height/Stature: [measurement with units]

**COGNITION/PERCEPTUAL:**
- Orientation: [exact finding]
- Attention: [exact finding]
- Memory: [exact finding]

**MUSCLE TONE/HYPERTONIA/HYPOTONIA:**
- Muscle power:
  - Upper Limb: [finding]
  - Lower Limb: [finding]

---

## REFLEX, MOTOR/TONE

**Reflex Maturation:**
- Spinal Level Reflexes (0-2 months): [checked items]
- Brain-Stem Reflexes: [checked items]
- Righting Reactions: [checked items]
- Equilibrium Reaction: [checked items]
- Proof of toxicity (6 months onwards): [checked items]
- Rapture of toxicity (8 month onwards): [checked items]
- Quadruple (1-10 months onwards): [checked items]
- Writing (6-8 month onwards): [checked items]

**Swaying (2-4 month onwards):**  
[checked items]

---

## NEUROMOTOR DISTURBANCE

**I. Neuromotor Type:**  
□ Hypotonic  □ Hypertonic  □ Ataxia  □ V-Rigidity  □ VI-Tremor

**II. Distribution:**  
□ I-Monoplegia  □ II-Hemiplegia  □ III-Paraplegia  □ IV-Diplegia

**III. Posture:**
- Sitting: [description]
- Standing: [description]
- Lying: [description]

**IV. Gait/Diversity:** [description]

**V. Orthotics/Prosthetic aids:** [description]

---

## DEFORMITIES & CONTRACTURES

**I. Hand Position:**
- Radial/Palmar/Ulnar: [checked items]
- Grasp: [description]

**II. Prominent:**
- Lateral/Palmar/Dorsal: [description]

**III. Opposition:** [description]

**IV. Spinal Malalignment:** [description]

**V. Alignment of Hand:** [description]

**VI. Release:** [description]

**VII. Handedness:** [description]

**VIII. Eye-Hand Coordination:** [description]

---

## CO-ORDINATION

| TEST | STANDING | WALKING |
|------|----------|---------|
| a) Finger to nose | [finding] | [finding] |
| b) Nose-equilibrium | [finding] | [finding] |
| c) Toe-to-floor | [finding] | [finding] |
| d) Finger to finger | [finding] | [finding] |
| e) Heel to knee | [finding] | [finding] |

---

## PARENTAL EXPECTATIONS

[exact text from form]

---

## THERAPY/OPINION/RECOMMENDATION

[exact text from form]

**Special Arrangement needed:** [exact text]

---

## SPEECH AND LANGUAGE DEVELOPMENT ASSESSMENT

**SPEECH DEVELOPMENTAL MILESTONES:**

| S.No | Milestones | Normal age | Delayed By |
|------|------------|------------|------------|
| 1    | Vocalization | 0-3 months |           |
| 2    | Babbling | 4-6 months |           |
| 3    | First word | 9-10 months |          |
| 4    | Two words | 10-18 months |          |
| 5    | Phrases | 18-24 months |           |
| 6    | Sentences | 2.5-3 years |           |

**FAMILY HISTORY:** [Present/Not Present]

**SPEECH MECHANISM:**

| PART | APPEARANCE | FUNCTION |
|------|------------|----------|
| 1. Lips |          |          |
| 2. Teeth |         |          |
| 3. Tongue |        |          |
| 4. Hard palate |   |          |
| 5. Soft palate |   |          |
| 6. Uvula |         |          |

**PHONOLOGICAL/ARTICULATION ASSESSMENT:**
- Consonant: [exact findings]
- Vowel: [exact findings]
- Blends: [exact findings]
- Diphthong: [exact findings]

**VOICE PARAMETER:**
- Loudness: [finding]
- Pitch: [finding]
- Quality: [finding]

---

## LANGUAGE DEVELOPMENT

**Non-verbal:**

| Comprehension | Expression |
|---------------|------------|
| Gesture: [✓ or blank] | Gesture: [✓ or blank] |
| Sign: [✓ or blank] | Sign: [✓ or blank] |
| Facial expression: [✓ or blank] | Verbal: [✓ or blank] |

**SUPRA-SEGMENTALS:**
- Intonation: [finding]
- Stress: [finding]
- Juncture: [finding]
- Rhythm: [finding]

**RATE OF SPEECH:** [exact description]

**FLUENCY/DISFLUENCY:** [exact description]

---

## PROVISIONAL DIAGNOSIS

[exact diagnosis]

---

## RECOMMENDATIONS

1. Speech therapy: [exact recommendation]
2. Parent education: [exact recommendation]

---

## SPECIAL EDUCATION ASSESSMENT FORM

**SELF-HELP SKILLS:**

*Meal times:*
- Eating: [independence level]
- Drinking: [independence level]

*Toileting:* [description]

*Doffing and Donning:* [details]

*Wearing shoes:* [details]

*Grooming:* [details]

**SOCIALIZATION:**
- Sits properly but avoids eye contact: [Yes/No]
- Does not move in different places: [Yes/No]
- Often talkative: [Yes/No]

**COGNITIVE:**  
Level of disability (Mild/Moderate/Severe/Profound): [level]

---

## ACADEMICS

1. **Reading:** [exact description]
2. **Writing:** [exact description]
3. **Arithmetic:** [exact description]

---

## SENSORY STATUS

- **Vision:** [exact finding]
- **Hearing:** [exact finding with dB if mentioned]

---

## BEHAVIOUR

1. **Attention span:** [description]
2. **Is child self-destructive:** [Yes/No with details]
3. **Any problem behavior reported by parents:** [exact text]
4. **Problem behavior observed by Educator:** [exact text]

---

## RELATIONSHIP (as reported by Parents)

1. Child - Father: [description]
2. Child - Mother: [description]
3. Child - Siblings: [description]
4. Child - Other members: [description]
5. Child - Older: [description]
6. Among other members: [description]

---

## ADDITIONAL INFORMATION

**Class and family background:** [exact text]

**Previous intervention:** [exact text]

**Coordination/Counseling with:** [exact text]

---

## SIGNATURES

- **Signature:** [name if visible]
- **Received Manager:** [name if visible]
- **Date:** [date]
- **H.O.D:** [name if visible]
- **Date:** [date]
- **Coordinator/Teacher Name:** [name]
- **Designated Officer:** [name if visible]
- **Superintendent/Principal:** [name if visible]
- **Date of Assessment:** [date]

---

EXTRACTION INSTRUCTIONS FOR THIS SPECIFIC PAGE:
1. Look at the image and identify which sections are visible
2. For each visible section:
   - Write the section header (## SECTION NAME)
   - Add a blank line
   - Extract the data with proper formatting using bold (**text**) for labels
   - Add horizontal separator (---) after each section
3. Skip any sections not visible on this page
4. Copy all visible text EXACTLY as written
5. For tables: ensure proper markdown table format
6. Use bold text for field labels
7. Use bullet points (-) for lists

Now extract ONLY the visible sections from this page using markdown formatting with headers (##), bold text (**), and tables:"""
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "model_id": MODEL_ID,
            "project_id": PROJECT_ID,
            "max_tokens": 4000,
            "temperature": 0.05
        }
        
        response = requests.post(WATSONX_API_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code}")
            st.error(f"Response: {response.text}")
            raise Exception(f"API request failed: {response.text}")
        
        result = response.json()
        generated_text = result["choices"][0]["message"]["content"].strip()
        
        # Clean up markdown code blocks if present
        if "```" in generated_text:
            generated_text = generated_text.replace("```markdown", "").replace("```", "").strip()
        
        return generated_text
    
    def merge_extracted_data(self, all_page_data, range_label=""):
        """Merge formatted text from multiple pages"""
        merged_text = f"# 📋 EXTRACTED DATA - {range_label}\n\n"
        merged_text += "---\n\n"
        
        for page_idx, (page_num, page_text) in enumerate(all_page_data):
            merged_text += f"# 📄 PAGE {page_num}\n\n"
            merged_text += page_text + "\n\n"
            merged_text += "---\n\n"
        
        return merged_text
    
    def process_pdf(self, pdf_file, start_page, end_page, range_label="Range"):
        """Process a PDF file and extract fields from specified page range"""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.getvalue())
            temp_path = tmp_file.name
        
        try:
            images = convert_from_path(
                temp_path, 
                first_page=start_page, 
                last_page=end_page, 
                dpi=300
            )
        except Exception as e:
            st.error(f"Error converting PDF to images: {e}")
            return "Error: failed to convert PDF", [], []
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
        
        all_page_data = []
        
        for i, image in enumerate(images):
            actual_page_num = start_page + i
            st.write(f"Processing page {actual_page_num} ({i+1}/{len(images)})...")
            try:
                extracted_text = self.extract_fields_from_image(image)
                all_page_data.append((actual_page_num, extracted_text))
            except Exception as e:
                st.warning(f"Error processing page {actual_page_num}: {str(e)}")
                all_page_data.append((actual_page_num, f"[Error processing page {actual_page_num}]"))
        
        merged_text = self.merge_extracted_data(all_page_data, range_label)
        
        return merged_text, images, all_page_data


def main():
    st.set_page_config(page_title="Medical Form OCR Extractor", page_icon="🏥", layout="wide")
    
    st.title("🏥 Medical Assessment Form OCR Extractor")
    st.markdown("Upload medical assessment PDFs and extract structured data from multiple page ranges")
    
    # Initialize session state
    if 'all_extracted_data' not in st.session_state:
        st.session_state.all_extracted_data = []
    if 'current_pdf' not in st.session_state:
        st.session_state.current_pdf = None
    
    with st.sidebar:
        st.header("⚙️ Page Range Configuration")
        st.markdown("Define multiple page ranges to extract from the same PDF")
        
        st.markdown("---")
        
        # Page Range 1
        st.subheader("📄 Page Range 1")
        col1, col2 = st.columns(2)
        with col1:
            start_page_1 = st.number_input("Start Page", min_value=1, value=1, step=1, key="start_1")
        with col2:
            end_page_1 = st.number_input("End Page", min_value=1, value=2, step=1, key="end_1")
        
        range_1_enabled = st.checkbox("Enable Range 1", value=True, key="enable_1")
        
        if range_1_enabled:
            if start_page_1 > end_page_1:
                st.error("⚠️ Start page must be ≤ end page!")
            else:
                st.success(f"✅ Pages {start_page_1}-{end_page_1} ({end_page_1 - start_page_1 + 1} pages)")
        
        st.markdown("---")
        
        # Page Range 2
        st.subheader("📄 Page Range 2")
        col3, col4 = st.columns(2)
        with col3:
            start_page_2 = st.number_input("Start Page", min_value=1, value=8, step=1, key="start_2")
        with col4:
            end_page_2 = st.number_input("End Page", min_value=1, value=15, step=1, key="end_2")
        
        range_2_enabled = st.checkbox("Enable Range 2", value=False, key="enable_2")
        
        if range_2_enabled:
            if start_page_2 > end_page_2:
                st.error("⚠️ Start page must be ≤ end page!")
            else:
                st.success(f"✅ Pages {start_page_2}-{end_page_2} ({end_page_2 - start_page_2 + 1} pages)")
        
        st.markdown("---")
        
        # Summary
        total_pages = 0
        if range_1_enabled and start_page_1 <= end_page_1:
            total_pages += (end_page_1 - start_page_1 + 1)
        if range_2_enabled and start_page_2 <= end_page_2:
            total_pages += (end_page_2 - start_page_2 + 1)
        
        st.info(f"📊 Total pages to process: **{total_pages}**")
    
    # Main content area
    uploaded_file = st.file_uploader(
        "Upload Medical Assessment PDF",
        type=['pdf'],
        accept_multiple_files=False,
        help="Upload a medical assessment PDF file"
    )
    
    if uploaded_file:
        st.info(f"📁 File uploaded: **{uploaded_file.name}**")
        st.session_state.current_pdf = uploaded_file
        
        # Validate ranges
        valid_ranges = []
        if range_1_enabled and start_page_1 <= end_page_1:
            valid_ranges.append((start_page_1, end_page_1, "Range 1"))
        if range_2_enabled and start_page_2 <= end_page_2:
            valid_ranges.append((start_page_2, end_page_2, "Range 2"))
        
        if not valid_ranges:
            st.warning("⚠️ Please enable at least one valid page range in the sidebar")
            return
        
        if st.button("🚀 Start OCR Extraction", type="primary", use_container_width=True):
            extractor = WatsonxOCRExtractor()
            
            # Clear previous results
            st.session_state.all_extracted_data = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                for idx, (start_pg, end_pg, range_label) in enumerate(valid_ranges):
                    status_text.text(f"Processing {range_label}: Pages {start_pg}-{end_pg}...")
                    
                    with st.expander(f"📄 {range_label}: Pages {start_pg}-{end_pg}", expanded=True):
                        merged_text, page_images, page_data_list = extractor.process_pdf(
                            uploaded_file, start_pg, end_pg, range_label
                        )
                        
                        # Store extracted data
                        st.session_state.all_extracted_data.append({
                            'range_label': range_label,
                            'pages': f"{start_pg}-{end_pg}",
                            'text': merged_text,
                            'images': page_images,
                            'data_list': page_data_list
                        })
                        
                        # Display each page with its extracted data
                        for page_num, page_text in page_data_list:
                            st.markdown(f"### 📄 Page {page_num}")
                            
                            col_img, col_data = st.columns([1, 1])
                            
                            page_idx = page_num - start_pg
                            if page_idx < len(page_images):
                                with col_img:
                                    st.image(page_images[page_idx], 
                                           caption=f"Page {page_num}", 
                                           use_container_width=True)
                            
                            with col_data:
                                st.markdown("**Extracted Data:**")
                                st.markdown(page_text)
                            
                            st.markdown("---")
                        
                        # Show complete range data
                        st.markdown(f"### 📊 Complete {range_label} Data")
                        st.markdown(merged_text)
                        
                        # Download option for this range
                        st.download_button(
                            label=f"📥 Download {range_label} Data (TXT)",
                            data=merged_text,
                            file_name=f"{uploaded_file.name}_{range_label.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain",
                            key=f"download_{idx}"
                        )
                    
                    progress_bar.progress((idx + 1) / len(valid_ranges))
                
                status_text.text("✅ All ranges processed successfully!")
                
                # Combined download option
                if len(st.session_state.all_extracted_data) > 1:
                    st.markdown("---")
                    st.subheader("📦 Combined Data from All Ranges")
                    
                    combined_text = f"# 📋 COMPLETE EXTRACTION - {uploaded_file.name}\n\n"
                    combined_text += f"Extraction Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    combined_text += "=" * 80 + "\n\n"
                    
                    for data in st.session_state.all_extracted_data:
                        combined_text += f"\n\n{'=' * 80}\n"
                        combined_text += f"# {data['range_label']} (Pages {data['pages']})\n"
                        combined_text += f"{'=' * 80}\n\n"
                        combined_text += data['text']
                    
                    st.download_button(
                        label="📥 Download Complete Combined Data (TXT)",
                        data=combined_text,
                        file_name=f"{uploaded_file.name}_COMPLETE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                st.success("🎉 OCR extraction completed successfully!")
            
            except Exception as e:
                st.error(f"❌ Error during extraction: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    else:
        st.info("👆 Please upload a medical assessment PDF file to begin extraction")
        
        with st.expander("ℹ️ How it works"):
            st.markdown("""
            ### Process:
            1. **Upload PDF**: Select a medical assessment PDF file
            2. **Configure Ranges**: Set up to 2 page ranges in the sidebar
               - Range 1: e.g., pages 1-2 (basic info)
               - Range 2: e.g., pages 8-15 (detailed assessment)
            3. **AI Processing**: Each page is analyzed using IBM Watsonx Vision AI
            4. **Formatted Output**: Data extracted in structured, readable format
            5. **Export**: Download results separately or as combined document
            
            ### Features:
            - ✅ Process any number of pages (no 50-page limit!)
            - ✅ Multiple page ranges from the same PDF
            - ✅ Extracts ONLY visible sections from each page
            - ✅ Preserves original form structure and formatting
            - ✅ Extracts tables in markdown format
            - ✅ Side-by-side view of images and extracted data
            - ✅ Individual downloads per range
            - ✅ Combined download for all ranges
            - ✅ Clean, readable output format
            
            ### Example Use Cases:
            - Extract pages 1-2 (patient info) and 20-27 (assessment results)
            - Process pages 1-5 (demographics) and 94-100 (appendix)
            - Multiple non-consecutive sections from large documents
            """)


if __name__ == "__main__":
    main()