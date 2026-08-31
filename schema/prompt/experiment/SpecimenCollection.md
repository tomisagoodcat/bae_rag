### **Define**

A **SpecimenCollection** (`whu:SpecimenCollection`) is a **planned sampling process** (`p-plan:Plan`) composed of one or more `whu:ActivityStep`.
It:

* Collects raw material from an **environmental context** (soil, water, plant, air, food).
* Produces `whu:Specimen` as **output** (`p-plan:isOutputVarOf`).
* Provides input specimens for later `whu:BioChemicalActivityStep` (`p-plan:isInputVarOf`).
* Is semantically mapped to **OBI\:specimen\_collection\_process** (`skos:closeMatch`).

### **Context**

Trigger `whu:SpecimenCollection` when text describes:

* **Where/when** sampling occurs.
* **Design/method** (random, stratified, depth, time interval).
* **Tools/devices** used (auger, trap, pump, containers).
* Number, type, or treatment of samples before analysis.
* Implicit link: collected **Specimen** later consumed by a `whu:BioChemicalActivityStep`.

### **Examples**

* *“We randomly collected 60 rice grain samples from 10 districts of Hubei Province during 2022–2023.”*
  → `SpecimenCollection`

  * prov\:used: Device(sample bags, GPS locator)
  * prov\:generated: Specimen(rice grains)
  * isOutputVarOf: Specimen → BioChemicalActivityStep(digestion, ICP-MS)

* *“Topsoil (0–20 cm) was sampled from paddy fields using a stainless-steel auger, air-dried, and stored for further analysis.”*
  → `SpecimenCollection`

  * prov\:used: Device(soil auger)
  * prov\:generated: Specimen(soil samples)
  * isInputVarOf: Specimen → BioChemicalActivityStep(metal extraction, ICP-OES)

