 #### Define
A **BioChemicalExperiment** (`whu:BioChemicalExperiment`) is a **planned setup** (`mp:Representation ⊓ p-plan:Plan`) where **biochemical methods** act on **specimens** using instruments, reagents, and protocols.  
It has a **goal** (`whu:Goal`), consists of **BioChemicalActivitySteps** (`p-plan:isStepOfPlan`), and yields **outputs** (`whu:DataSet`, `whu:ProcessedSpecimen`) that support or challenge **Claims** (`mp:Claim`).  

---

#### Context
Trigger when text refers to:  
- Experiments with chemical/biological transformation, assays, or measurements.  
- Use of devices (ICP-MS, HPLC, GC-MS, fluorescence, TOC analyzer).  
- Mention of reagents/protocols.  
- Reporting outputs (concentration, spectra, isotope ratios).  
- A unifying explicit or implicit **goal**.  

*Note: Even without “experiment,” a chain of steps with a shared goal counts as one.*  

---

#### Examples
**Rice Pot Experiment**  
- **Goal**: test biochar effects on Hg cycling.  
- **Steps**: biochar modification, soil prep, cultivation, sampling, Hg analysis.  
- **Outputs**: DOC values, DOM indices, THg/MeHg in rice tissues.  

**Microcosm Batch Experiment**  
- **Goal**: evaluate biochar dose on MeHg mobility.  
- **Steps**: soil/biochar prep, incubation, sampling, MeHg quantification, microbial assays.  
- **Outputs**: MeHg in soils/water, partition coefficients, SRB/IRB counts.  
