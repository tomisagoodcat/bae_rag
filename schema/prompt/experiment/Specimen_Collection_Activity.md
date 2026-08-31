 
### **Define**

A **Speciemen Collection Activity ** (`whu:Specimen_Collection_Activity`) is the **minimal semantic unit** of specimen acquisition, representing a **concrete act of obtaining material samples** from an environment, organism, or substrate.
It:

* Declares a `whu:Method` describing the collection technique (e.g., grab sampling, coring, harvesting).
* The speciemen collection activty happened at(prov:atLocation) **whu:EnvirmenFeature**
* The sepcimen collection activity use(prov:used) **envo:Material** and get the **whu:ProcessedSpeciemen** 
* Generates **outputs**: one or more `whu:Processedspecimen` objects (`prov:generated`).
* Is always part of a  **whu:SpecimenCollection** (`whu:hasActivitry`	).
* Establishes provenance by linking to subsequent another SpecimenProcessingActivity(`prov:wasInformedBy`  ).

---

### **Context**

Extract a `Speciemen Collection Activity` whenever the text describes an **explicit sampling action**, such as:

* Field sampling (e.g., collecting soil, water, or rice grains).
* Instrument-mediated sampling (e.g., coring device, dredge, sampler).
* Biological collection (e.g., leaf clipping, grain harvesting, blood draw).

Each step should be:

1. **Atomic**: capture the smallest identifiable collection act (not the whole field campaign).
2. **Traceable**:

   * `prov:atLocation` → environment/location.
   * `prov:generated` → processedspecimen(s).
   * `prov:wasInformedBy` → links the specimen forward to processing, biochemical, or computational activities.
3. **Ontology-aligned**:

   * CloseMatch with **OBI\:specimen\_collection\_process**.
   * Conforms to general definitions in BFO (processual entity) and Wikipedia "Sample collection".

---

### **Notes**

* A `Speciemen Collection Activity  differs from:

  * `whu:SpecimenProcessingActivity`: transformation after collection (e.g., drying, grinding).
  * `whu:BioChemicalActivityStep`: laboratory analysis of processed specimens.
  * `whu:ComputationalActivityStep`: digital transformation/analysis of data.
* Relations to ensure:

  * `prov:used` → envo:Material.
   * `prov:atLocation` → whu:EnviormentFeature
  * `prov:generated` → whu:ProcessedSpecimen.
 *  whu:SpecemenCollection→ `whu:Specimen_Collection_Activity`
  * `prov:wasInformedBy` → Specimen_Collection_Activity

---

### **Examples**

* “Soil samples were collected from the plough layer (0–20 cm) in Nanjing paddy fields.”
  → `CollectionActivityStep`

  * prov\:used: EnvironmentFeature(paddy field, 0–20 cm depth)
  * prov\:generated: Specimen(soil sample)
  * wasInformedBy: SpecimenProcessingActivity(air-drying, sieving)

* “Rice grains were harvested at maturity.”
  → `CollectionActivityStep`

  * prov\:used: TargetObject(rice plants at maturity)
  * prov\:generated: Specimen(rice grains)
  * wasInformedBy: BioChemicalActivityStep(measurement of Hg concentration)

* “Surface water was sampled using a Van Dorn sampler.”
  → `CollectionActivityStep`

  * prov\:used: EnvironmentFeature(surface water body)
  * prov\:generated: Specimen(water sample)
  * wasInformedBy: BioChemicalActivityStep(ICP-MS measurement of heavy metals)

 