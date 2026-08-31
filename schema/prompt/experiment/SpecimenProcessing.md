### **Define**

A **SpecimenProcessing** (`whu:SpecimenProcessing`) is a **planned processing procedure** (`p-plan:Plan`) composed of `whu:ActivityStep`.
It:

* Takes collected `whu:Specimen` as **input** (`p-plan:isInputVarOf`).
* Produces `whu:ProcessedSpecimen` as **output** (`p-plan:isOutputVarOf`).
* Prepares specimens for downstream `whu:BioChemicalActivityStep` (e.g., digestion, measurement).
* Is mapped to **OBI\:material\_processing** (`skos:closeMatch`).

---

### **Context**

Trigger `whu:SpecimenProcessing` when text describes:

* **Sample treatment** (air-drying, sieving, grinding, freeze-drying, filtering).
* **Pre-analytical handling** (storage, preservation, homogenization).
* **Devices/reagents** used in processing (sieves, ovens, filters, chemicals).
* **Outputs** that become inputs to a `whu:BioChemicalActivityStep`.

---

### **Examples**

* *“Soil samples were air-dried, ground, and passed through a 20-mesh nylon sieve before analysis.”*
  → `SpecimenProcessing`

  * prov\:used: Device(sieve), Specimen(raw soil)
  * prov\:generated: ProcessedSpecimen(sieved soil)
  * isInputVarOf: ProcessedSpecimen → BioChemicalActivityStep(digestion, ICP-MS)

* *“Rice grains were oven-dried at 60 °C, dehulled, and milled into flour.”*
  → `SpecimenProcessing`

  * prov\:used: Device(oven, mill), Specimen(rice grain)
  * prov\:generated: ProcessedSpecimen(rice flour)
  * isInputVarOf: ProcessedSpecimen → BioChemicalActivityStep(Hg measurement)

