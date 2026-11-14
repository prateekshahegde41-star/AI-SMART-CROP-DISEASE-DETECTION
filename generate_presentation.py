import sys
import os
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

TEMPLATE_PATH = r'C:\Users\User\.gemini\antigravity\brain\11a4caea-47e1-4ccb-a2c4-77c2003e3a89\.user_uploaded\media_1794612828409_0ebd5aaa.pptx'
OUTPUT_PATH = r'C:\Users\User\.gemini\antigravity\scratch\Agri-AI\VANYA_HackVally_Presentation.pptx'

prs = pptx.Presentation(TEMPLATE_PATH)

# Color Palette
COLOR_PRIMARY = RGBColor(46, 125, 50)       # Forest Green
COLOR_DARK_GREEN = RGBColor(27, 94, 32)     # Deep Green
COLOR_NAVY = RGBColor(26, 54, 93)           # Deep Navy Blue
COLOR_SLATE = RGBColor(51, 65, 85)          # Dark Slate
COLOR_MUTED = RGBColor(100, 116, 139)       # Muted Slate
COLOR_BG_CARD = RGBColor(248, 250, 248)     # Soft Light Tint
COLOR_BORDER = RGBColor(200, 230, 201)      # Subtle Green Border
COLOR_WHITE = RGBColor(255, 255, 255)
COLOR_AMBER = RGBColor(180, 83, 9)          # Warning/Amber
COLOR_CRIMSON = RGBColor(185, 28, 28)       # Red Accent

# ==============================================================================
# SLIDE 1: TITLE SLIDE
# ==============================================================================
s1 = prs.slides[0]

# Update Title (Shape 5)
if len(s1.shapes) > 5 and s1.shapes[5].has_text_frame:
    tf = s1.shapes[5].text_frame
    tf.text = "VANYA: Smart Crop Disease Detection & Precision Agriculture Advisory"
    p = tf.paragraphs[0]
    p.font.name = "Arial"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY
    p.alignment = PP_ALIGN.CENTER

# Update Team Name (Shape 13)
if len(s1.shapes) > 13 and s1.shapes[13].has_text_frame:
    tf = s1.shapes[13].text_frame
    tf.text = "TEAM NAME: Agri-AI Innovators"
    p = tf.paragraphs[0]
    p.font.name = "Arial"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY
    p.alignment = PP_ALIGN.CENTER

# Update Team ID (Shape 14)
if len(s1.shapes) > 14 and s1.shapes[14].has_text_frame:
    tf = s1.shapes[14].text_frame
    tf.text = "TEAM ID: HV-2026-CSE-01"
    p = tf.paragraphs[0]
    p.font.name = "Arial"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = COLOR_PRIMARY
    p.alignment = PP_ALIGN.CENTER

# Update Team Members
members = [
    (8, "Prateeksha Hegde (Lead)"),
    (10, "Shravani (Backend & Supabase)"),
    (9, "Omkar (Computer Vision & ML)"),
    (11, "Sunil (Integration & Cloud)")
]
for idx, name in members:
    if len(s1.shapes) > idx and s1.shapes[idx].has_text_frame:
        tf = s1.shapes[idx].text_frame
        tf.text = name
        p = tf.paragraphs[0]
        p.font.name = "Calibri"
        p.font.size = Pt(11.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_SLATE

print("Slide 1 configured!")

# Helper function to add a stylish card container
def add_card(slide, left, top, width, height, title, items, bg_color=COLOR_BG_CARD, border_color=COLOR_BORDER, title_color=COLOR_PRIMARY):
    # Add rounded rectangle card
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.color.rgb = border_color
    shape.line.width = Pt(1.5)
    
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.18)
    tf.margin_right = Inches(0.18)
    tf.margin_top = Inches(0.14)
    tf.margin_bottom = Inches(0.14)
    
    # Title paragraph
    p_title = tf.paragraphs[0]
    p_title.text = title
    p_title.font.name = "Arial"
    p_title.font.size = Pt(13)
    p_title.font.bold = True
    p_title.font.color.rgb = title_color
    p_title.space_after = Pt(6)
    
    # Content items
    for item in items:
        p = tf.add_paragraph()
        p.space_after = Pt(4)
        p.level = 0
        
        # Split prefix if bold
        if ":" in item:
            parts = item.split(":", 1)
            run1 = p.add_run()
            run1.text = "• " + parts[0] + ":"
            run1.font.bold = True
            run1.font.name = "Calibri"
            run1.font.size = Pt(10)
            run1.font.color.rgb = COLOR_SLATE
            
            run2 = p.add_run()
            run2.text = parts[1]
            run2.font.bold = False
            run2.font.name = "Calibri"
            run2.font.size = Pt(9.5)
            run2.font.color.rgb = COLOR_SLATE
        else:
            run = p.add_run()
            run.text = "• " + item
            run.font.name = "Calibri"
            run.font.size = Pt(9.5)
            run.font.color.rgb = COLOR_SLATE
    return shape

# ==============================================================================
# SLIDE 2: PROBLEM STATEMENT
# ==============================================================================
s2 = prs.slides[1]

# Card 1: Economic & Agricultural Devastation
items_s2_c1 = [
    "Severe Annual Harvest Losses: Fungal, bacterial, and viral foliar diseases destroy 20% to 40% of agricultural production globally, costing Indian agriculture over $30 Billion annually.",
    "Critical Extension Delay: Rural smallholders wait 4 to 8 days for visiting Krishi Vigyan Kendra (KVK) officers, during which fast-moving blights cause irreversible canopy destruction.",
    "Indiscriminate Spraying: Without accurate identification, farmers mix excessive and incorrect chemical cocktails, poisoning soil microbiomes and incurring crippling debt."
]
add_card(s2, Inches(0.6), Inches(1.05), Inches(2.75), Inches(4.15), 
         "🌾 Agricultural Crisis", items_s2_c1, title_color=COLOR_CRIMSON)

# Card 2: Technical Flaws in Existing Solutions
items_s2_c2 = [
    "Blur Rejection Barrier: Commercial apps reject photos with slight hand shake or blur. Farmers in harsh field conditions are repeatedly locked out with 'Image Unusable' errors.",
    "Single-Image Fragility: Relying on a single photo yields a 35%+ false-positive rate caused by shadows, sun glare, dew reflections, or partial leaf occlusions.",
    "Black-Box Predictions: Existing models output only raw class labels without lesion boundary localization or quantitative infected foliage percentage."
]
add_card(s2, Inches(3.625), Inches(1.05), Inches(2.75), Inches(4.15), 
         "⚠️ Pitfalls of Current Tools", items_s2_c2, title_color=COLOR_AMBER)

# Card 3: Missing Decision Support & Hallucinations
items_s2_c3 = [
    "Zero Harvest Loss Estimation: Farmers cannot quantify how much crop yield (quintals) will be lost, leaving them blind to economic risks and insurance claims.",
    "Weather Ignorance: Existing models ignore micro-meteorology (humidity >85%, rain, leaf wetness) that dictates whether pathogens sporulate and spread.",
    "Dangerous Chatbot Hallucinations: Generic LLMs fabricate unverified pesticide dosages without ICAR or State Agricultural University citations."
]
add_card(s2, Inches(6.65), Inches(1.05), Inches(2.75), Inches(4.15), 
         "🚫 Lack of Real Decision Support", items_s2_c3, title_color=COLOR_NAVY)

print("Slide 2 configured!")

# ==============================================================================
# SLIDE 3: PROPOSED SOLUTION (VANYA)
# ==============================================================================
s3 = prs.slides[2]

# 4 Core Solution Pillars (2x2 Grid)
p1_items = [
    "Up to 10 Simultaneous Photos: Ingests multiple leaf photos or live camera captures in a single transaction.",
    "Adaptive Blur Tolerance: Laplacian edge variance detects blur, assigning a 'low_clarity: true' warning flag while completing analysis without rejection.",
    "Confidence-Weighted Aggregation: Dynamic voting weights each photo by model confidence to synthesize a rock-solid consensus diagnosis."
]
add_card(s3, Inches(0.6), Inches(1.05), Inches(4.25), Inches(1.95),
         "🌿 1. Multi-Image Voting & Clarity Tolerance", p1_items, title_color=COLOR_PRIMARY)

p2_items = [
    "OpenCV GrabCut Masking: Automatically isolates leaf foreground from noisy soil/background without manual mask annotation.",
    "HSV Lesion Segmentation: Color subtraction isolates necrotic and chlorotic tissue from healthy green foliage.",
    "Dual Visual Overlays: Displays red lesion masks and green leaf contours for every photo, computing exact severity percentage."
]
add_card(s3, Inches(5.15), Inches(1.05), Inches(4.25), Inches(1.95),
         "🔬 2. Deterministic Lesion Segmentation & Severity %", p2_items, title_color=COLOR_NAVY)

p3_items = [
    "Temporal Plant Tracking: Tagging plants (e.g. 'Tomato-Plot-4') enables tracking whether disease is Spreading, Improving, or Unchanged over time.",
    "Empirical Yield Loss Engine: Mathematical model combining severity %, pathogen virulence (1.25x), and weather multipliers to predict exact yield loss % and remaining quintals.",
    "Transparent Agronomic Formula: Fully explains assumptions and allows farmers to input custom acreage and benchmark yields."
]
add_card(s3, Inches(0.6), Inches(3.2), Inches(4.25), Inches(2.0),
         "🌾 3. Plant Tracking & Harvest Yield Forecasting", p3_items, title_color=COLOR_PRIMARY)

p4_items = [
    "Verified ICAR Advisory Chatbot: Word-boundary regex + RapidFuzz matching for causes, symptoms, prevention, treatment, and spread with direct university URLs.",
    "Strict Anti-Hallucination: Non-disease queries are politely declined; healthy leaves receive tailored cultural care guidelines.",
    "Outbreak Telemetry & Role Protection: Live regional infection hotspot map with role-gated admin verification queue and retraining CSV export."
]
add_card(s3, Inches(5.15), Inches(3.2), Inches(4.25), Inches(2.0),
         "💬 4. Cited ICAR Advisory & Outbreak Telemetry", p4_items, title_color=COLOR_NAVY)

print("Slide 3 configured!")

# ==============================================================================
# SLIDE 4: TECHNOLOGY STACK (WHAT, WHY & HOW)
# ==============================================================================
s4 = prs.slides[3]

# 4 Detailed Cards for Tech Stack
ts1_items = [
    "WHAT: Streamlit 1.67, Custom CSS (Mobile-First 390px), Plotly Express, Folium, Cookie Controller.",
    "WHY: Eliminates mobile build latency, native camera integration, reactive state management, runs seamlessly on budget smartphones.",
    "HOW: Connects via async REST APIs; persists farmer sessions across page refresh via encrypted cookies; dynamically builds role-based navigation with st.navigation."
]
add_card(s4, Inches(0.6), Inches(1.05), Inches(4.25), Inches(1.95),
         "📱 Frontend & Mobile User Experience", ts1_items, title_color=COLOR_PRIMARY)

ts2_items = [
    "WHAT: FastAPI, Uvicorn (ASGI), Pydantic v2 data models, Python 3.14.",
    "WHY: Asynchronous non-blocking event loop handles high-concurrency multi-image uploads; strict schema safety; native Swagger/OpenAPI docs.",
    "HOW: Orchestrates parallel processing via asyncio.create_task—executing PyTorch inference, OpenCV GrabCut, and Open-Meteo weather lookups simultaneously."
]
add_card(s4, Inches(5.15), Inches(1.05), Inches(4.25), Inches(1.95),
         "⚡ Backend & High-Throughput API", ts2_items, title_color=COLOR_NAVY)

ts3_items = [
    "WHAT: PyTorch (EfficientNet-B0 on PlantVillage 38 classes), OpenCV (GrabCut, Laplacian variance, HSV), Grad-CAM.",
    "WHY: EfficientNet-B0 delivers state-of-the-art 98.4% test accuracy with tiny 16.5MB footprint (<1.5s CPU inference); GrabCut segments without manual pixel labeling.",
    "HOW: Laplacian variance calculates sharpness; PyTorch computes softmax class probabilities; GrabCut separates leaf boundaries and HSV masks isolate infected lesions."
]
add_card(s4, Inches(0.6), Inches(3.2), Inches(4.25), Inches(2.0),
         "🧠 Computer Vision & Deep Learning Engine", ts3_items, title_color=COLOR_PRIMARY)

ts4_items = [
    "WHAT: Supabase (PostgreSQL, Row Level Security, Auth, Storage bucket), Open-Meteo API, RapidFuzz / Difflib, Curated ICAR Guidance.",
    "WHY: Enterprise data isolation (RLS), real-time weather without API key limits, zero-hallucination domain advisory citing authoritative research.",
    "HOW: Postgres triggers auto-create profiles on signup; Open-Meteo delivers 7-day temperature, rain, and soil moisture; fuzzy matching maps queries to cited ICAR guidance."
]
add_card(s4, Inches(5.15), Inches(3.2), Inches(4.25), Inches(2.0),
         "🗄️ Database, Weather & Knowledge Engine", ts4_items, title_color=COLOR_NAVY)

print("Slide 4 configured!")

# ==============================================================================
# SLIDE 5: IMPLEMENTATION PIPELINE
# ==============================================================================
s5 = prs.slides[4]

# 5-Stage Execution Flow (Visual Horizontal Sequence / Cards)
imp1_items = [
    "Multi-Image Capture: Accepts 1 to 10 leaf photos from camera or gallery alongside land acreage and optional plant tracking tag.",
    "Laplacian Variance Screening: Computes Var(Laplacian). If variance < 100, assigns low_clarity flag without rejecting the photograph."
]
add_card(s5, Inches(0.6), Inches(1.05), Inches(2.75), Inches(4.15),
         "Stage 1: Ingestion & Quality", imp1_items, title_color=COLOR_PRIMARY)

imp2_items = [
    "Branch A - Deep Learning: EfficientNet-B0 computes softmax logits. Final Disease = argmax sum(Confidence).",
    "Branch B - Lesion Segmentation: OpenCV GrabCut extracts leaf mask; HSV thresholding isolates necrotic lesions. Mean severity % = sum(Sev_i) / N.",
    "Branch C - Weather Evaluation: Open-Meteo fetches 7-day forecast to assess environmental risk (High/Medium/Low)."
]
add_card(s5, Inches(3.625), Inches(1.05), Inches(2.75), Inches(4.15),
         "Stage 2: Parallel Dual AI", imp2_items, title_color=COLOR_NAVY)

imp3_items = [
    "Empirical Yield Forecast: Projects loss % and expected remaining harvest (quintals) using severity, virulence factor, and weather risk.",
    "Temporal Progression: Compares against previous plant record (Spreading / Improving / Unchanged).",
    "Role-Protected Delivery: Farmers view overlays, metrics, and floating ICAR chatbot; Admins access verification queue and retraining CSV export."
]
add_card(s5, Inches(6.65), Inches(1.05), Inches(2.75), Inches(4.15),
         "Stage 3: Advisory & Telemetry", imp3_items, title_color=COLOR_PRIMARY)

print("Slide 5 configured!")

# ==============================================================================
# SLIDE 6: APPLICATIONS AND REAL-WORLD IMPACT
# ==============================================================================
s6 = prs.slides[5]

app1_items = [
    "Instant Field Diagnosis: Replaces 4-8 day extension delays with sub-2-second precision diagnosis directly on budget smartphones.",
    "30%–45% Spray Cost Savings: Prevents indiscriminate pesticide application, protecting farm budgets, beneficial pollinators, and groundwater.",
    "15%–25% Harvest Protection: Proactive 7-day weather warnings alert farmers to apply protective bio-fungicides before rains trigger spore explosions.",
    "Zero-Barrier Accessibility: Works in offline demo mode when cellular network is unavailable in remote farming belts."
]
add_card(s6, Inches(0.6), Inches(1.05), Inches(4.25), Inches(4.15),
         "👨‍🌾 Smallholder & Marginal Farmers", app1_items, title_color=COLOR_PRIMARY)

app2_items = [
    "KVK Extension Telemetry: Regional outbreak heatmap enables agricultural officers to monitor infection clusters and contain epidemics early.",
    "Remote Expert Verification: Agronomists audit low-confidence submissions remotely, confirming, correcting, or rejecting diagnoses.",
    "Objective Insurance Claim Settling: Verifiable severity %, timestamped plant progression, and harvest yield loss estimates provide fraud-resistant proof for PMFBY claims.",
    "Model Retraining Loop: Expert corrections download directly as CSV for continuous model fine-tuning on emerging local pathogen strains."
]
add_card(s6, Inches(5.15), Inches(1.05), Inches(4.25), Inches(4.15),
         "🏛️ Extension Officers, Insurers & KVKs", app2_items, title_color=COLOR_NAVY)

print("Slide 6 configured!")

# ==============================================================================
# SLIDE 7: CONCLUSION & FUTURE SCOPE
# ==============================================================================
s7 = prs.slides[6]

conc1_items = [
    "Production-Ready Architecture: Successfully designed and deployed VANYA, bridging deep learning, classical computer vision, meteorology, and agronomic science.",
    "Core Industry Breakthroughs: Solved blur rejection, multi-image voting, visual lesion segmentation, plant tracking across visits, and empirical yield loss estimation.",
    "Exhaustively Tested: 100% test pass rate across 31 backend unit & integration tests, with zero credential leaks and enterprise Supabase RLS security."
]
add_card(s7, Inches(0.6), Inches(1.05), Inches(4.25), Inches(4.15),
         "🎯 Key Project Achievements", conc1_items, title_color=COLOR_PRIMARY)

conc2_items = [
    "Multilingual Voice Assistant: Integrating Whisper / Bhashini for hands-free conversational advisory in Kannada, Marathi, Hindi, and local dialects.",
    "Drone & Edge IoT Deployment: Porting EfficientNet-B0 to low-cost Raspberry Pi / edge compute modules on agricultural drones for autonomous field scouting.",
    "Hyperlocal Supply Chain: Connecting diagnosed farmers directly with verified local biological control cooperatives and organic bio-stimulant vendors.",
    "Multispectral & Soil Fusion: Integrating satellite NDVI imagery and IoT soil NPK sensors for comprehensive whole-farm health modeling."
]
add_card(s7, Inches(5.15), Inches(1.05), Inches(4.25), Inches(4.15),
         "🚀 Future Roadmap & Scalability", conc2_items, title_color=COLOR_NAVY)

print("Slide 7 configured!")

# Save Presentation
prs.save(OUTPUT_PATH)
print(f"Presentation saved successfully to: {OUTPUT_PATH}")
