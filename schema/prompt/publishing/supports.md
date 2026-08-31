 

### Define

`mp:supports` is an **argumentative relation** in the Micropublication ontology that links a **supporting Representation** (e.g., `whu:DataSet`, `whu:Method`, `mp:Statement`) to a **target Representation** (`mp:Claim` or `mp:Statement`) that it provides **affirmative evidence for**.

* It encodes the **positive evidential role** of scientific artifacts in the argumentative structure.
* Most importantly, it captures how **datasets validate or reinforce central claims** in a micropublication.
* This is the **positive counterpart** of `mp:challenges`.

---

### Purpose

* **Evidence Modeling**: Represent explicit evidence-based connections (e.g., *Dataset S1 supports Claim C1*).
* **Argument Construction**: Enable reasoning paths such as `whu:DataSet → mp:supports → mp:Claim`.
* **Methodological Traceability**: Capture when methods or intermediate statements provide grounding for claims.
* **Reproducibility Assurance**: Make explicit how claims are backed by empirical evidence or methodological context.

---

### Context

Use `mp:supports` **only** when the text explicitly signals a positive evidential relation.

Trigger phrases may include: *support(s)*, *provide(s) evidence for*, *validate(s)*, *confirm(s)*, *consistent with*, *corroborate(s)*, *demonstrate(s)*.


---

### Notes

* `mp:supports` always points **from evidence Representation → to Claim/Statement**.
* Typical evidence sources:

  * `whu:DataSet` (empirical or experimental evidence).
  * `whu:Method` (methodological validation).
  * `mp:Statement` (secondary/assertive support).
* A Representation can both **support one Claim** and **challenge another** depending on textual context.
* Ensure strict distinction:

  * **`mp:supports`** = strengthens / affirms.
  * **`mp:challenges`** = weakens / refutes.

---

### Examples

 
1.  **Supporting Representation**: `whu:DataSet` - The **experimental results** quantifying the reduction of methylmercury (MeHg) bioaccumulation in rice plants due to biochar addition, including statistical significance (p < 0.05).
    *   **Target Representation**: `mp:Claim` - **"The results showed that the addition of biochar, whether in original or modified form, significantly reduced the bioaccumulation of MeHg in rice plants, especially in hulls and grains** ( p < 0.05)".
    *   **Evidential Signal**: "**The results showed that** the addition of biochar... significantly reduced...".

2.  **Supporting Representation**: `whu:DataSet` - The **quantitative data displaying the MeHg and MeHg/THg ratios in soil** specifically for the modified biochar treatment, as presented in **Fig. 3 b and c**.
    *   **Target Representation**: `mp:Claim` - "This observation suggests that **only modified biochar in this study could effectively decrease MeHg production in paddy soils**".
    *   **Evidential Signal**: "**This observation suggests that**...".

3.  **Supporting Representation**: `whu:DataSet` - The **optical analysis data of soil porewater dissolved organic matter (DOM) characteristics** (e.g., a355, SUVA254, SR, HIX, normalized CDOM, and fluorescence peaks A, C, M, BIX values), depicted in **Fig. 2 b–k**.
    *   **Target Representation**: `mp:Statement` - "...the **optical analysis showed that DOM characteristics were significantly changed induced by biochar addition**".
    *   **Evidential Signal**: "the **optical analysis showed that** DOM characteristics were significantly changed...".

4.  **Supporting Representation**: `whu:DataSet` - The **measured concentrations of MeHg in different tissues of rice plants** (roots, stalks, leaves, and grains) across all treatments, visually detailed in **Fig. 4**.
    *   **Target Representation**: `mp:Claim` - "**The accumulation of MeHg in rice plants was significantly decreased in both types of biochar-amended soils compared to the control** ( Fig. 4 ) ( p < 0.05)".
    *   **Evidential Signal**: "The accumulation of MeHg in rice plants was significantly decreased... **( Fig. 4 )**".

5.  **Supporting Representation**: `mp:Statement` - "This study **observed increases in rice yield and biomass growth in the original and modified biochar treatments**".
    *   **Target Representation**: `mp:Claim` - "Thus, the '**bio-dilution effect' might partially contribute to the MeHg decreases in rice**".
    *   **Evidential Signal**: "**Thus**, the 'bio-dilution effect' might partially contribute...".

 
 