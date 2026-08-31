
### **Define**

A **BioChemicalExperiment** (`whu:BioChemicalExperiment`) is a **planned experimental representation** (`mp:Representation ⊓ p-plan:Plan`) that applies **biochemical methods** (laboratory or field-based) to **specimens** or their **processed derivatives** using **instruments**, **reagents**, and standardized **protocols**.
It is composed of one or more **BioChemicalActivitySteps** (`p-plan:isStepOfPlan BioChemicalExperiment`), each of which contributes intermediate results (datasets, processed specimens) that serve as inputs for subsequent steps.

According to **OBI (Ontology for Biomedical Investigations)** and **CHEBI**, biochemical experiments aim at transforming, detecting, or quantifying chemical/biological entities (e.g., heavy metals, organic pollutants, metabolites, biomarkers).
The **core semantic features** are:

* A **Goal** (`whu:Goal`): the intended scientific outcome (e.g., quantify cadmium in rice, characterize dissolved organic matter).
* **Steps**: a chain of `whu:BioChemicalActivityStep`s, each using instruments/reagents and producing datasets or processed specimens.
* **Data/Evidence**: measurable outputs (`whu:DataSet`) that support or challenge scientific **Claims** (`mp:Claim`).

---

### **Purpose**

1. **Goal-driven Investigation**
   Every `whu:BioChemicalExperiment` is motivated by an explicit **Goal**, such as detecting pollutants, characterizing biogeochemical cycles, or quantifying biomarkers.

2. **Stepwise Execution**

   * Each `BioChemicalActivityStep` consumes specimens or intermediate outputs.
   * Sequential dependencies exist: results of step *n* become inputs of step *n+1*.
   * Steps collectively instantiate the experimental plan.

3. **Evidence Generation**
   Produces datasets (e.g., spectra, concentrations, chromatograms) that provide **traceable evidence** in scientific reasoning and can be reused by computational workflows (`whu:ComputationalActivityStep`).

---

### **Context**

Trigger `whu:BioChemicalExperiment` when text (explicitly or implicitly):

* Describes an **experiment** involving chemical/biological transformations, measurements, or assays on specimens.
* Reports **instrument use** (ICP-MS, HPLC, GC-MS, fluorescence spectrometer) or **reagents/protocols**.
* Provides **outputs as datasets** (e.g., pollutant concentration, spectral index, isotope ratio).
* States or implies a **scientific goal**.
* Even if the word *“experiment”* is not mentioned, **a combination of BioChemicalActivitySteps with a shared goal** should be recognized as one experiment.

**Semantic links**:

* `whu:hasGoal` → experiment’s scientific intent
* `whu:hasActivityStep` → constituent steps
* `p-plan:isStepOfPlan` → each ActivityStep is part of the experiment
* `prov:used` → devices, reagents
* `prov:generated` → datasets

---

### **Examples**

1.  **Rice Cultivation Pot-Experiments**
    *   **Goal**: The primary goals were to **investigate the changes in soil Dissolved Organic Matter (DOM) characteristics due to biochar application** and to **understand the impact of these DOM properties on methylmercury (MeHg) production in soils and its subsequent bioaccumulation in rice plants**. This aimed to gain insight into how biochar affects Hg behavior in rice paddy fields via the carbon and Hg cycles.
    *   **Planned Experimental Representation**: A **pot experiment was conducted at the greenhouse facility of Southwest University (SWU)** in Chongqing, China. This involved a controlled setup with different biochar treatments (original and selenium-modified) and a control.
    *   **Steps (Chain of `whu:BioChemicalActivityStep`s)**:
        *   **Biochar modification**: Chemically coating original pinecone-derived biochar with selenium.
        *   **Soil preparation**: Air-drying and sieving surface layer soil collected from SWU's monitoring base.
        *   **Pot setup and amendment**: Filling PVC buckets with soil, adding exogenous HgCl2 solution, and incorporating original or modified biochar at 0.2% weight/weight. Fertilizers (ammonium acetate, Ca(H2PO4)2, KCl) were also added.
        *   **Rice cultivation**: Flooding soil with deionized water and transplanting healthy rice seedlings (Oryza sativa L.) into each pot.
        *   **Sample collection**: Collecting porewater samples using a Rhizon sampler, soil samples (0–20 cm depth), and rice plants (roots, stalks, leaves, grains) at the mature stage.
        *   **DOM characterization**: Measuring DOM concentration (DOC) using a TOC analyzer, and performing fluorescence and UV-Vis measurements with an Aqualog® absorption-fluorescence spectrometer.
        *   **THg and MeHg determination**: Measuring total mercury (THg) in soil and rice plants using F-732 cold vapor atomic fluorescence spectroscopy (CVAAS) and MeHg using ethylated isothermal gas chromatography-cold atomic fluorescence method (GC-CVAFC).
    *   **Data/Evidence**: Measurable outputs included **DOC concentrations**, various **UV-Vis and fluorescence spectral parameters of DOM** (e.g., SUVA254, SR, HIX, BIX), and **THg and MeHg content in soil, porewater, and different rice tissues** (roots, stalks, leaves, grains).

2.  **Microcosm Batch Experiments for MeHg Production and Mobility**
    *   **Goal**: The objective was to **investigate the effects of different biochar (BC) doses on net methylmercury (MeHg) production and MeHg mobility/phytoavailability in soils under anoxic conditions**.
    *   **Planned Experimental Representation**: **Microcosm experiments were conducted** using 50-mL centrifuge tubes with specific soil and biochar amendments, incubated under controlled conditions.
    *   **Steps (Chain of `whu:BioChemicalActivityStep`s)**:
        *   **Soil and biochar preparation**: Air-drying, grinding, and sieving different Hg-contaminated paddy soils (W, X, Y) and producing bamboo-derived biochar via pyrolysis.
        *   **Microcosm setup**: Adding 6g of soil to centrifuge tubes, amending with varying biochar doses (0.3, 0.5, and 1%, w/w), and adding deionized water and sodium acetate.
        *   **Incubation**: Sealing and incubating tubes in a climate chamber at 28 °C in the dark for 14 days, with manual shaking.
        *   **Sampling and separation**: Sampling overlying water and solid soil particles in a glovebag filled with nitrogen, then centrifuging to separate them.
        *   **Overlying water analysis**: Filtering and preserving overlying water samples for dissolved MeHg determination.
        *   **MeHg concentration determination**: Measuring MeHg concentrations in both soil particles and overlying water using digestion and cold vapor atomic fluorescence spectrometric analysis (CVAFS).
        *   **Bacterial population quantification**: Quantifying the population sizes of sulfate-reducing bacteria (SRB) and iron-reducing bacteria (IRB) in high-dose BC-amended treatments using the most probable number (MPN) method.
    *   **Data/Evidence**: Outputs included **soil MeHg concentrations**, **dissolved MeHg concentrations in overlying water**, **MeHg partitioning coefficient (log Kd)**, **fraction of extractable MeHg in soils**, and **population sizes of SRB and IRB**.

3.  **Determination of THg and MeHg in Environmental Samples**
    *   **Goal**: The overarching goal of this experimental phase was the **accurate and quality-controlled determination of total mercury (THg) and methylmercury (MeHg) content** in various environmental samples including **soil, rice plant tissues, and porewater**.
    *   **Planned Experimental Representation**: This involved **standardized analytical methods and quality control procedures** performed in the Mercury Biogeochemistry Laboratory (MBL) at SWU.
    *   **Steps (Chain of `whu:BioChemicalActivityStep`s)**:
        *   **Sample preparation**: Freeze-drying and storing soil and plant samples at 4 °C. For analysis, grinding rice grains and straw into fine powders, and grinding roots after iron plaque removal.
        *   **THg determination in soil/rice**: Digestion of soil with ultrapure water and aqua regia, or rice samples with mixed acid (HNO3: H2SO4) in a water bath, followed by measurement using F-732 cold vapor atomic fluorescence spectroscopy (CVAAS).
        *   **THg determination in porewater**: Oxidation, purging, trapping, and cold vapor atomic fluorescence spectrometry following USEPA method 1631.
        *   **MeHg determination in soil/rice**: Extraction of soil or rice plants using diluted HNO3, CuSO4, and KOH-methanol solution, followed by CH2Cl2 extraction and analysis with ethylated isothermal gas chromatography-cold atomic fluorescence method (GC-CVAFC).
        *   **MeHg determination in porewater**: Distillation-ethylation method.
        *   **Quality control**: Using method blanks, spike recoveries, duplicates, and certified reference materials (CRMs) like citrus leaf, soil, and estuarine sediment.
    *   **Data/Evidence**: The main outputs were **quantified THg and MeHg concentrations** in ng/g or ng/L for soil, various rice tissues (roots, stalks, leaves, grains), and porewater. This data also included **detection limits (LOD)** and **recovery rates** for quality assurance.
 