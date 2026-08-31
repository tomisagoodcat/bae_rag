#### Define
A **BioChemicalExperiment** (`whu:BioChemicalExperiment`) is a **planned experimental setup** (`mp:Representation ⊓ p-plan:Plan`) involving **biochemical methods** applied to **specimens** using **instruments, reagents, and protocols**.  

It:
- Has a **scientific goal** (`whu:Goal`).
- Is composed of sequential **BioChemicalActivitySteps** (`p-plan:isStepOfPlan`).
- Produces measurable **outputs** (`whu:DataSet`, `whu:ProcessedSpecimen`) that support or challenge scientific **Claims** (`mp:Claim`).

---

#### Context
Trigger `BioChemicalExperiment` when text describes:
- **Experiments** with chemical/biological transformations, assays, or measurements.  
- Use of **devices** (ICP-MS, HPLC, GC-MS, fluorescence/TOC analyzer).  
- Use of **reagents/protocols**.  
- Reporting **data outputs** (concentrations, spectra, isotope ratios).  
- An **explicit or implicit goal** unifying multiple steps.  

*Note: Even if “experiment” is not mentioned, a chain of steps with a shared goal = one BioChemicalExperiment.*


---

#### Examples
- **Rice Pot Experiment**  
  - **Goal**: assess how biochar affects Hg cycling and bioaccumulation in rice.  
  - **Steps**: biochar modification, soil prep, pot setup, rice cultivation,0999990 sample collection, DOM and Hg measurement.  
  - **Outputs**: DOC data, DOM spectral indices, THg/MeHg levels in soil and rice tissues.  

- **Microcosm Batch Experiment**  
  - **Goal**: test biochar dose effects on MeHg production and mobility.  
  - **Steps**: soil/biochar prep, microcosm setup, incubation, sampling, MeHg quantification, microbial assays.  
  - **Outputs**: MeHg concentrations in soils/water, partition coefficients, SRB/IRB counts.  
