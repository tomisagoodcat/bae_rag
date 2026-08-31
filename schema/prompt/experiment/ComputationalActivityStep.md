 
### **Define**
A **Computational Activity Step** (`whu:ComputationalActivityStep`) is the **minimal semantic unit** of computational research activity, representing a **specific data processing, transformation, or analysis step actually performed** in the study.
It:

* Declares a `whu:Method` that specifies the computational procedure.
* Consumes **inputs**: `whu:DataSet`, `whu:Device` (e.g., server, workstation), or `whu:Software` (`prov:used`).
* Generates **outputs**: one or more new `whu:DataSet` objects (`prov:generated`).
* Is always part of a broader `whu:Computational_Experiment` (`p-plan:isStepOfPlan`).
* May correspond to a formal `p-plan:Step`.

---

### **Context**
Extract a `ComputationalActivityStep` whenever the text describes an **explicit computational action** (e.g., statistical test, normalization, model fitting, feature extraction).
Each step is:

1. **Atomic**: capture the smallest meaningful computational operation (not an entire analysis pipeline).
2. **Sequentially linked**:

   * The **output** (`whu:DataSet`) of one computational step is the **input** of the next (`prov:used`).
   * Steps are chained via `p-plan:isPrecededBy`.
3. **Cross-chain integration**:

   * Input datasets may originate from **BioChemicalActivitySteps** (e.g., instrument measurements).
   * This creates a **research workflow chain**: Specimen → BioChemicalActivityStep → DataSet → ComputationalActivityStep → Result DataSet.
4. **Experiment alignment**:

   * Each step should be aligned to its parent `whu:Computational_Experiment`, ensuring traceability of the computational research chain.

---

### **Notes**

* A `ComputationalActivityStep` differs from:

  * `whu:Method`: abstract technique, not an execution.
  * `whu:BioChemicalActivityStep`: wet-lab procedure, not data analysis.
* Capturing step-level granularity enables **workflow reconstruction, provenance tracing, and reproducibility validation**.
* Relations to ensure:

  * `prov:used` → DataSet, Software, Device.
  * `prov:generated` → new DataSet(s).
  * `p-plan:isStepOfPlan` → Computational\_Experiment.
  * `p-plan:isPrecededBy` → previous computational step(s).
  * Input DataSet may originate from BioChemicalActivityStep.

---

### **Examples**

  * “Log-transform concentration values.”
    → `ComputationalActivityStep`

    * prov\:used: DataSet(raw concentrations), Software(R script)
    * prov\:generated: DataSet(log-transformed values)
    * isStepOfPlan: Computational\_Experiment

  * “Run one-way ANOVA to test treatment effects.”
    → `ComputationalActivityStep`

    * prov\:used: DataSet(log-transformed values), Software(SPSS)
    * prov\:generated: DataSet(ANOVA results)
    * isPrecededBy: log-transformation step

  * “Compute Pearson correlation (r) between mercury and DOM concentrations.”
    → `ComputationalActivityStep`

    * prov\:used: DataSet(ANOVA results), Software(R)
    * prov\:generated: DataSet(correlation results)

 

1.  **Statistical Test of Treatment Effects (Kruskal-Wallis Test)**
    *   **Concrete computational action**: The **effects of different biochar treatments on various parameters were tested** using a non-parametric Kruskal-Wallis test.
    *   `whu:Method`: **Non-parametric Kruskal-Wallis test**, followed by non-parametric post hoc procedures using the Kruskalmc function.
    *   `prov:used` (Inputs):
        *   `whu:DataSet`: Data for various parameters collected from different biochar treatments (e.g., DOM characteristics, Hg concentrations in soil and rice plants). This data would originate from `whu:BioChemicalActivityStep` outputs.
        *   `whu:Software`: R version 4.1.0 and the `pgirmess` package.
    *   `prov:generated` (Outputs):
        *   `whu:DataSet`: Statistical test results, including p-values to determine significant differences (e.g., `p < 0.05`) between treatments.
    *   `whu:Computational_Experiment` (`p-plan:isStepOfPlan`): Statistical analysis of experimental data.

2.  **Calculation of Specific Ultraviolet Absorbance (SUVA254)**
    *   **Concrete computational action**: The **degree of aromaticity of Dissolved Organic Matter (DOM) was characterized** by calculating SUVA254.
    *   `whu:Method`: SUVA254 is calculated as the **absorbance of UV light at 254 nm, normalized to the Dissolved Organic Carbon (DOC) concentration**.
    *   `prov:used` (Inputs):
        *   `whu:DataSet`: UV-Vis absorption spectrum data (specifically absorbance at 254 nm) and DOC concentration data (in mg/L). These datasets would be outputs from `whu:BioChemicalActivityStep` like "DOM characterization" and "Dissolved Organic Carbon (DOC) Concentration Measurement".
        *   `whu:Software`: Aqualog® software (implied for initial spectral data processing/correction).
    *   `prov:generated` (Outputs):
        *   `whu:DataSet`: SUVA254 values, representing the degree of DOM aromaticity.
    *   `whu:Computational_Experiment` (`p-plan:isStepOfPlan`): DOM characterization.

3.  **Calculation of Human Health Hazard Quotient (HQ)**
    *   **Concrete computational action**: The **hazard of noncarcinogenic effects from methylmercury (MeHg) exposure via rice consumption was evaluated** by calculating the Hazard Quotient (HQ).
    *   `whu:Method`: HQ was calculated using the formula: **HQ = EDI / RfD**, where EDI (Estimated Daily Intake) = (CMeHg \* IR) / BW.
    *   `prov:used` (Inputs):
        *   `whu:DataSet`: CMeHg (MeHg concentration in brown rice, mg/kg), IR (daily rice intake rate, g/day), BW (average body weight, kg), and RfD (reference dose, 0.1 mg/kg/d). The CMeHg values are derived from `whu:BioChemicalActivityStep` outputs like "Determination of THg and MeHg" in rice plants.
    *   `prov:generated` (Outputs):
        *   `whu:DataSet`: HQ values (unitless) for adults and children.
    *   `whu:Computational_Experiment` (`p-plan:isStepOfPlan`): Human health risk assessment.
 