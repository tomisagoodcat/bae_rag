### **Define**
A **BioChemicalActivityStep** (`whu:BioChemicalActivityStep`) is the **minimal semantic unit** in a paper, representing a **concrete biochemical/lab action actually performed**.  

It:  
- Declares a `whu:Method`.  
- Consumes **inputs**: `whu:ProcessedSpecimen`, `whu:Reagent`, `whu:Device` (`prov:used`).  
- Generates **outputs**: `whu:ProcessedSpecimen` and/or `whu:DataSet` (`prov:generated`).  
- May occur in a `whu:ExecutionEnvironment`.  
- Is always part of a `whu:Bio_chemical_Experiment` (`p-plan:isStepOfPlan`).  

### **Context**
Extract when text describes an **actual experimental step** (e.g., digestion, separation, measurement).  
Key features:  
1. **Atomic**: smallest actionable unit.  
2. **Sequential**: outputs of one step = inputs of next (`prov:used`), linked by `p-plan:isPrecededBy`.  
3. **Cross-step**: outputs (`whu:DataSet`) may feed into a `whu:ComputationalActivityStep`.  
4. **Alignment**: steps link back to `whu:Bio_chemical_Experiment`, ensuring a coherent research chain.  

### **Notes**
- Different from `whu:Method` (abstract technique) and `whu:SpecimenCollectionFeature` (sampling).  
- Outputs may be **physical** (processed specimen) or **digital** (dataset).  
- Capturing step-level detail supports **workflow reconstruction** and **reproducibility**.  
- Relations:  
  - `prov:used` → inputs.  
  - `prov:generated` → outputs.  
  - `p-plan:isStepOfPlan` → experiment.  
  - `p-plan:isPrecededBy` → prior step.  
  - Data handoff → `whu:ComputationalActivityStep`.  

### **Examples**
- **Microwave digestion with HNO₃ (65%) using MARS 6**  
  - used: Reagent(HNO₃), Device(MARS 6), Specimen(sample)  
  - generated: ProcessedSpecimen(digested sample)  
  - isStepOfPlan: Experiment  

- **Run ICP-MS for elemental analysis**  
  - used: Device(ICP-MS), Specimen(digested sample)  
  - generated: DataSet(element concentrations)  
  - isPrecededBy: Digestion step  

- **Biochar modification**  
  - Action: original biochar coated with selenium using Na₂SeO₃ in supercritical CO₂ device; dried in vacuum oven.  
  - used: Biochar, Na₂SeO₃, methanol, devices.  
  - generated: Selenium-modified biochar.  
  - isStepOfPlan: Pot experiment.  

 
