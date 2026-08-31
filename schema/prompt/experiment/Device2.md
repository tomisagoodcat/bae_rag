**Define**  
A **Device** (`whu:Device`) is a **scientific/analytical instrument** used in experiments, especially `whu:BioChemicalActivityStep`s.  
Following **OBI**, a device is a **manufactured object** enabling measurement, detection, transformation, or processing of specimens.  

Examples:  
- Lab instruments: ICP-MS, HPLC, GC-MS, UV-Vis.  
- Processing tools: centrifuge, microwave digestion system.  
- Measurement tools: balance, sensor, pH meter.  

---

**Context**  
Extract `whu:Device` when text explicitly names an instrument, tool, or equipment in research.  
Devices connect to:  
- `whu:BioChemicalActivityStep` → `prov:used`.  
- Occasionally `whu:ComputationalActivityStep` (e.g., GPU cluster).  
Capture **brand, model, manufacturer, serial number** if given.  
Treat mentions with full metadata (brand+model+SN) as unique entities; otherwise group by model.  

---

**Notes**  
- A device is always linked via `prov:used` in one or more activity steps.  
- Chain example:  
  `BioChemicalActivityStep → prov:used → Device`.  
- A device may be reused across steps.  

---

**Examples**  

- *“Samples were analyzed using an Agilent 7700 ICP-MS.”*  
  → Device:  
  - schema:hasBrand = `"Agilent"`  
  - schema:hasModel = `"7700 ICP-MS"`  
  - prov:used by measurement step  

- *“Microwave digestion was performed with a MARS 6 (CEM Corporation).”*  
  → Device:  
  - schema:hasBrand = `"CEM"`  
  - schema:hasModel = `"MARS 6 microwave digestion system"`  
  - schema:hasManufacturer = `"CEM Corporation"`  

1. **TOC Analyzer**  
   - Shimadzu TOC-L (Japan); used to measure DOC (mg/L) in DOM characterization at SWU NOM-Lab.  

2. **Absorption-Fluorescence Spectrometer**  
   - Aqualog® (Horiba, Japan); used for DOM optical property measurement.  

3. **Cold Vapor Atomic Fluorescence Spectrometer / GC-CVAFC**  
   - F-732 CVAAS (Shanghai Huaguang, China).  
   - Brooks Rand Model III (USA) for GC-CVAFC.  
   - Applied in THg/MeHg analysis at SWU Mercury Biogeochemistry Lab.  
