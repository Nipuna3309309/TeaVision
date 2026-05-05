# 4.1. Key Insights

## Objective 1 – Tea Leaf Freshness Grading Key Insights

### Data Quality Analysis

| Quality Metric | Pass Rate | Primary Failure Mode |
|----------------|-----------|----------------------|
| Resolution | 98.5% | Operator selecting low-resolution mode |
| Blur Score | 85.2% | Hand movement during capture |
| Brightness | 91.3% | Capturing in shaded areas |
| Glare | 94.7% | Direct sunlight hitting the leaf surface |
| Background | 88.9% | Not enough background cloth coverage |
| **Overall Pass** | **78.4%** | **Failures tend to cluster in poor capture conditions** |

The overall pass rate of 78.4% is higher than what independent failure rates would predict (~64.5%), because failures tend to happen together in the same problematic images. For example, capturing in a shaded spot can cause both brightness and background failures at the same time. This means a smaller group of difficult captures accounts for most rejections, while the rest pass all checks cleanly.

**Insight 1 – Sensor-guided capture reduces blur:** The TeaVision app uses tilt and stability sensors to guide the user during capture. This reduced blur-related rejections from about 25% during early unguided pilot captures to 8% after the sensor-guided system was introduced.

### Segmentation Performance

| Method | Confidence | Detection Rate | False Positive Rate |
|--------|------------|----------------|---------------------|
| TensorFlow Lite Model | 0.90 | 94.2% | 3.1% |
| Colour-Based Fallback | 0.70 | 82.7% | 8.5% |

**Insight 2 – Dual segmentation ensures device coverage:** The TF Lite model gives the best results (94.2% detection, 3.1% false positives) on devices that support it. For older or less powerful phones, the colour-based fallback still detects over 80% of leaves on white backgrounds, making sure the app works on any device.

**Insight 3 – Morphological post-processing reduces noise:** Applying erosion followed by dilation to the segmentation mask removes small noise spots and smooths out rough edges, cutting false positive rates by about 40%.

### Colour-Freshness Correlation

| Freshness Grade | Mean Greenness Index | Mean Colour Uniformity | Mean Brownness Index |
|-----------------|----------------------|------------------------|----------------------|
| Fresh (Grade A) | 0.72 ± 0.08 | 0.85 ± 0.06 | 0.12 ± 0.05 |
| Moderate (Grade B) | 0.55 ± 0.10 | 0.72 ± 0.09 | 0.28 ± 0.08 |
| Stale (Grade C) | 0.38 ± 0.12 | 0.61 ± 0.11 | 0.45 ± 0.10 |

**Insight 4 – Colour features strongly indicate freshness:** There is a strong negative correlation (r = −0.78) between greenness and brownness. As leaves age, green colour fades and brown colour increases. Fresh leaves scored 0.72 on the greenness index compared to just 0.38 for stale leaves, confirming that colour change is a reliable way to measure freshness.

**Insight 5 – Colour uniformity signals quality:** Colour uniformity has a moderate correlation (r = 0.62) with freshness grade. Fresh leaves tend to have even, consistent colour, while older leaves develop patchy or uneven colouring.

**Insight 6 – QR-based calibration enables real-world measurements:** Using a QR code as a size reference, the system calculates 80–150 pixels per cm at a 25–35 cm capture distance, with an accuracy of ±2 mm. This allows the app to measure actual leaf dimensions consistently across different phone cameras.

**Insight 7 – Field lighting needs normalization:** Outdoor lighting changes throughout the day (morning vs. afternoon, sunny vs. cloudy) cause brightness to shift by about ±30 units on the 0–255 scale. This means brightness normalization is needed during preprocessing to keep colour readings accurate.

**Insight 8 – Leaf area as a secondary quality indicator:** Properly plucked tea (two leaves and a bud) has leaf areas of 5–25 cm², while roughly plucked tea exceeds 30 cm². This size difference can serve as an additional feature to assess plucking quality.

---

# 4.2. Challenges Faced During Data Analysis

The analysis of our datasets presented several challenges, mainly during the data gathering and preprocessing stages. The key challenges are listed below:

## 1. Data Collection Challenges

- Although public datasets were available, collecting data that matches Sri Lankan tea estate conditions was difficult. Field data collection needed consistent lighting, camera angles, and backgrounds.
- In some cases, certain disease, pest, or invasive species categories had fewer samples, creating class imbalance.
- **[Obj 1]** Freshness grade labelling needed domain expert judgment, which introduces subjectivity. Different assessors may give different grades to borderline samples. To reduce this, all 275 original labels were manually audited for consistency.
- **[Obj 1]** Early tea leaf collection was biased toward fresh samples because field visits coincided with recent plucking. Fresh leaves were easy to find, while aged or damaged samples had to be collected deliberately.

## 2. Data Quality and Variability

- The datasets had variations in image quality, background noise, and how symptoms appear. Tea leaf diseases and pest damage often look similar, making accurate classification harder.
- Auction and yield datasets also needed careful checking due to inconsistent formatting across sources.
- **[Obj 1]** Different smartphone cameras reproduce colours differently and use different white balance and exposure settings. This affects how well the model works across devices, especially for colour-based features like greenness and brownness indices.
- **[Obj 1]** Outdoor lighting changes (shadows from trees, cloud cover, time-of-day shifts) cause brightness to vary by about ±30 units, so preprocessing normalization is needed before extracting colour features.

## 3. Preprocessing and Data Cleaning Issues

- Several preprocessing steps were needed, including image resizing, normalization, augmentation, and label verification.
- For yield analytics, handwritten logbooks needed OCR-based digitization, where unclear handwriting and missing entries reduced extraction accuracy.
- **[Obj 1]** Overlapping leaves, curled edges, and shadows create unclear boundaries during segmentation, which affects the accuracy of leaf measurements like area, width, and height.
- **[Obj 1]** Session-based data splitting is needed to prevent data leakage. Images from the same capture session share lighting, angles, and leaf arrangement, so randomly splitting across sessions would give misleadingly high performance numbers.

## 4. Handling Large-Scale Data

- The auction transaction dataset contained over 1.5 million records, which increased processing time and required grouping data into weekly trends to make forecasting manageable.

## 5. Computational and Training Limitations

- Training deep learning models required high computational resources.
- Limited hardware availability increased training time and restricted the number of experiments and hyperparameter tuning that could be done.
- **[Obj 1]** The current dataset of only 275 original images (augmented to 1,000) is relatively small for deep learning, which limits how well the model can generalize to new, unseen data. Continued data collection across more estates and seasons is planned to address this.
