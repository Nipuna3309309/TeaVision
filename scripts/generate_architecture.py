import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(1, 1, figsize=(18, 12))
ax.set_xlim(0, 18)
ax.set_ylim(0, 12)
ax.axis('off')
fig.patch.set_facecolor('white')

# Colors
c_input = '#E3F2FD'
c_preprocess = '#FFF3E0'
c_ml = '#E8F5E9'
c_dl = '#F3E5F5'
c_rag = '#FFF9C4'
c_deploy = '#FFEBEE'
c_output = '#E0F2F1'

b_input = '#1565C0'
b_preprocess = '#E65100'
b_ml = '#2E7D32'
b_dl = '#6A1B9A'
b_rag = '#F9A825'
b_deploy = '#C62828'
b_output = '#00695C'

def draw_box(x, y, w, h, text, fc, ec, fs=8, bold=False, sub=None):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                          facecolor=fc, edgecolor=ec, linewidth=1.8)
    ax.add_patch(box)
    wt = 'bold' if bold else 'normal'
    if sub:
        ax.text(x + w/2, y + h/2 + 0.13, text, ha='center', va='center',
                fontsize=fs, fontweight=wt, color='#212121')
        ax.text(x + w/2, y + h/2 - 0.16, sub, ha='center', va='center',
                fontsize=6.5, fontweight='normal', color='#555555', style='italic')
    else:
        ax.text(x + w/2, y + h/2, text, ha='center', va='center',
                fontsize=fs, fontweight=wt, color='#212121')

def arrow(x1, y1, x2, y2, color='#424242', lw=1.5):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw))

def label(x, y, text, color):
    ax.text(x, y, text, ha='center', va='center', fontsize=9,
            fontweight='bold', color='white',
            bbox=dict(boxstyle='round,pad=0.35', facecolor=color, edgecolor=color, linewidth=1.5))

def dashed_line(x1, y1, x2, y2, color='#9E9E9E'):
    ax.plot([x1, x2], [y1, y2], linestyle='--', color=color, linewidth=1, alpha=0.5)

# ============================================================
# TITLE
# ============================================================
ax.text(9, 11.55, 'Component System Architecture', ha='center', va='center',
        fontsize=15, fontweight='bold', color='#1A237E')
ax.text(9, 11.2, 'Objective 1: Tea Leaf Freshness Grading  |  Project 25-263-133  |  IT22154576',
        ha='center', va='center', fontsize=9, color='#616161')

# ============================================================
# Vertical divider between ML/DL pipeline and RAG system
# ============================================================
dashed_line(13.2, 10.7, 13.2, 1.4, '#BDBDBD')

# ============================================================
# LEFT SIDE: ML/DL PIPELINE (x: 0-13)
# ============================================================

# --- ROW 1: DATA ACQUISITION ---
label(1.5, 10.5, 'DATA ACQUISITION', b_input)

draw_box(0.3, 9.6, 3.5, 0.65, 'TeaVision Mobile App', c_input, b_input, 9, True,
         'Kotlin / Jetpack Compose / CameraX')
draw_box(4.3, 9.6, 3.5, 0.65, 'Quality Gates (5)', c_input, b_input, 8, False,
         'Blur, Brightness, Glare, Tilt, Stability')

arrow(3.8, 9.92, 4.3, 9.92, b_input)

ax.text(8.5, 9.92, '275 images\n66 sessions', ha='center', va='center',
        fontsize=7, color=b_input, fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.25', facecolor='white', edgecolor=b_input, linewidth=1.2))

# --- ROW 2: PREPROCESSING ---
label(1.5, 8.85, 'PREPROCESSING', b_preprocess)

draw_box(0.3, 8.0, 2.8, 0.6, 'Brightness Normalization', c_preprocess, b_preprocess, 8, False,
         '+/-30 unit outdoor correction')
draw_box(3.6, 8.0, 3.0, 0.6, 'Dual Segmentation', c_preprocess, b_preprocess, 8, True,
         'TFLite (94.2%) + HSV fallback (82.7%)')
draw_box(7.1, 8.0, 2.8, 0.6, 'Morphological Cleanup', c_preprocess, b_preprocess, 8, False,
         'Erosion + Dilation (-40% FP)')

# Vertical arrow from Data Acq to Preprocessing (aligned with Dual Seg center)
arrow(5.1, 9.6, 5.1, 8.6, '#424242')
# Horizontal arrows within preprocessing
arrow(3.1, 8.3, 3.6, 8.3, b_preprocess)
arrow(6.6, 8.3, 7.1, 8.3, b_preprocess)

# --- SPLIT into two pipelines (diverging fork from Dual Seg) ---
ax.text(5.5, 7.35, 'TWO PARALLEL PIPELINES', ha='center', va='center',
        fontsize=8, fontweight='bold', color='#424242',
        bbox=dict(boxstyle='round,pad=0.2', facecolor='#F5F5F5', edgecolor='#BDBDBD', linewidth=1))

arrow(4.5, 8.0, 2.5, 7.15, b_ml)   # left fork to Classical ML
arrow(5.7, 8.0, 9.5, 7.15, b_dl)   # right fork to Deep Learning

# ============================================================
# LEFT BRANCH: CLASSICAL ML (x: 0-6)
# ============================================================
label(2.5, 7.15, 'CLASSICAL ML', b_ml)

draw_box(0.3, 6.1, 2.5, 0.65, 'Feature Extraction', c_ml, b_ml, 8, True,
         '25 features (from 56 via ANOVA)')
draw_box(3.3, 6.1, 2.5, 0.65, 'StandardScaler', c_ml, b_ml, 8, False,
         'Z-score normalization')

arrow(2.8, 6.42, 3.3, 6.42, b_ml)

draw_box(0.3, 5.0, 2.5, 0.65, '10-Model Comparison', c_ml, b_ml, 8, False,
         '5-fold stratified CV')
draw_box(3.3, 5.0, 2.5, 0.65, 'AdaBoost (Best)', c_ml, b_ml, 9, True,
         '96.36% test accuracy')

arrow(1.55, 6.1, 1.55, 5.65, b_ml)
arrow(2.8, 5.32, 3.3, 5.32, b_ml)

# ML Output
draw_box(1.2, 3.9, 3.5, 0.7, 'Binary Quality Grade', c_output, b_output, 9, True,
         'high_quality / medium_quality')
arrow(4.55, 5.0, 2.95, 4.6, b_output)

# ============================================================
# RIGHT BRANCH: DEEP LEARNING (x: 7-13)
# ============================================================
label(9.5, 7.15, 'DEEP LEARNING', b_dl)

draw_box(7.3, 6.1, 2.5, 0.65, 'YOLOv8s Model', c_dl, b_dl, 8, True,
         'COCO pretrained, 20 epochs')
draw_box(10.3, 6.1, 2.5, 0.65, 'SAHI Tiling', c_dl, b_dl, 8, False,
         '512x512 slices, 0.3 overlap')

arrow(9.8, 6.42, 10.3, 6.42, b_dl)

draw_box(7.3, 5.0, 2.5, 0.65, '7-Class Detection', c_dl, b_dl, 8, True,
         'mAP@0.5 = 32.5%')
draw_box(10.3, 5.0, 2.5, 0.65, 'Freshness Scoring', c_dl, b_dl, 8, False,
         'good / moderate / poor ratio')

arrow(8.55, 6.1, 8.55, 5.65, b_dl)
arrow(9.8, 5.32, 10.3, 5.32, b_dl)

# DL Output
draw_box(8.3, 3.9, 3.5, 0.7, 'Freshness Grade (A-D)', c_output, b_output, 9, True,
         'A>=70% / B>=50% / C>=30% / D<30%')
arrow(11.55, 5.0, 10.05, 4.6, b_output)

# ============================================================
# RIGHT SIDE: RAG ADVISORY (x: 13.5-17.5)
# ============================================================
label(15.5, 10.5, 'RAG ADVISORY', b_rag)
ax.text(15.5, 10.1, '(Independent System)', ha='center', va='center',
        fontsize=7, color='#795548', style='italic')

draw_box(13.8, 9.0, 3.4, 0.65, 'Knowledge Base', c_rag, b_rag, 8, True,
         '156 documents, 13 categories')
arrow(15.5, 9.0, 15.5, 8.55, b_rag)

draw_box(13.8, 7.85, 3.4, 0.65, 'Chunking & Embedding', c_rag, b_rag, 8, False,
         '473 chunks, Sentence-BERT, 384d')
arrow(15.5, 7.85, 15.5, 7.4, b_rag)

draw_box(13.8, 6.7, 3.4, 0.65, 'FAISS Index + BM25', c_rag, b_rag, 8, False,
         'Dense + sparse retrieval')
arrow(15.5, 6.7, 15.5, 6.25, b_rag)

draw_box(13.8, 5.55, 3.4, 0.65, 'Hybrid Retrieval (RRF)', c_rag, b_rag, 8, True,
         'alpha=0.5, top_k=5')
arrow(15.5, 5.55, 15.5, 5.1, b_rag)

draw_box(13.8, 4.4, 3.4, 0.65, 'Advisory Output', c_rag, b_rag, 8, True,
         'MRR=1.0, NDCG@5=1.0')

# ============================================================
# BOTTOM: DEPLOYMENT LAYER
# Rearranged: TeaVision (left), Streamlit (center), FastAPI (right under RAG)
# This ensures arrows go DOWN without crossing each other
# ============================================================
label(1.5, 3.1, 'DEPLOYMENT', b_deploy)

draw_box(1.5, 1.8, 5.0, 0.7, 'Streamlit Dashboard', c_deploy, b_deploy, 9, True,
         'YOLOv8 + SAHI + Grading UI')
draw_box(13.5, 1.8, 3.7, 0.7, 'FastAPI Backend', c_deploy, b_deploy, 9, True,
         'RAG serving, port 8000')

# Output -> Deployment arrows (all go downward, none cross)
arrow(2.95, 3.9, 3.2, 2.5, b_output)    # Binary Grade -> Streamlit left side
arrow(10.05, 3.9, 5.3, 2.5, b_output)   # Freshness Grade -> Streamlit right side
arrow(15.5, 4.4, 15.35, 2.5, b_rag)     # RAG Advisory -> FastAPI (straight down)

# Arrow labels (positioned to the side of each arrow, not on top)
ax.text(2.0, 3.35, 'quality\nresults', ha='center', va='center', fontsize=6,
        color=b_output, style='italic',
        bbox=dict(boxstyle='round,pad=0.12', facecolor='white', edgecolor='none'))
ax.text(10.5, 3.35, 'detection\nresults', ha='center', va='center', fontsize=6,
        color=b_output, style='italic',
        bbox=dict(boxstyle='round,pad=0.12', facecolor='white', edgecolor='none'))
ax.text(16.5, 3.5, 'advisory\nresponses', ha='center', va='center', fontsize=6,
        color=b_rag, style='italic',
        bbox=dict(boxstyle='round,pad=0.12', facecolor='white', edgecolor='none'))

# Bottom caption
ax.text(9, 1.15, 'Fig. X.  Component system architecture for Objective 1: Tea Leaf Freshness Grading.',
        ha='center', va='center', fontsize=8, color='#616161', style='italic')

plt.tight_layout()
plt.savefig('methodology_figures/Component_System_Architecture.png', dpi=200, bbox_inches='tight',
            facecolor='white', edgecolor='none')
print("Saved: methodology_figures/Component_System_Architecture.png")
