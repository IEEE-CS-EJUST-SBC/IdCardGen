import streamlit as st
import pandas as pd
import qrcode
import base64
import io
import zipfile
from datetime import datetime
from jinja2 import Environment, DictLoader
import weasyprint

# ──────────────────────────── HTML Template ────────────────────────────
# Embedding the template makes the web app foolproof (no missing files)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        @page { size: 1200px 400px; margin: 0; }
        body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; background: white; color: #333; width: 1200px; height: 400px; }
        .card-container { width: 1200px; height: 400px; position: relative; box-sizing: border-box; border: 1px solid #e0e0e0; overflow: hidden; }
        .card-front { position: absolute; left: 0; top: 0; width: 600px; height: 400px; box-sizing: border-box; padding-top: 60px; }
        .front-header { position: absolute; top: 0; left: 0; width: 600px; height: 60px; }
        .header-blue { position: absolute; left: 0; width: 450px; height: 60px; background-color: #00629B; color: white; font-size: 22px; font-weight: bold; letter-spacing: 2px; line-height: 60px; padding-left: 40px; box-sizing: border-box; }
        .header-green { position: absolute; left: 450px; width: 150px; height: 60px; background-color: #1B5E20; color: white; font-size: 20px; font-weight: bold; line-height: 60px; text-align: center; }
        .front-body { padding: 40px; }
        .volunteer-name { font-size: 38px; color: #00629B; text-transform: uppercase; margin: 10px 0 40px 0; font-weight: bold; }
        .data-group { display: inline-block; vertical-align: top; width: 150px; }
        .data-group label { display: block; font-size: 13px; color: #888; text-transform: uppercase; margin-bottom: 5px; font-weight: 600; }
        .data-group .val { font-size: 20px; color: #222; font-weight: bold; }
        .front-footer { position: absolute; bottom: 40px; left: 40px; width: 520px; }
        .signature-block { position: absolute; left: 0; bottom: 0; }
        .signature { font-family: 'Brush Script MT', cursive, sans-serif; font-size: 32px; color: #00629B; margin-bottom: -5px; }
        .signature-title { font-size: 13px; color: #666; border-top: 1px solid #ccc; padding-top: 5px; width: 200px; }
        .logo-placeholder { position: absolute; right: 0; bottom: 0; width: 140px; height: 45px; border: 2px dashed #bbb; text-align: center; line-height: 45px; color: #999; font-size: 12px; font-weight: bold; background-color: #f9f9f9; }
        .crease { position: absolute; left: 599px; top: 0; width: 2px; border-left: 2px dashed #ddd; height: 400px; z-index: 10; }
        .card-back { position: absolute; left: 600px; top: 0; width: 600px; height: 400px; background-color: #fcfcfc; text-align: center; box-sizing: border-box; padding-top: 40px; }
        .society-title { color: #00629B; font-size: 20px; font-weight: bold; letter-spacing: 1px; margin-bottom: 30px; }
        .qr-wrapper { width: 150px; height: 150px; background: white; padding: 10px; border: 1px solid #eaeaea; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin: 0 auto 25px auto; }
        .qr-wrapper img { width: 100%; height: 100%; display: block; }
        .back-heading { font-size: 24px; color: #00629B; font-weight: bold; margin-bottom: 15px; }
        .terms-text { font-size: 12px; color: #777; width: 75%; margin: 0 auto; line-height: 1.5; }
        .back-footer { position: absolute; bottom: 0; left: 0; width: 600px; height: 60px; background-color: #1B5E20; color: white; font-size: 13px; box-sizing: border-box; }
        .back-footer-text { position: absolute; left: 40px; top: 20px; }
        .footer-placeholder { position: absolute; right: 40px; top: 15px; width: 100px; height: 30px; border: 1px dashed rgba(255,255,255,0.5); text-align: center; line-height: 30px; font-size: 10px; color: rgba(255,255,255,0.8); }
    </style>
</head>
<body>
    <div class="card-container">
        <div class="card-front">
            <div class="front-header">
                <div class="header-blue">VOLUNTEER</div><div class="header-green">{{ valid_year }}</div>
            </div>
            <div class="front-body">
                <div class="volunteer-name">{{ name }}</div>
                <div>
                    <div class="data-group"><label>Committee</label><div class="val">{{ committee }}</div></div>
                    <div class="data-group"><label>Role</label><div class="val">{{ role }}</div></div>
                    <div class="data-group"><label>Volunteer ID</label><div class="val">{{ generated_id }}</div></div>
                </div>
                <div class="front-footer">
                    <div class="signature-block"><div class="signature">{{ name }}</div><div class="signature-title">Branch Coordinator</div></div>
                    <div class="logo-placeholder">LOGO ASSET HERE</div>
                </div>
            </div>
        </div>
        <div class="crease"></div>
        <div class="card-back">
            <div class="society-title">IEEE COMPUTER SOCIETY</div>
            <div class="qr-wrapper"><img src="data:image/png;base64,{{ qr_base64 }}" alt="QR Code"></div>
            <div class="back-heading">VOLUNTEER ID CARD</div>
            <div class="terms-text">This non-transferable card identifies the named volunteer only. This card is valid for official local Branch activities through 31 December {{ valid_year }}.</div>
            <div class="back-footer">
                <div class="back-footer-text">local.volunteers@ieee.org</div>
                <div class="footer-placeholder">LOGO HERE</div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# ──────────────────────────── Logic ────────────────────────────
COMMITTEE_MAP = {
    "HR": 1, "PR": 2, "IT & Logistics": 3,
    "Marketing": 4, "Media": 5, "Logistics": 6, "AI": 7
}

def generate_custom_id(join_date: pd.Timestamp, committee: str, member_id: int) -> str:
    yy = str(join_date.year)[-2:]                            
    c = str(COMMITTEE_MAP.get(committee, 0))                
    iii = str(int(member_id)).zfill(3)                      
    return f"{yy}{c}{iii}"

def generate_qr_base64(full_name: str, custom_id: str, role: str) -> str:
    qr_data = f"Name: {full_name}\nID: {custom_id}\nRole: {role}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")

# ──────────────────────────── UI ────────────────────────────
st.set_page_config(page_title="IEEE ID Generator", page_icon="🪪")

st.title("🪪 Volunteer ID Card Generator")
st.markdown("Upload the latest `volunteers.xlsx` file. The system will automatically find accepted members, generate their PDF cards, and provide a ZIP file containing the cards and the updated tracking sheets.")

uploaded_file = st.file_uploader("Upload volunteers.xlsx", type=["xlsx"])
uploaded_archive = st.file_uploader("Upload processed_volunteers.xlsx (Optional, if it exists)", type=["xlsx"])

if uploaded_file is not None:
    if st.button("Generate Cards", type="primary"):
        with st.spinner("Processing data and rendering PDFs..."):
            
            # Read Data
            df = pd.read_excel(uploaded_file, engine="openpyxl")
            df.columns = df.columns.str.strip()
            
            if 'Status' not in df.columns:
                st.error("❌ 'Status' column not found in the Excel sheet.")
                st.stop()

            # Filter
            accepted_mask = df["Status"].astype(str).str.strip().str.lower() == "accepted"
            accepted_df = df[accepted_mask].copy()
            remaining_df = df[~accepted_mask].copy()

            if accepted_df.empty:
                st.info("ℹ️ No new 'Accepted' volunteers found in this sheet.")
                st.stop()

            # Setup Jinja Environment
            env = Environment(loader=DictLoader({'template': HTML_TEMPLATE}))
            template = env.get_template('template')

            # Create an in-memory ZIP file
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                
                # Process Cards
                progress_bar = st.progress(0)
                for idx, row in accepted_df.iterrows():
                    first_name = str(row["First Name"]).strip()
                    last_name = str(row["Last Name"]).strip()
                    full_name = f"{first_name} {last_name}"
                    role = str(row["Role"]).strip()
                    committee = str(row["Committee"]).strip()
                    
                    try:
                        join_date = pd.to_datetime(row["Join Date"])
                    except Exception:
                        join_date = pd.to_datetime(datetime.now())
                        
                    member_id = int(row["Member ID"])
                    custom_id = generate_custom_id(join_date, committee, member_id)

                    qr_b64 = generate_qr_base64(full_name, custom_id, role)
                    
                    # Render HTML & Create PDF
                    rendered_html = template.render(
                        name=full_name, role=role, committee=committee, 
                        generated_id=custom_id, valid_year=datetime.now().year, qr_base64=qr_b64
                    )
                    
                    pdf_buffer = io.BytesIO()
                    weasyprint.HTML(string=rendered_html).write_pdf(pdf_buffer)
                    
                    # Write PDF to ZIP
                    zip_file.writestr(f"Cards/{custom_id}.pdf", pdf_buffer.getvalue())
                    
                    # Update Progress
                    progress_bar.progress((list(accepted_df.index).index(idx) + 1) / len(accepted_df))

                # Handle Archives
                if uploaded_archive is not None:
                    existing_archive = pd.read_excel(uploaded_archive, engine="openpyxl")
                    updated_archive = pd.concat([existing_archive, accepted_df], ignore_index=True)
                else:
                    updated_archive = accepted_df

                # Save updated DataFrames to Excel buffers
                archive_buffer = io.BytesIO()
                updated_archive.to_excel(archive_buffer, index=False, engine="openpyxl")
                zip_file.writestr("processed_volunteers.xlsx", archive_buffer.getvalue())

                remaining_buffer = io.BytesIO()
                remaining_df.to_excel(remaining_buffer, index=False, engine="openpyxl")
                zip_file.writestr("volunteers.xlsx", remaining_buffer.getvalue())

            st.success(f"✅ Successfully generated {len(accepted_df)} ID cards!")
            
            # Download Button
            zip_buffer.seek(0)
            st.download_button(
                label="📥 Download Output Package (.zip)",
                data=zip_buffer,
                file_name=f"Generated_Cards_{datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip",
                type="primary"
            )