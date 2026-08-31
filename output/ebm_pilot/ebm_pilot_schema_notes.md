# EBM Pilot schema notes

- Chunk properties observed: `EBM_num`, `EEM_num`, `MPU_num`, `dc_author`, `dc_creator`, `dc_publisher`, `dc_title`, `dcterms_identifier`, `dcterms_issued`, `embedding`, `filename`, `from_section`, `header_path`, `index`, `processed_at`, `section_role`, `source_doc`, `text`
- Chunk EBM stats: `{'chunks': 195, 'ebm_null': 0, 'ebm_pos': 39, 'ebm_min': 0, 'ebm_max': 110}`
- DoCO type column = `Chunk.from_section` (exported as `doco_type`).
- Entity `subgraph` property is generally absent; EBM membership = label in `output/subgraph_mapping.json` mappings.EBM.
- Relation inclusion: both endpoints have ≥1 EBM-mapped domain label (allows shared participants also in EEM/MPU).
