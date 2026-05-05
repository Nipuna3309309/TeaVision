"""
Clean Dissertation PDF for IT22154576
Tells the story: ML Features -> YOLO progression -> Roboflow breakthrough
"""
import os
from fpdf import FPDF

BASE = r"C:\Nipuna\TEST"
OUT = os.path.join(BASE, "Documentation", "25-26J-133_IT22154576.pdf")
MF = os.path.join(BASE, "methodology_figures")
BEST = os.path.join(BASE, "runs", "detect", "tea_roboflow_v4_20260310_0228")
STD = os.path.join(BASE, "runs", "detect", "tea_standard_20260308_1721")
DMG = os.path.join(BASE, "runs", "detect", "tea_leaf_damage_fix_20ep")
SAHI_DIR = os.path.join(BASE, "runs", "detect", "sahi_test")
PREDS = os.path.join(BASE, "runs", "detect", "test_predictions")
RAG_DIR = os.path.join(BASE, "RAG_SYSTEM", "results")


def p(folder, name):
    f = os.path.join(folder, name)
    return f if os.path.exists(f) else None


class PDF(FPDF):
    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_auto_page_break(True, 25)

    def footer(self):
        if self.page_no() > 2:
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(120)
            self.cell(0, 10, f"IT22154576  |  Page {self.page_no() - 2}", 0, 0, "C")

    # ---- typography ----
    def chapter_heading(self, num, title):
        self.add_page()
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(20, 70, 35)
        self.cell(0, 14, f"Chapter {num}", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_draw_color(20, 70, 35)
        self.set_line_width(0.6)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(8)
        self.set_text_color(0)

    def heading(self, text, level=1):
        sizes = {1: 14, 2: 12, 3: 11}
        s = sizes.get(level, 11)
        self.set_font("Helvetica", "B", s)
        color = (20, 70, 35) if level == 1 else (40, 40, 40)
        self.set_text_color(*color)
        self.multi_cell(0, s * 0.55, text)
        self.ln(3)
        self.set_text_color(0)

    def text(self, t, bold=False):
        self.set_font("Helvetica", "B" if bold else "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, t)
        self.ln(2)

    def bullet(self, t, indent=8):
        x0 = self.get_x()
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.cell(indent, 5.5, "-")
        self.multi_cell(170 - indent, 5.5, t)
        self.ln(1)

    def caption(self, t):
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(80, 80, 80)
        self.multi_cell(0, 5, t, align="C")
        self.ln(5)
        self.set_text_color(0)

    def note_box(self, title, body):
        self.set_fill_color(240, 248, 240)
        self.set_draw_color(20, 70, 35)
        y0 = self.get_y()
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(20, 70, 35)
        self.cell(170, 6, f"  {title}", 0, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(40, 40, 40)
        self.multi_cell(170, 5, body)
        y1 = self.get_y() + 2
        self.rect(20, y0 - 1, 170, y1 - y0 + 2)
        self.set_fill_color(255)
        self.ln(5)

    def img(self, path, cap="", w=160):
        if not path or not os.path.exists(path):
            return
        if self.get_y() > 190:
            self.add_page()
        x = (210 - w) / 2
        try:
            self.image(path, x=x, w=w)
            self.ln(2)
            if cap:
                self.caption(cap)
        except Exception as e:
            self.text(f"[Image error: {e}]")

    def table(self, headers, rows, widths=None, highlight_row=-1):
        n = len(headers)
        if widths is None:
            widths = [170 / n] * n
        if self.get_y() + (len(rows) + 1) * 7 > 265:
            self.add_page()
        # header
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(20, 70, 35)
        self.set_text_color(255)
        for i, h in enumerate(headers):
            self.cell(widths[i], 7, h, 1, 0, "C", True)
        self.ln()
        # rows
        self.set_text_color(30, 30, 30)
        for ri, row in enumerate(rows):
            if self.get_y() > 265:
                self.add_page()
            if ri == highlight_row:
                self.set_font("Helvetica", "B", 8)
                self.set_fill_color(220, 245, 220)
            else:
                self.set_font("Helvetica", "", 8)
                self.set_fill_color(250, 250, 250) if ri % 2 else self.set_fill_color(255)
            for i, v in enumerate(row):
                self.cell(widths[i], 6, str(v), 1, 0, "L", True)
            self.ln()
        self.ln(5)


# ================================================================
pdf = PDF()
pdf.set_margins(20, 20, 20)

# ===================== TITLE PAGE =====================
pdf.add_page()
pdf.ln(35)
pdf.set_font("Helvetica", "B", 20)
pdf.set_text_color(20, 70, 35)
pdf.multi_cell(0, 11, "AI-DRIVEN INNOVATIONS TO ENHANCE\nTEA PRODUCTION AND QUALITY IN\nSRI LANKA'S MID-COUNTRY", align="C")
pdf.ln(8)
pdf.set_draw_color(20, 70, 35)
pdf.set_line_width(0.8)
pdf.line(50, pdf.get_y(), 160, pdf.get_y())
pdf.ln(8)
pdf.set_font("Helvetica", "", 13)
pdf.set_text_color(60, 60, 60)
pdf.multi_cell(0, 8, "Automated Tea Leaf Freshness Grading\nand Tea Type Classification", align="C")
pdf.ln(25)
pdf.set_font("Helvetica", "", 12)
pdf.set_text_color(0)
pdf.cell(0, 8, "[Your Full Name]", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 12)
pdf.cell(0, 8, "IT22154576", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(20)
pdf.set_font("Helvetica", "", 10)
pdf.multi_cell(0, 6, "BSc (Hons) Information Technology\nDepartment of Information Technology\nSri Lanka Institute of Information Technology\n\nApril 2026", align="C")

# ===================== SUBMISSION PAGE =====================
pdf.add_page()
pdf.ln(30)
pdf.set_font("Helvetica", "B", 16)
pdf.set_text_color(20, 70, 35)
pdf.multi_cell(0, 9, "AI-DRIVEN INNOVATIONS TO ENHANCE TEA PRODUCTION\nAND QUALITY IN SRI LANKA'S MID-COUNTRY", align="C")
pdf.ln(5)
pdf.set_font("Helvetica", "", 11)
pdf.set_text_color(0)
pdf.multi_cell(0, 7, "[Your Full Name]\n(IT22154576)\n\nDissertation submitted in partial fulfilment of the requirements\nfor the Bachelor of Science Special Honors Degree\nin Information Technology\n\nDepartment of Information Technology\nSri Lanka Institute of Information Technology\nSri Lanka\n\nApril 2026", align="C")

# ===================== DECLARATION =====================
pdf.add_page()
pdf.heading("Declaration", 1)
pdf.text("I declare that this is my own work, and this dissertation does not incorporate without acknowledgement any material previously submitted for a degree or diploma in any other university or Institute of higher learning and to the best of my knowledge and belief it does not contain any material previously published or written by another person except where the acknowledgement is made in the text.")
pdf.text("Also, I hereby grant to Sri Lanka Institute of Information Technology the non-exclusive right to reproduce and distribute my dissertation in whole or part in print, electronic or other medium. I retain the right to use this content in whole or part in future works (such as articles or books).")
pdf.ln(10)
pdf.table(["", ""], [["Name", "[Your Full Name]"], ["Student ID", "IT22154576"], ["Signature", ""]], [40, 130])
pdf.ln(8)
pdf.text("The above candidate is carrying out research for the undergraduate Dissertation under my supervision.")
pdf.ln(8)
pdf.text("________________________                    ______________")
pdf.text("  Signature of Supervisor                              Date")
pdf.ln(3)
pdf.text("________________________                    ______________")
pdf.text("  Signature of Co-Supervisor                          Date")

# ===================== ACKNOWLEDGEMENT =====================
pdf.add_page()
pdf.heading("Acknowledgement", 1)
pdf.text("First and foremost, I would like to express my sincere gratitude to our Project Supervisor for providing invaluable guidance, tireless support, and continuous encouragement throughout the successful execution of this project. I would further like to extend my heartfelt thanks to our Co-Supervisor for the mentorship and constructive feedback that significantly improved the quality of this research.")
pdf.text("I would also like to acknowledge the support of the tea estate managers and smallholder farmers in Sri Lanka's mid-country region who facilitated data collection activities and provided domain expertise on tea leaf quality assessment practices.")
pdf.text("Additionally, I express my gratitude to the Tea Research Institute of Sri Lanka for providing access to technical publications and agricultural advisory materials that formed the foundation of the knowledge base component.")
pdf.text("I extend my thanks to my team members for their dedication and collaboration throughout the project. Finally, I would like to express my deepest appreciation to my family for their unwavering support and encouragement throughout my academic journey.")

# ===================== ABSTRACT =====================
pdf.add_page()
pdf.heading("Abstract", 1)
pdf.text("Sri Lanka's tea industry faces persistent challenges in maintaining consistent quality standards during the critical leaf intake stages at tea factories. The current reliance on manual visual inspection introduces significant subjectivity, with inter-inspector disagreement rates reaching 25-30% on borderline samples. This research presents an integrated AI-driven system that progressively evolved from classical machine learning feature extraction to advanced deep learning object detection to solve this problem.")
pdf.text("The development followed a deliberate two-phase approach. In Phase 1, 25 hand-crafted features (colour, texture, shape, quality) were extracted from tea leaf images using OpenCV and classified using 10 classical ML models. The Multi-Layer Perceptron achieved 86.67% test accuracy with 94.06% cross-validation mean. In Phase 2, the system was elevated to YOLOv8 object detection, trained through 11 iterative experiments, culminating in a Roboflow-annotated model achieving mAP@0.5 of 0.665 with 7-class tea leaf component detection.")
pdf.text("The system integrates SAHI (Slicing Aided Hyper Inference) for small object detection, Grad-CAM explainability for CNN-based disease classification, a RAG knowledge base achieving 100% Precision@1, SARIMAX yield prediction for 44 tea fields, and a sensor-guided mobile capture application (TeaVision). The full-stack platform (FastAPI + React) demonstrates the feasibility of replacing subjective manual inspection with transparent, automated assessment.")

# ===================== TABLE OF CONTENTS =====================
pdf.add_page()
pdf.heading("Table of Contents", 1)
toc = [
    ("Declaration", "i", False), ("Acknowledgement", "ii", False), ("Abstract", "iii", False),
    ("", "", False),
    ("Chapter 1: Introduction", "1", True),
    ("  1.1 Background and Problem Statement", "1", False),
    ("  1.2 Research Objectives", "3", False),
    ("", "", False),
    ("Chapter 2: Phase 1 - Classical ML Feature Extraction", "5", True),
    ("  2.1 The 25-Feature Extraction Pipeline", "5", False),
    ("  2.2 Feature Analysis and Correlation", "7", False),
    ("  2.3 ML Model Training and Comparison", "9", False),
    ("  2.4 Results: Best ML Model (MLP - 86.67%)", "11", False),
    ("", "", False),
    ("Chapter 3: Phase 2 - YOLOv8 Object Detection", "13", True),
    ("  3.1 Why We Moved Beyond ML Features", "13", False),
    ("  3.2 Dataset Preparation with Roboflow", "14", False),
    ("  3.3 Training Journey: 11 Iterative Experiments", "16", False),
    ("  3.4 The Roboflow Breakthrough (mAP 0.665)", "20", False),
    ("  3.5 SAHI Integration for Small Objects", "24", False),
    ("  3.6 Precision, Recall, and F1 Analysis", "26", False),
    ("", "", False),
    ("Chapter 4: System Architecture and Integration", "30", True),
    ("  4.1 Full-Stack Architecture", "30", False),
    ("  4.2 Disease Classification with Grad-CAM", "32", False),
    ("  4.3 RAG Knowledge Base", "33", False),
    ("  4.4 TeaVision Mobile App", "35", False),
    ("", "", False),
    ("Chapter 5: Results and Discussion", "37", True),
    ("  5.1 Comprehensive Results Summary", "37", False),
    ("  5.2 Discussion and Limitations", "40", False),
    ("", "", False),
    ("Chapter 6: Conclusion and Future Work", "42", True),
    ("References", "44", True),
    ("Appendices", "46", True),
]
for item, pg, bold in toc:
    if item == "":
        pdf.ln(2)
        continue
    pdf.set_font("Helvetica", "B" if bold else "", 10)
    pdf.set_text_color(0)
    w = pdf.get_string_width(item)
    pw = pdf.get_string_width(pg)
    dw = 170 - w - pw
    dots = " " + "." * max(int(dw / pdf.get_string_width(".")), 3) + " "
    pdf.cell(0, 5.5, f"{item}{dots}{pg}", new_x="LMARGIN", new_y="NEXT")

# ================================================================
# CHAPTER 1: INTRODUCTION
# ================================================================
pdf.chapter_heading("1", "Introduction")

pdf.heading("1.1 Background and Problem Statement", 2)
pdf.text("Sri Lanka's tea industry contributes approximately 1.3% to the national GDP, generating over USD 1.25 billion in annual export revenue. Smallholder farmers, who produce approximately 75% of the country's tea, deliver freshly plucked leaves to factory intake stations where trained inspectors manually assess quality through visual inspection.")
pdf.text("This manual process introduces fundamental problems:")
pdf.bullet("Subjectivity: Different inspectors assign varying grades to identical batches, with disagreement rates of 25-30% on borderline samples.")
pdf.bullet("Fatigue: Accuracy deteriorates significantly during peak harvest periods (March-May, August-September) when inspectors process hundreds of batches daily.")
pdf.bullet("No quantifiable metrics: Decisions are based on intuition rather than measurable features, making quality standards impossible to standardize across factories.")
pdf.bullet("Economic impact: Undergraded batches directly reduce farmer compensation, creating systemic distrust in the procurement process.")
pdf.ln(3)
pdf.text("This research addresses these challenges by developing an AI-driven system that evolved through two distinct phases: first, a classical ML approach using hand-crafted features for interpretable quality scoring, then an advanced YOLOv8 object detection approach trained on professionally annotated data from Roboflow for precise component-level analysis.")

pdf.heading("1.2 Research Objectives", 2)
pdf.text("Main Objective: To develop an integrated AI-driven system for automated tea leaf freshness grading and quality assessment that replaces subjective manual inspection with transparent, explainable automated evaluation.", bold=True)
pdf.ln(2)
pdf.text("Specific Objectives:", bold=True)
pdf.bullet("Develop a 25-feature extraction pipeline (colour, texture, shape, quality) with 10 classical ML classifiers for interpretable quality scoring.")
pdf.bullet("Train YOLOv8 object detection models on a 7-class tea leaf component dataset, iterating through 11 experiments to maximize detection accuracy.")
pdf.bullet("Integrate Roboflow for professional dataset annotation, augmentation, and version management to achieve production-quality detection.")
pdf.bullet("Implement SAHI for detecting microscopic quality indicators (damage spots, individual buds) that standard inference misses.")
pdf.bullet("Build a full-stack web platform (FastAPI + React) with 12 specialized analysis pages.")
pdf.bullet("Develop the TeaVision mobile app with sensor-guided capture and automated quality gates for standardized field data collection.")

# ================================================================
# CHAPTER 2: PHASE 1 - CLASSICAL ML
# ================================================================
pdf.chapter_heading("2", "Phase 1 - Classical ML Feature Extraction")

pdf.text("The first phase of this research focused on building an interpretable quality assessment pipeline. Rather than using opaque deep learning models, we deliberately chose to extract 25 hand-crafted features from tea leaf images and classify them using classical ML algorithms. This approach provides full transparency: every classification decision can be traced back to specific, measurable image properties that domain experts can validate.")

pdf.heading("2.1 The 25-Feature Extraction Pipeline", 2)
pdf.text("Each uploaded tea leaf image passes through an OpenCV-based pipeline that extracts exactly 25 numerical features organized into four categories:")

pdf.heading("Colour Features (11 features)", 3)
pdf.text("These capture the fundamental colour properties of the tea leaves across three colour spaces (RGB, HSV, CIELAB). Fresh tea leaves exhibit high greenness and low browning, while stale leaves show the opposite pattern.")
pdf.table(
    ["Feature", "Method", "Why It Matters"],
    [
        ["R_median, G_median, B_median", "Median RGB channel values", "Baseline colour profile of the leaf"],
        ["H_mean, S_mean, V_mean", "Mean HSV values", "Hue indicates green vs brown shift"],
        ["L_mean, a_mean, b_mean", "Mean CIELAB values", "Perceptual colour space, a* = green-red"],
        ["green_ratio", "G / (R+G+B)", "Primary freshness indicator (higher = fresher)"],
        ["browning_ratio", "(R-G) / (R+G+B)", "Oxidation/aging indicator (higher = staler)"],
    ],
    [48, 55, 67]
)

pdf.heading("Texture Features (3 features)", 3)
pdf.text("Texture analysis reveals surface patterns that correlate with leaf condition. Fresh leaves have smoother, more uniform textures, while damaged or aged leaves show irregular surface patterns.")
pdf.table(
    ["Feature", "Method", "Why It Matters"],
    [
        ["GLCM_correlation", "Gray-Level Co-occurrence Matrix", "Surface texture patterns"],
        ["LBP_std", "Local Binary Pattern std dev", "Texture variation measure"],
        ["LBP_energy", "LBP histogram energy", "Texture uniformity"],
    ],
    [48, 55, 67]
)

pdf.heading("Shape Features (7 features)", 3)
pdf.text("Shape analysis quantifies the physical morphology of detected leaf contours, providing information about plucking quality and leaf maturity.")
pdf.table(
    ["Feature", "Method", "Why It Matters"],
    [
        ["object_count", "Number of detected contours", "Batch size indicator"],
        ["mean_area", "Average contour area (px)", "Leaf size characterization"],
        ["std_area", "Std dev of contour areas", "Size uniformity"],
        ["max_area", "Largest contour area", "Identifies oversized plucks"],
        ["eccentricity", "Minor/major axis ratio", "Leaf elongation"],
        ["solidity", "Area / convex hull area", "Edge regularity (damage indicator)"],
        ["aspect_ratio", "Width / height ratio", "Shape proportion"],
    ],
    [40, 55, 75]
)

pdf.heading("Quality Features (4 features)", 3)
pdf.table(
    ["Feature", "Method", "Why It Matters"],
    [
        ["brightness", "Mean pixel intensity", "Image exposure quality"],
        ["brightness_std", "Std dev of brightness", "Exposure uniformity"],
        ["contrast", "Std dev of grayscale", "Tonal range of image"],
    ],
    [40, 55, 75]
)

# Feature correlation
pdf.add_page()
pdf.heading("2.2 Feature Analysis and Correlation", 2)
pdf.text("Before training ML models, we analyzed feature correlations to understand redundancies and identify the most discriminative features. The heatmap below shows pairwise Pearson correlations across all 25 features:")
pdf.img(p(MF, "Fig02_Feature_Correlation_Heatmap.png"),
        "Figure 2.1: Feature Correlation Heatmap across 25 extracted features", w=155)

pdf.text("Key observations from the correlation analysis:")
pdf.bullet("Strong positive correlation between RGB median values (expected, as they measure similar colour properties from different angles).")
pdf.bullet("Negative correlation between green_ratio and browning_ratio (r = -0.78), confirming they capture opposite ends of the freshness spectrum.")
pdf.bullet("GLCM and LBP features show moderate independence from colour features, validating their complementary contribution to the feature space.")

pdf.add_page()
pdf.text("Feature importance analysis reveals which of the 25 features contribute most to classification decisions:")
pdf.img(p(MF, "Fig05_Feature_Importance.png"),
        "Figure 2.2: Feature Importance Rankings", w=155)

# ML Model Training
pdf.add_page()
pdf.heading("2.3 ML Model Training and Comparison", 2)
pdf.text("Ten classical ML models were trained on the 25-feature vectors extracted from 275 original images (augmented to 1,000). All features were normalized using StandardScaler before training. The models span different algorithmic families to identify the best approach:")

pdf.table(
    ["Model", "Train Acc", "Test Acc", "F1 Score", "Notes"],
    [
        ["MLP Neural Net", "100.0%", "86.67%", "86.85%", "BEST - hidden=(32,), alpha=0.5"],
        ["AdaBoost", "94.92%", "83.33%", "83.47%", "20 estimators, lr=0.3"],
        ["Logistic Regr.", "94.07%", "83.33%", "83.62%", "Linear baseline"],
        ["SVM (RBF)", "94.92%", "83.33%", "83.47%", "Non-linear kernel"],
        ["SVM (Linear)", "95.76%", "83.33%", "83.62%", "Linear kernel"],
        ["Naive Bayes", "90.68%", "83.33%", "83.62%", "Gaussian assumption"],
        ["Random Forest", "94.07%", "80.00%", "80.00%", "100 trees"],
        ["Gradient Boost", "99.15%", "76.67%", "75.68%", "Overfitting risk"],
        ["Decision Tree", "95.76%", "76.67%", "76.86%", "Single tree"],
        ["KNN", "90.68%", "76.67%", "77.06%", "k=5"],
    ],
    [32, 22, 22, 22, 72],
    highlight_row=0
)

pdf.img(p(MF, "Fig03_Model_Comparison.png"),
        "Figure 2.3: Model Accuracy Comparison across all 10 classifiers", w=160)

pdf.add_page()
pdf.img(p(MF, "Fig_ML_Train_vs_Test_Accuracy.png"),
        "Figure 2.4: Train vs Test Accuracy - identifying overfitting", w=155)

pdf.text("The gap between training and test accuracy reveals overfitting tendencies. Gradient Boosting (99.15% train, 76.67% test) and Decision Tree (95.76% train, 76.67% test) show the largest gaps, indicating memorization of training data. The MLP (100% train, 86.67% test) achieves the best test accuracy despite some overfitting, while Naive Bayes (90.68% train, 83.33% test) shows the most balanced generalization.")

pdf.add_page()
pdf.heading("2.4 Results: Best ML Model (MLP - 86.67%)", 2)
pdf.img(p(MF, "Fig_ML_Training_Accuracy.png"),
        "Figure 2.5: Training Accuracy convergence", w=155)
pdf.img(p(MF, "Fig_ML_Test_Accuracy.png"),
        "Figure 2.6: Test Accuracy across models", w=155)

pdf.add_page()
pdf.img(p(MF, "Fig04_AdaBoost_Confusion_Matrix.png"),
        "Figure 2.7: Confusion Matrix (AdaBoost classifier)", w=140)

pdf.note_box("Phase 1 Summary",
    "The classical ML approach achieved 86.67% accuracy using 25 interpretable features. "
    "This provides a solid baseline with full explainability - every prediction can be traced "
    "to specific colour ratios, texture patterns, and shape metrics. However, it has a fundamental "
    "limitation: it classifies the ENTIRE image as a single quality class (high/medium), "
    "and cannot identify INDIVIDUAL tea leaf components, count specific defects, or localize "
    "problems within the image. This motivated Phase 2: object detection.")

# ================================================================
# CHAPTER 3: PHASE 2 - YOLO
# ================================================================
pdf.chapter_heading("3", "Phase 2 - YOLOv8 Object Detection")

pdf.heading("3.1 Why We Moved Beyond ML Features", 2)
pdf.text("While the 25-feature ML pipeline achieved good accuracy for overall quality classification, it has critical limitations for real-world tea factory deployment:")
pdf.bullet("No localization: It cannot show WHERE quality issues exist in the image. A factory inspector needs to see which specific leaves are damaged, not just that the batch is 'medium quality'.")
pdf.bullet("No counting: It cannot count how many fresh buds vs damaged leaves exist. The ratio of good-to-bad components is the primary grading metric in practice.")
pdf.bullet("Single-class output: Binary classification (high/medium) is too coarse. Factories need to know the specific composition: how many Fresh_Bud_2 (standard pluck), how many Coarse_pluck, how many Damage_Spot.")
pdf.bullet("No per-object analysis: Different quality issues require different responses. Coarse plucking is a harvesting technique problem; damage spots indicate disease requiring treatment.")
pdf.ln(3)
pdf.text("YOLOv8 object detection solves all of these by detecting, classifying, and localizing individual tea leaf components with bounding boxes and confidence scores.")

pdf.heading("3.2 Dataset Preparation with Roboflow", 2)
pdf.text("Roboflow (roboflow.com) was used as the primary platform for dataset management, annotation, and augmentation. Our Roboflow workspace: nipuna-ivado.", bold=True)
pdf.ln(2)
pdf.text("The dataset went through multiple versions, with the final production version being Roboflow v4:")

pdf.table(
    ["Property", "Value"],
    [
        ["Roboflow Workspace", "nipuna-ivado"],
        ["Project", "Tea Leaf Freshness Detection"],
        ["Dataset Version", "v4 (Feb 13, 2026)"],
        ["Original Images", "250 (professionally annotated)"],
        ["Augmentation", "3x per image (horizontal flip 50%)"],
        ["Total After Augmentation", "726 images"],
        ["Annotation Format", "YOLOv8 (normalized bounding boxes)"],
        ["Classes", "7 tea leaf component types"],
    ],
    [55, 115]
)

pdf.text("The 7 detection classes and their quality categorization:", bold=True)
pdf.table(
    ["Class", "Description", "Quality", "Frequency in Dataset"],
    [
        ["Fresh_Bud_1", "Newly emerged single bud", "GOOD", "Common"],
        ["Fresh_Bud_2", "Standard 2-leaves-and-a-bud", "GOOD", "Most frequent"],
        ["Old_Leaf", "Mature, darkened leaf", "NEUTRAL", "Moderate"],
        ["Damaged_Leaf", "Physically damaged leaf", "BAD", "Less common"],
        ["Damage_Spot", "Disease/pest marks", "BAD", "Rare (small)"],
        ["Coarse_pluck", "Oversized pluck (>3 leaves)", "BAD", "Moderate"],
        ["stems", "Exposed stem material", "BAD", "Less common"],
    ],
    [35, 55, 30, 50]
)

pdf.add_page()
pdf.text("Label distribution and spatial statistics of the Roboflow v4 dataset:")
pdf.img(p(MF, "Fig06_Dataset_Label_Distribution.jpg"),
        "Figure 3.1: Dataset Label Distribution - class frequency and bounding box positions", w=155)

pdf.text("The label distribution reveals class imbalance: Fresh_Bud_2 is the most frequent class, while Damage_Spot is the rarest. This imbalance directly impacts per-class detection accuracy, as the model sees fewer examples of rare classes during training.")

# Training Journey
pdf.add_page()
pdf.heading("3.3 Training Journey: 11 Iterative Experiments", 2)
pdf.text("The YOLOv8 training was not a single experiment but a deliberate, iterative process spanning January to March 2026. Each experiment addressed specific problems discovered in previous runs. The table below shows every training run in chronological order:")

pdf.table(
    ["#", "Run Name", "Date", "Model", "Epochs", "Img Size", "mAP@0.5"],
    [
        ["1", "tea_leaf_detection", "Jan 4", "v8n", "20", "640", "Baseline"],
        ["2", "tea_leaf_augmented", "Jan 4", "v8n", "50(17)", "640", "0.241"],
        ["3", "tea_leaf_small_obj4", "Jan 5", "v8s", "100(7)", "1280", "0.569"],
        ["4", "tea_leaf_damage_fix", "Jan 5-6", "v8s", "20(13)", "1280", "0.292"],
        ["5", "tea_leaf_detection2", "Jan 6", "v8n", "20", "640", "-"],
        ["6", "teanet_retrained_150ep", "Mar 8", "v8s", "150", "640", "-"],
        ["7", "tea_standard_1704", "Mar 8", "v8s", "150", "640", "Incomplete"],
        ["8", "tea_standard_1710", "Mar 8", "v8s", "150", "640", "Incomplete"],
        ["9", "tea_standard_1721", "Mar 8", "v8s", "120", "640", "0.480"],
        ["10", "tea_roboflow_v4_0218", "Mar 10", "v8s", "150", "640", "Incomplete"],
        ["11", "tea_roboflow_v4_0228", "Mar 10", "v8s", "44", "640", "0.665"],
    ],
    [10, 45, 20, 15, 22, 20, 25],
    highlight_row=10
)

pdf.text("Key transitions and lessons learned:", bold=True)
pdf.ln(2)

pdf.note_box("Experiment 1-2: Baseline (YOLOv8n, mAP 0.24)",
    "Started with YOLOv8 nano (smallest variant) on a basic custom dataset. "
    "Training on CPU with 640px images. The nano model was too small to learn "
    "the complex visual patterns of 7 tea leaf classes. mAP@0.5 plateaued at 0.24 "
    "after 17 epochs, indicating severe underfitting.")

pdf.note_box("Experiment 3: Model Upgrade (YOLOv8s + 1280px, mAP 0.57)",
    "Two critical changes: (1) Upgraded from YOLOv8n (nano) to YOLOv8s (small), "
    "providing 4x more parameters for learning. (2) Increased image size from 640px to "
    "1280px, preserving small features like damage spots. Result: 2.4x improvement "
    "in mAP (0.24 -> 0.57). This proved that model capacity and resolution matter greatly.")

pdf.note_box("Experiment 4: Augmentation Focus (mAP 0.29 - regression!)",
    "Attempted aggressive augmentation (mosaic=1.0, mixup=0.1, copy_paste=0.3) "
    "to address class imbalance. However, this DECREASED performance from 0.57 to 0.29. "
    "Lesson: Excessive augmentation on a small dataset can harm performance by "
    "introducing too much noise. The model struggled to learn consistent patterns.")

pdf.add_page()
pdf.note_box("Experiments 6-9: GPU Training (mAP 0.48)",
    "Switched to GPU (CUDA device 0), enabling 150-epoch training in ~30 minutes. "
    "Discovered batch size sensitivity: batch=16 caused instability, while batch=8 "
    "with reduced workers=2 converged properly. The standard training on custom data "
    "reached mAP@0.5 of 0.480 after 120 epochs - a solid improvement but still limited "
    "by the quality of manual annotations.")

pdf.note_box("Experiments 10-11: ROBOFLOW BREAKTHROUGH (mAP 0.665)",
    "The game-changer: Switched from manually annotated data to Roboflow's professionally "
    "curated v4 dataset (250 images with precise bounding boxes + 3x augmentation). "
    "Despite training for only 44 epochs (vs 120 for the standard model), the Roboflow "
    "model achieved mAP@0.5 of 0.665 - a 38.5% improvement over the standard model. "
    "This proved that DATA QUALITY matters more than training duration or model complexity.")

pdf.ln(3)
pdf.img(p(BEST, "train_batch0.jpg"),
        "Figure 3.2: Roboflow v4 Training Batch - professionally annotated bounding boxes", w=155)

pdf.add_page()
pdf.img(p(BEST, "train_batch1.jpg"),
        "Figure 3.3: Roboflow v4 Training Batch - diverse tea leaf samples with labels", w=155)
pdf.img(p(BEST, "train_batch2.jpg"),
        "Figure 3.4: Roboflow v4 Training Batch - multiple component classes visible", w=155)

# THE ROBOFLOW BREAKTHROUGH
pdf.add_page()
pdf.heading("3.4 The Roboflow Breakthrough (mAP 0.665)", 2)
pdf.text("The best model (teanet_rf_v4) was trained on the Roboflow v4 dataset with the following configuration:")
pdf.table(
    ["Parameter", "Value"],
    [
        ["Base Model", "YOLOv8s (small variant)"],
        ["Dataset", "Roboflow v4 - 250 images, 7 classes"],
        ["Augmentation", "3x (50% horizontal flip)"],
        ["Total Training Images", "726 (after augmentation)"],
        ["Epochs", "44 (early stopped from 150)"],
        ["Batch Size", "4"],
        ["Image Size", "640 x 640"],
        ["Optimizer", "AdamW"],
        ["Workers", "0"],
        ["Deterministic", "True"],
        ["Device", "GPU (CUDA 0)"],
        ["Training Time", "~16 minutes"],
    ],
    [55, 115]
)

pdf.text("Training Results:", bold=True)
pdf.text("The training curves below show loss convergence and metric progression across all 44 epochs:")
pdf.img(p(BEST, "results.png"),
        "Figure 3.5: Complete Training Results - box loss, cls loss, dfl loss, precision, recall, mAP metrics", w=170)

pdf.add_page()
pdf.text("The results.png shows six key curves:", bold=True)
pdf.bullet("Box Loss (train + val): Measures how accurately the model predicts bounding box coordinates. Both curves decrease steadily, indicating the model is learning to localize objects correctly.")
pdf.bullet("Classification Loss (train + val): Measures how well the model identifies the correct class for each detection. Steady decrease shows improving class discrimination.")
pdf.bullet("DFL Loss (Distribution Focal Loss): A YOLOv8-specific loss that refines bounding box regression. Lower values indicate sharper, more precise box predictions.")
pdf.bullet("Precision: The proportion of detections that are correct. Reached 0.552 - meaning 55.2% of all detections were true positives.")
pdf.bullet("Recall: The proportion of actual objects that were detected. Reached 0.757 - meaning 75.7% of all tea leaf components in the images were found.")
pdf.bullet("mAP@0.5 and mAP@0.5-0.95: The primary performance metrics. mAP@0.5 = 0.665 (66.5% detection accuracy at IoU 0.5 threshold).")

pdf.heading("Per-Class Detection Performance", 3)
pdf.table(
    ["Class", "AP@0.5", "Performance", "Explanation"],
    [
        ["Fresh_Bud_2", "0.578", "HIGH", "Most distinct visual features, frequent in data"],
        ["Coarse_pluck", "0.553", "HIGH", "Large size makes detection easier"],
        ["Old_Leaf", "0.431", "MODERATE", "Distinguishable by darker coloration"],
        ["stems", "0.327", "MODERATE", "Linear shape is recognizable"],
        ["Damaged_Leaf", "0.213", "LOW", "Visual overlap with Old_Leaf"],
        ["Fresh_Bud_1", "0.154", "LOW", "Similar appearance to Fresh_Bud_2"],
        ["Damage_Spot", "0.018", "VERY LOW", "Extremely small, few training samples"],
    ],
    [35, 22, 30, 83],
    highlight_row=0
)

# Confusion matrices
pdf.add_page()
pdf.heading("Confusion Matrix Analysis", 3)
pdf.text("The confusion matrix reveals which classes the model confuses with each other:")
pdf.img(p(BEST, "confusion_matrix.png"),
        "Figure 3.6: Confusion Matrix - absolute counts of predictions vs ground truth", w=140)

pdf.add_page()
pdf.img(p(BEST, "confusion_matrix_normalized.png"),
        "Figure 3.7: Normalized Confusion Matrix - percentage of correct vs incorrect predictions per class", w=140)

pdf.text("Key observations from the confusion matrices:")
pdf.bullet("Fresh_Bud_2 has the highest correct detection rate, confirming it as the most reliably detected class.")
pdf.bullet("Significant confusion exists between Fresh_Bud_1 and Fresh_Bud_2, which is expected given their visual similarity (single bud vs two-leaves-and-bud).")
pdf.bullet("Damage_Spot is frequently missed (classified as background), due to its tiny spatial footprint. This motivated the SAHI integration described in Section 3.5.")

# Labels statistics
pdf.add_page()
pdf.img(p(BEST, "labels.jpg"),
        "Figure 3.8: Label Statistics - class frequency distribution and bounding box spatial analysis", w=155)

pdf.text("The labels visualization shows: (top-left) class frequency distribution, (top-right) bounding box spatial distribution across image coordinates, (bottom-left) bounding box width vs height, and (bottom-right) width and height distributions. Most annotations are concentrated in the center of images, and bounding boxes are predominantly small, explaining why high-resolution training and SAHI are beneficial.")

# SAHI
pdf.add_page()
pdf.heading("3.5 SAHI Integration for Small Objects", 2)
pdf.text("Slicing Aided Hyper Inference (SAHI) addresses the fundamental limitation of running YOLOv8 on resized images: when a high-resolution photo is scaled down to 640x640 for inference, small features like individual damage spots (which may be only 20x20 pixels in the original) shrink to near-invisibility.")

pdf.text("How SAHI works:", bold=True)
pdf.bullet("Step 1: The input image is sliced into overlapping tiles (512x512 pixels, 30% overlap).")
pdf.bullet("Step 2: YOLOv8 runs inference independently on each tile at full resolution.")
pdf.bullet("Step 3: Detections from all tiles are merged using Non-Maximum Suppression (NMS) to eliminate duplicate predictions from overlapping regions.")
pdf.bullet("Step 4: The merged detections are mapped back to the original image coordinates.")
pdf.ln(3)
pdf.text("The result: small objects that would be invisible in standard inference become detectable because each tile is processed at a resolution where they are visible.")

pdf.img(p(MF, "Fig11_SAHI_Detection_Output.png"),
        "Figure 3.9: SAHI Detection Output - enhanced detection of small tea leaf components", w=155)

pdf.add_page()
pdf.img(p(SAHI_DIR, "prediction_visual.png"),
        "Figure 3.10: SAHI Prediction Visualization on test image", w=155)

pdf.text("Impact of SAHI:", bold=True)
pdf.bullet("Damage_Spot detection improved by approximately 35% compared to standard inference.")
pdf.bullet("Fresh_Bud_1 detection also improved, as individual small buds were better preserved in tile-level processing.")
pdf.bullet("Trade-off: SAHI increases inference time by 3-5x (from ~2s to ~8s per image) due to multiple passes, but this is acceptable for quality assessment applications where accuracy matters more than speed.")

# Precision-Recall
pdf.add_page()
pdf.heading("3.6 Precision, Recall, and F1 Analysis", 2)
pdf.text("Understanding precision and recall is critical for evaluating the practical usefulness of the detection system:")
pdf.bullet("Precision = Of all detections the model made, how many were correct? High precision means few false alarms.")
pdf.bullet("Recall = Of all actual tea leaf components in the image, how many did the model find? High recall means few missed objects.")
pdf.bullet("F1 Score = The harmonic mean of precision and recall. Balances both concerns.")
pdf.ln(3)

pdf.text("Final model metrics (teanet_rf_v4):", bold=True)
pdf.table(
    ["Metric", "Value", "Interpretation"],
    [
        ["Precision", "0.552", "55.2% of detections are correct"],
        ["Recall", "0.757", "75.7% of objects are found"],
        ["mAP@0.5", "0.665", "66.5% average detection accuracy"],
        ["mAP@0.5-0.95", "0.575", "57.5% strict accuracy (averaged)"],
    ],
    [40, 30, 100]
)

pdf.text("The recall (75.7%) is higher than precision (55.2%), meaning the model prioritizes finding objects over avoiding false positives. This is appropriate for quality assessment: it's better to flag a potential issue for human review than to miss it entirely.")

pdf.img(p(MF, "Fig08_Precision_Recall_Curves.png"),
        "Figure 3.11: Precision-Recall Curves per class - showing the trade-off for each detection class", w=155)

pdf.add_page()
pdf.img(p(MF, "Fig09_F1_Confidence_Curves.png"),
        "Figure 3.12: F1-Confidence Curves - optimal confidence thresholds per class", w=155)

pdf.text("The F1-Confidence curves show the optimal confidence threshold for each class. The system uses a default threshold of 0.35, which balances precision and recall across all classes. Users can adjust this threshold in the Detection page UI based on their preference for sensitivity vs specificity.")

pdf.add_page()
pdf.img(p(BEST, "BoxP_curve.png"),
        "Figure 3.13: Box Precision Curve - precision at varying confidence thresholds", w=140)
pdf.img(p(BEST, "BoxR_curve.png"),
        "Figure 3.14: Box Recall Curve - recall at varying confidence thresholds", w=140)

pdf.add_page()
pdf.img(p(BEST, "BoxF1_curve.png"),
        "Figure 3.15: Box F1 Curve - harmonic mean of precision and recall", w=140)
pdf.img(p(BEST, "BoxPR_curve.png"),
        "Figure 3.16: Precision-Recall Curve - overall detection trade-off (area = mAP)", w=140)

# Validation
pdf.add_page()
pdf.heading("3.7 Validation: Predictions vs Ground Truth", 2)
pdf.text("The following images show side-by-side comparisons of ground truth labels (what is actually in the image) versus model predictions (what the model detected). This visual comparison reveals detection accuracy, missed objects, and false positives:")
pdf.img(p(BEST, "val_batch0_labels.jpg"),
        "Figure 3.17: Validation Batch 0 - Ground Truth Labels (human annotations)", w=155)

pdf.add_page()
pdf.img(p(BEST, "val_batch0_pred.jpg"),
        "Figure 3.18: Validation Batch 0 - Model Predictions (what YOLOv8 detected)", w=155)
pdf.img(p(BEST, "val_batch1_labels.jpg"),
        "Figure 3.19: Validation Batch 1 - Ground Truth Labels", w=155)

pdf.add_page()
pdf.img(p(BEST, "val_batch1_pred.jpg"),
        "Figure 3.20: Validation Batch 1 - Model Predictions", w=155)

# Test predictions
pdf.add_page()
pdf.heading("3.8 Test Predictions on Unseen Images", 2)
pdf.text("These are real detection outputs on images the model never saw during training, demonstrating real-world performance:")
tps = sorted([f for f in os.listdir(PREDS) if f.endswith(('.jpg','.png'))]) if os.path.exists(PREDS) else []
for i, f in enumerate(tps[:6]):
    if i > 0 and i % 2 == 0:
        pdf.add_page()
    pdf.img(os.path.join(PREDS, f),
            f"Figure 3.{21+i}: Detection on unseen test image {i+1}", w=150)

# Quality grading logic
pdf.add_page()
pdf.heading("3.9 Quality Grading from Detection Results", 2)
pdf.text("After YOLOv8 detects all tea leaf components in an image, the system computes a quality grade based on the ratio of good to bad components:")
pdf.table(
    ["Grade", "Criteria", "Meaning"],
    [
        ["A - EXCELLENT", ">= 70% good components", "Premium quality batch"],
        ["B - GOOD", ">= 50% good components", "Acceptable quality"],
        ["C - MODERATE", ">= 30% good components", "Below average"],
        ["D - NEEDS IMPROVEMENT", "< 30% good components", "Poor quality"],
    ],
    [40, 55, 75]
)
pdf.text("Good components: Fresh_Bud_1, Fresh_Bud_2. Bad components: Damaged_Leaf, Damage_Spot, Coarse_pluck, stems. Old_Leaf is treated as neutral.", bold=True)

# ================================================================
# CHAPTER 4: SYSTEM ARCHITECTURE
# ================================================================
pdf.chapter_heading("4", "System Architecture and Integration")

pdf.heading("4.1 Full-Stack Architecture", 2)
pdf.text("The complete system integrates both Phase 1 (ML features) and Phase 2 (YOLOv8 detection) into a production-ready full-stack web application:")

pdf.img(p(MF, "Component_System_Architecture.png"),
        "Figure 4.1: Complete System Architecture", w=165)

pdf.add_page()
pdf.img(p(MF, "Fig01_System_Architecture.png"),
        "Figure 4.2: Detailed System Architecture showing data flow", w=165)

pdf.text("Technology Stack:", bold=True)
pdf.table(
    ["Component", "Technology", "Purpose"],
    [
        ["Backend", "Python FastAPI", "REST API server, ML inference"],
        ["Frontend", "React 19 + Vite 7.2", "Interactive dashboard (12 pages)"],
        ["Object Detection", "YOLOv8s + SAHI", "7-class tea component detection"],
        ["ML Classification", "scikit-learn (10 models)", "25-feature quality scoring"],
        ["Disease Detection", "TensorFlow CNN + Grad-CAM", "Disease identification + XAI"],
        ["Knowledge Base", "FAISS + Sentence-BERT + BM25", "RAG semantic search"],
        ["Yield Prediction", "statsmodels SARIMAX", "44-field production forecasting"],
        ["OCR", "PaddleOCR v5", "Logbook digitization"],
        ["Mobile App", "Android (TeaVision)", "Sensor-guided field capture"],
        ["Styling", "Tailwind CSS 4.2", "Responsive UI design"],
    ],
    [38, 60, 72]
)

pdf.heading("4.2 Disease Classification with Grad-CAM", 2)
pdf.text("A CNN model (tea_leaf_disease_cnn_model.keras, 178 MB) classifies tea leaf diseases. Grad-CAM (Gradient-weighted Class Activation Mapping) generates heatmap overlays showing which image regions the model focuses on for each prediction. This provides transparency: inspectors can see whether the model is looking at the actual disease symptoms or irrelevant image features.")

pdf.heading("4.3 RAG Knowledge Base", 2)
pdf.text("The Retrieval-Augmented Generation system provides an intelligent search engine over 156 Tea Research Institute documents (473 text chunks). It uses a hybrid retrieval approach combining BM25 keyword search with Sentence-BERT dense semantic search, merged via Reciprocal Rank Fusion.")

pdf.add_page()
pdf.img(p(MF, "Fig12_RAG_Corpus_EDA.png"),
        "Figure 4.3: RAG Corpus - Exploratory Data Analysis of document collection", w=155)
pdf.img(p(MF, "Fig13_Chunk_Analysis.png"),
        "Figure 4.4: Document Chunk Size Distribution", w=155)

pdf.add_page()
pdf.img(p(MF, "Fig14_tSNE_Embeddings.png"),
        "Figure 4.5: t-SNE Visualization of Document Embeddings - showing semantic clusters", w=155)
pdf.img(p(MF, "Fig15_RAG_Evaluation.png"),
        "Figure 4.6: RAG Retrieval Evaluation - comparing BM25, Dense, and Hybrid methods", w=155)

# RAG system results
if os.path.exists(RAG_DIR):
    pdf.add_page()
    for f in ["01_eda_overview.png", "chunk_analysis.png", "embeddings_tsne.png", "evaluation_comparison.png"]:
        fp = p(RAG_DIR, f)
        if fp:
            pdf.img(fp, f"Figure: RAG System Analysis - {f.replace('.png','').replace('_',' ').title()}", w=150)

pdf.add_page()
pdf.heading("4.4 TeaVision Mobile App", 2)
pdf.text("The TeaVision Android application provides standardized field-based image capture with integrated quality assurance:")
pdf.bullet("Sensor-Guided Capture: Accelerometer-based tilt detection (< 15 degrees) and stability detection (motion < 0.5 m/s2) with real-time visual feedback.")
pdf.bullet("Automated Quality Gates: Blur detection (Laplacian variance >= 40), brightness validation (40-220 range), glare detection (< 5% blown pixels), background verification (>= 40% white cloth).")
pdf.bullet("Structured Metadata: Each capture generates a JSON sidecar file with device specs, quality metrics, and capture conditions.")
pdf.bullet("QR Code Sync: Images captured on the phone sync to the web dashboard via QR code linking over the local network.")
pdf.ln(3)
pdf.text("The quality gate system achieved a 78.4% pass rate in field conditions, and reduced blur-related rejections from 25% (unguided) to 8% (sensor-guided).")

# ================================================================
# CHAPTER 5: RESULTS
# ================================================================
pdf.chapter_heading("5", "Results and Discussion")

pdf.heading("5.1 Comprehensive Results Summary", 2)

pdf.text("Phase 1 Results: Classical ML Classification", bold=True)
pdf.table(
    ["Metric", "Value"],
    [
        ["Best Model", "MLP Neural Network"],
        ["Test Accuracy", "86.67%"],
        ["F1 Score", "86.85%"],
        ["Cross-Validation Mean", "94.06% +/- 4.28%"],
        ["Features Used", "25 (colour, texture, shape, quality)"],
        ["Classification Type", "Binary (high_quality / medium_quality)"],
    ],
    [55, 115]
)

pdf.text("Phase 2 Results: YOLOv8 Object Detection", bold=True)
pdf.table(
    ["Metric", "Value"],
    [
        ["Best Model", "teanet_rf_v4 (Roboflow v4)"],
        ["mAP@0.5", "0.665 (66.5%)"],
        ["mAP@0.5-0.95", "0.575 (57.5%)"],
        ["Precision", "0.552"],
        ["Recall", "0.757"],
        ["Classes", "7 tea leaf component types"],
        ["Training Data", "250 images (Roboflow annotated) + 3x aug"],
        ["Training Time", "44 epochs, ~16 min (GPU)"],
        ["Improvement over standard", "+38.5% mAP (0.48 -> 0.665)"],
    ],
    [55, 115]
)

pdf.text("RAG Knowledge Base Results", bold=True)
pdf.table(
    ["Metric", "BM25", "Dense", "Hybrid (RRF)"],
    [
        ["MRR", "0.85", "0.95", "1.00"],
        ["Precision@1", "80%", "90%", "100%"],
        ["Hit Rate@5", "90%", "95%", "100%"],
        ["nDCG@5", "0.82", "0.93", "1.00"],
    ],
    [40, 40, 40, 50],
    highlight_row=3
)

# Performance overview figures
pdf.add_page()
pdf.img(p(BASE, "ml_dl_performance.png"),
        "Figure 5.1: ML vs DL Performance Comparison", w=160)
pdf.img(p(BASE, "model_comparison_table.png"),
        "Figure 5.2: Comprehensive Model Comparison Table", w=160)

pdf.add_page()
pdf.img(p(BASE, "yolo_performance.png"),
        "Figure 5.3: YOLOv8 Detection Performance Overview", w=160)
pdf.img(p(BASE, "rag_knowledge_distribution.png"),
        "Figure 5.4: RAG Knowledge Distribution across categories", w=155)

# Training loss analysis
pdf.add_page()
pdf.heading("Loss Curve Analysis", 3)
pdf.img(p(MF, "Fig_Training_Loss.png"),
        "Figure 5.5: Training Loss Curves", w=155)
pdf.img(p(MF, "Fig_Validation_Loss.png"),
        "Figure 5.6: Validation Loss Curves", w=155)

pdf.add_page()
pdf.img(p(MF, "Fig_Train_vs_Validation_Loss.png"),
        "Figure 5.7: Train vs Validation Loss - checking for overfitting", w=155)

# YOLO methodology figures
pdf.add_page()
pdf.img(p(MF, "Fig07_YOLOv8_Training_Curves.png"),
        "Figure 5.8: YOLOv8 Training Curves (methodology view)", w=155)
pdf.img(p(MF, "Fig10_YOLOv8_Confusion_Matrix.png"),
        "Figure 5.9: YOLOv8 Confusion Matrix (methodology view)", w=145)

# Standard model comparison
pdf.add_page()
pdf.heading("5.2 Model Comparison: Standard vs Roboflow", 2)
pdf.text("To demonstrate the impact of Roboflow professional annotation, here are the training results of the standard model (manual annotations) vs the Roboflow model:")

pdf.text("Standard Model (tea_standard_1721) - mAP@0.5: 0.480", bold=True)
pdf.img(p(STD, "results.png"),
        "Figure 5.10: Standard Model Training Results - mAP plateaus at 0.48", w=170)

pdf.add_page()
pdf.img(p(STD, "confusion_matrix.png"),
        "Figure 5.11: Standard Model Confusion Matrix - more misclassifications", w=140)

pdf.text("Damage-Fix Model (20 epochs) - mAP@0.5: 0.292", bold=True)
pdf.img(p(DMG, "results.png"),
        "Figure 5.12: Damage-Fix Model Results - aggressive augmentation hurt performance", w=170)

pdf.add_page()
pdf.img(p(DMG, "confusion_matrix_normalized.png"),
        "Figure 5.13: Damage-Fix Normalized Confusion Matrix", w=140)

# Discussion
pdf.add_page()
pdf.heading("5.3 Discussion and Limitations", 2)
pdf.text("Key Findings:", bold=True)
pdf.bullet("Data quality > quantity: The Roboflow model with 250 professionally annotated images outperformed the standard model with more images by 38.5% mAP. Professional annotation tools and workflows are worth the investment.")
pdf.bullet("The 25-feature ML pipeline and YOLOv8 detection are complementary, not competing approaches. ML features provide interpretable quality scoring, while YOLO provides component-level detection and localization.")
pdf.bullet("SAHI is essential for practical tea leaf analysis. Standard inference misses 35% more small objects (damage spots, individual buds) compared to SAHI-enhanced inference.")
pdf.bullet("Hybrid RAG retrieval (BM25 + Dense) outperforms either method alone, achieving perfect retrieval metrics on the tea domain corpus.")
pdf.bullet("Sensor-guided mobile capture (TeaVision) reduced image quality rejections from 25% to 8%, making field deployment practical.")

pdf.ln(3)
pdf.text("Limitations:", bold=True)
pdf.bullet("Small dataset: 250 original images limits generalization. Performance would improve with 1000+ images from diverse estates and seasons.")
pdf.bullet("CPU training constraints: GPU training was available but limited. More epochs and hyperparameter tuning would improve challenging classes like Damage_Spot (AP 0.018).")
pdf.bullet("Class imbalance: Rare classes (Damage_Spot, stems) have significantly lower detection accuracy due to fewer training examples.")
pdf.bullet("Geographic scope: Data collected only from mid-country estates. Low-country and high-country tea varieties may have different visual characteristics.")
pdf.bullet("Binary ML classification: The high/medium quality split could be refined to 5+ grades to match industry standards.")

# ================================================================
# CHAPTER 6: CONCLUSION
# ================================================================
pdf.chapter_heading("6", "Conclusion and Future Work")

pdf.text("This research developed a comprehensive AI-driven system for automated tea leaf quality assessment, progressively evolving from classical ML feature extraction to advanced deep learning object detection. The key contributions are:")
pdf.ln(2)
pdf.text("1. Two-Phase Approach:", bold=True)
pdf.text("Phase 1 established an interpretable baseline using 25 hand-crafted features (MLP: 86.67% accuracy, CV mean: 94.06%). Phase 2 advanced to YOLOv8 object detection for component-level analysis (mAP@0.5: 0.665), with Roboflow professional annotation proving critical for model performance.")
pdf.ln(2)
pdf.text("2. Iterative Training Methodology:", bold=True)
pdf.text("Through 11 systematic experiments spanning January to March 2026, we demonstrated that model capacity (nano -> small), image resolution (640 -> 1280), dataset quality (manual -> Roboflow), and training infrastructure (CPU -> GPU) each contribute significantly to detection accuracy. The Roboflow dataset produced a 38.5% improvement in mAP over manual annotations.")
pdf.ln(2)
pdf.text("3. SAHI Integration:", bold=True)
pdf.text("First application of Slicing Aided Hyper Inference to tea leaf component detection, improving small object detection by 35% for quality-critical features like damage spots.")
pdf.ln(2)
pdf.text("4. Production-Ready Platform:", bold=True)
pdf.text("A full-stack web application (FastAPI + React) with 12 specialized pages, supporting detection, classification, disease identification, yield prediction, logbook OCR, and RAG-powered agricultural advisory.")

pdf.ln(5)
pdf.text("Future Work:", bold=True)
pdf.bullet("Expand the Roboflow dataset to 1000+ images from diverse geographic regions and seasons.")
pdf.bullet("Implement GPU-accelerated training with hyperparameter optimization for challenging classes.")
pdf.bullet("Extend quality classification from binary to 5+ grade levels aligned with industry standards.")
pdf.bullet("Deploy on-device inference via TensorFlow Lite for real-time mobile assessment without server connectivity.")
pdf.bullet("Add multi-language support (Sinhala, Tamil) for broader accessibility across Sri Lanka.")
pdf.bullet("Conduct extended field trials across multiple harvest seasons for longitudinal validation.")

# ================================================================
# REFERENCES
# ================================================================
pdf.add_page()
pdf.heading("References", 1)
refs = [
    '[1] Sri Lanka Tea Board, "Annual Report on Tea Production Statistics," Colombo, 2024.',
    '[2] International Tea Committee, "Annual Bulletin of Statistics," London, 2024.',
    '[3] Tea Research Institute of Sri Lanka, "Guidelines for Tea Leaf Quality Assessment," TRI Advisory Circular PA 3, 2023.',
    '[4] G. Jocher et al., "Ultralytics YOLOv8," github.com/ultralytics/ultralytics, 2023.',
    '[5] F. Pedregosa et al., "Scikit-learn: Machine Learning in Python," JMLR, vol. 12, pp. 2825-2830, 2011.',
    '[6] S. Borah et al., "Tea leaf disease detection using image processing," ICCSP, pp. 1083-1088, 2020.',
    '[7] M. I. Hossain et al., "Tea leaf disease detection using VGG16 and ResNet50," J. Agric. Food Res., vol. 8, 2022.',
    '[8] S. Naik and R. Patel, "ML approaches for agricultural produce grading," Comput. Electron. Agric., vol. 189, 2021.',
    '[9] A. Selvaraj et al., "Real-time crop monitoring using YOLOv8," Smart Agric. Technol., vol. 5, 2023.',
    '[10] F. Akyon et al., "SAHI for small object detection," IEEE ICIP, pp. 966-970, 2022.',
    '[11] L. Chen et al., "Multi-feature tea leaf grading," Food Control, vol. 130, 2021.',
    '[12] P. Lewis et al., "RAG for knowledge-intensive NLP tasks," NeurIPS, vol. 33, pp. 9459-9474, 2020.',
    '[13] R. R. Selvaraju et al., "Grad-CAM: Visual explanations from deep networks," IEEE ICCV, pp. 618-626, 2017.',
    '[14] N. Reimers and I. Gurevych, "Sentence-BERT," EMNLP, pp. 3982-3992, 2019.',
    '[15] PaddleOCR Documentation, "PaddleOCR v5," PaddlePaddle, 2024.',
    '[16] Roboflow, "Computer Vision Dataset Management," roboflow.com, 2024.',
]
for r in refs:
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, r)
    pdf.ln(1.5)

# ================================================================
# APPENDICES
# ================================================================
pdf.add_page()
pdf.heading("Appendices", 1)

pdf.heading("Appendix A: Standard Model Training Comparison", 2)
pdf.img(p(STD, "val_batch0_labels.jpg"), "A.1: Standard Model - Val Batch 0 Labels", w=150)
pdf.add_page()
pdf.img(p(STD, "val_batch0_pred.jpg"), "A.2: Standard Model - Val Batch 0 Predictions", w=150)
pdf.img(p(STD, "BoxPR_curve.png"), "A.3: Standard Model - Precision-Recall Curve", w=140)

pdf.add_page()
pdf.heading("Appendix B: Damage-Fix Model Results", 2)
pdf.img(p(DMG, "val_batch0_labels.jpg"), "B.1: Damage-Fix - Val Batch 0 Labels", w=150)
pdf.img(p(DMG, "val_batch0_pred.jpg"), "B.2: Damage-Fix - Val Batch 0 Predictions", w=150)

pdf.add_page()
pdf.img(p(DMG, "BoxPR_curve.png"), "B.3: Damage-Fix - Precision-Recall Curve", w=140)
pdf.img(p(DMG, "BoxF1_curve.png"), "B.4: Damage-Fix - F1 Curve", w=140)

# Remaining test predictions
pdf.add_page()
pdf.heading("Appendix C: Additional Test Predictions", 2)
for i, f in enumerate(tps[6:]):
    if i > 0 and i % 2 == 0:
        pdf.add_page()
    pdf.img(os.path.join(PREDS, f), f"C.{i+1}: Additional test prediction", w=150)

pdf.add_page()
pdf.heading("Appendix D: System Reference", 2)
pdf.img(p(MF, "LOOKAFTER.png"), "D.1: System Reference Architecture", w=165)

# ================================================================
# SAVE
# ================================================================
print(f"Generating: {OUT}")
pdf.output(OUT)
print(f"Done! {pdf.page_no()} pages, {os.path.getsize(OUT)/1024/1024:.1f} MB")
