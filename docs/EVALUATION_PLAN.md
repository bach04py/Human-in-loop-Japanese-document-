# EVALUATION PLAN - WEEK 1

**Engineer**: Tang My Han

---

This document outlines the evaluation protocols, key performance indicators (KPIs), datasets, and benchmark workflows to test the accuracy, speed, and cognitive load of the system.

---

### **1. Evaluation Goals**
The primary objectives of this evaluation are:
1. **OCR Quality**: Quantify OCR character accuracy under complex layouts (vertical text, dense grids, legibility noise).
2. **Extraction Integrity**: Measure the accuracy of structural entity extraction (Invoice ID, dates, monetary values).
3. **Human Effort Reduction**: Prove that the active **Correction Memory** reduces human intervention over time.
4. **Agent Choreography Efficiency**: Measure system latency and decision precision of the multi-agent routing.

---

### **2. Target Evaluation Metrics**

#### **2.1 Quantitative OCR Metrics**
* **Character Error Rate (CER)**:
  $$CER = \frac{S + D + I}{N}$$
  *Where $S$ is substitutions, $D$ is deletions, $I$ is insertions, and $N$ is the total characters in the ground truth.*
* **Word/Token Accuracy**: Percentage of words perfectly parsed without individual character splits.

#### **2.2 Quantitative Structural Extraction Metrics**
* **Field Precision, Recall, and F1-Score**: Evaluated on key Pydantic fields.
* **Schema Integrity Rate**: Percentage of extractions conforming to the desired JSON schemas without syntax errors.

#### **2.3 Human-in-the-Loop & Efficiency Metrics**
* **Correction Reduction Rate (CRR)**: Measures the rate of decrease in manual field corrections over successive document imports.
  $$CRR_k = \frac{\text{Edits in Document } 1 - \text{Edits in Document } k}{\text{Edits in Document } 1}$$
* **System Time Reduction**: Total seconds spent to achieve a 100% correct database record:
  $$\text{Manual Processing Time} \quad \text{vs} \quad \text{Baseline OCR Review Time} \quad \text{vs} \quad \text{Memory-assisted HITL Review Time}$$
* **Human Approval Rate**: Ratio of documents approved in the validation agent phase without requiring human correction.

---

### **3. Evaluation Datasets**

We will evaluate the system against three primary datasets representing diverse layout complexities:

| Dataset Name | Source / Type | Characteristics | Key Testing Domain |
| :--- | :--- | :--- | :--- |
| **NDL-OCR Dataset** | National Diet Library Japan | Historical Kanji, vertical text lines, scans with micro-blemishes | OCR Vertical Line Parsing |
| **Receipt-Japan (SROIE-style)** | Synthetic / Scanned receipts | Dense tables, diverse font styles, mixed English/Japanese characters | Multi-agent extraction |
| **Form-Corp-JP** | Standard corporate forms | Dynamic grid cells, handwritten signatures, dense margins | Structural & validation rules |

---

### **4. Experimental Protocol**

We will execute three consecutive experimental runs:

#### **Run A: Autonomous Baseline (No Human Interaction)**
* System processes all datasets fully autonomously.
* Outgoing records are saved exactly as returned by the Extraction/Validation agents.
* Ground truth is compared directly to calculate baseline autonomous CER and F1 scores.

#### **Run B: Standard HITL (Without Correction Memory)**
* Human reviews all outputs in the **Workspace Dashboard** and manually edits every incorrect field.
* Downstream data is saved with 100% human-verified accuracy.
* Log review time per document to measure human operational strain.

#### **Run C: Adaptive HITL (With PostgreSQL + Vector Correction Memory)**
* Human reviews and corrects outputs. Each correction is written to the **Correction Memory**.
* During successive document runs, the Extraction Agent retrieves semantically similar historical corrections.
* Measure the drop in manual corrections over a sequence of 20 documents from the same issuer.

---

### **5. Logging & Metrics Aggregation**
All experimental data will be stored in designated benchmarking tables in PostgreSQL:
* `metrics_ocr_run`: records character alignment, word accuracy, confidence levels.
* `metrics_extraction_run`: captures true/false positives on fields.
* `metrics_human_feedback`: stores editing duration (seconds), number of key-presses, and correction rate indexes.

*The aggregated metrics will be fed directly to the **Thesis & Metrics Dashboard** of the frontend to visualize the operational benefits of the HITL architecture.*
