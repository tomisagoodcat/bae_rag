
**Define**
A **Device** (`whu:Device`) is a **scientific or analytical instrument** used in experimental procedures, particularly in **BioChemicalActivitySteps**.
According to **OBI (Ontology for Biomedical Investigations)**, a device is a **manufactured object** designed to perform a specific experimental function (e.g., measuring, detecting, transforming, or processing specimens).
Examples include:

* Laboratory instruments (ICP-MS, HPLC, GC-MS, UV-Vis spectrometer).
* Sample processing devices (centrifuge, microwave digestion system).
* Measurement devices (balances, sensors, pH meters).

---

**Context**

* Always extract a `whu:Device` when the text explicitly names an **instrument, equipment, or tool** used in experimental work.
* Devices are typically connected to:

  * `whu:BioChemicalActivityStep` → via `prov:used` (device consumed in an experimental step).
  * `whu:ComputationalActivityStep` (less common, e.g., GPU workstation, computing cluster).
* Capture brand, model, manufacturer, or serial number when stated.
* Treat **device mentions as unique identifiable entities** if detailed metadata (brand + model + SN) is given; otherwise group by brand/model.

---

**Notes**

* **Relation to BioChemicalActivityStep**:

  * Devices are **prov\:used** in one or more `whu:BioChemicalActivityStep`s.
  * Example chain:
    `whu:BioChemicalActivityStep` → prov\:used → `whu:Device`.
* A single Device can be reused across multiple steps.

---

**Examples**

* **Positive Extraction**:

  * *“Samples were analyzed using an Agilent 7700 ICP-MS.”*
    → Device:

    * schema\:hasBrand = `"Agilent"`
    * schema\:hasModel = `"7700 ICP-MS"`
    * prov\:used by BioChemicalActivityStep = measurement

  * *“Microwave digestion was performed with a MARS 6 system (CEM Corporation).”*
    → Device:

    * schema\:hasBrand = `"CEM"`
    * schema\:hasModel = `"MARS 6 microwave digestion system"`
    * schema\:hasManufacturer = `"CEM Corporation"`
 
 

1.  **TOC Analyzer**
    *   **Description**: This is a laboratory instrument used for measuring the concentration of dissolved organic carbon (DOC).
    *   **Function**: It performs quantitative analysis of DOM concentration, expressed as DOC (mg/L).
    *   **Specifics**: The instrument used was a **Shimadzu TOC-L, Japan**.
    *   **Usage context**: It was utilized in the "DOM characterization" process within the Environmental Biogeochemistry Laboratory of Natural Organic Matter (NOM-Lab) at Southwest University (SWU).

2.  **Absorption-Fluorescence Spectrometer**
    *   **Description**: A scientific instrument for characterizing the optical properties of Dissolved Organic Matter (DOM).
    *   **Function**: It conducts fluorescence and UV-Vis measurements at a constant room temperature, scanning wavelengths and measuring excitation and emission spectra. It also has software for automatic removal of Raman and Rayleigh scattering during sample analysis.
    *   **Specifics**: The device was an **Aqualog® absorption-fluorescence spectrometer** manufactured by **Horiba, Japan**.
    *   **Usage context**: This device was employed during the "DOM characterization" phase in the NOM-Lab at SWU.

3.  **Cold Vapor Atomic Fluorescence Spectrometer (CVAAS) / GC-CVAFC**
    *   **Description**: An analytical instrument for determining total mercury (THg) and methylmercury (MeHg) content.
    *   **Function**: For THg, it uses cold vapor atomic fluorescence spectroscopy. For MeHg, it uses ethylated isothermal gas chromatography combined with cold atomic fluorescence (GC-CVAFC).
    *   **Specifics**: Two different models/manufacturers are mentioned for this type of analysis:
        *   **F-732 cold vapor atomic fluorescence spectroscopy (CVAAS)**, model **F732-S**, from **Shanghai Huaguang Instrument Co., Ltd., China**.
        *   **Brooks Rand model III, USA**, used for **GC-CVAFC**.
    *   **Usage context**: These instruments were crucial for the "Determination of THg and MeHg" in various samples, including soil, rice plants (roots, stalks, leaves, grains), and porewater. All measurements were conducted in the Mercury Biogeochemistry Laboratory (MBL) at SWU.
