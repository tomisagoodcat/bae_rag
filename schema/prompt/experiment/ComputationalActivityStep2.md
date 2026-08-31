### **Define**
A **Computational Activity Step** (`whu:ComputationalActivityStep`) is the **minimal semantic unit** of computational research, representing a concrete data processing or analysis action.  
It:
- Declares a `whu:Method`.  
- Consumes inputs: `whu:DataSet`, `whu:Device` (e.g., server), or `whu:Software` (`prov:used`).  
- Generates outputs: new `whu:DataSet` (`prov:generated`).  
- Belongs to a `whu:Computational_Experiment` (`p-plan:isStepOfPlan`).  
- May map to a `p-plan:Step`.  

### **Context**
Extract when text describes **explicit computational operations** (e.g., statistical test, normalization, model fitting).  
Rules:  
1. **Atomic**: capture smallest meaningful step.  
2. **Sequential**:  
   - Output DataSet of one step → input of next (`prov:used`).  
   - Steps chained with `p-plan:isPrecededBy`.  
3. **Cross-chain**: datasets may originate from `whu:BioChemicalActivityStep` outputs, forming chains:  
   Specimen → BioChemicalActivityStep → DataSet → ComputationalActivityStep → Result.  
4. **Alignment**: each step tied to its parent `whu:Computational_Experiment` for provenance.  

### **Notes**
- Distinct from:  
  - `whu:Method`: abstract technique.  
  - `whu:BioChemicalActivityStep`: wet-lab step.  
- Granularity supports **workflow reconstruction** and **reproducibility**.  
- Relations:  
  - `prov:used` → DataSet, Software, Device.  
  - `prov:generated` → DataSet(s).  
  - `p-plan:isStepOfPlan` → Computational_Experiment.  
  - `p-plan:isPrecededBy` → previous step.  
  - Input DataSet may come from BioChemicalActivityStep.  

### **Examples**
- *“Log-transform concentration values.”*  
  → Step:  
  - prov:used = DataSet(raw), Software(R)  
  - prov:generated = DataSet(log values)  

- *“Run one-way ANOVA to test treatment effects.”*  
  → Step:  
  - prov:used = DataSet(log values), Software(SPSS)  
  - prov:generated = DataSet(ANOVA results)  
  - isPrecededBy = log-transformation  

- *“Compute Pearson correlation between mercury and DOM.”*  
  → Step:  
  - prov:used = DataSet(ANOVA results), Software(R)  
  - prov:generated = DataSet(correlation)  

1. **Kruskal-Wallis Test**  
   - Action: test effects of biochar treatments.  
   - Method: non-parametric Kruskal-Wallis + post hoc.  
   - prov:used: DataSet(parameters from BioChemical steps), Software(R 4.1.0 + pgirmess).  
   - prov:generated: DataSet(p-values).  
   - isStepOfPlan: Statistical analysis.  

2. **SUVA254 Calculation**  
   - Action: characterize DOM aromaticity.  
   - Method: absorbance at 254 nm / DOC concentration.  
   - prov:used: DataSet(UV-Vis data, DOC conc.), Software(Aqualog®).  
   - prov:generated: DataSet(SUVA254 values).  
   - isStepOfPlan: DOM characterization.  
 
