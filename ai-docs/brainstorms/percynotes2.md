# notes:

0. load the new data and all the data
1. we need to make a Fundamental Tensor Primitive spec so that the simulation and the hexagons are pulling data from the primitive, and the primitive pulls from SQLite. The hexagons DO NOT touch the database. ONLY the primitive tensor, its derivative tensors, its calculated values, and the magic constants populate the hexagons. TPRF and the tensors are measured in labor-hours, NOT in monetary wages. Monetary wages are calculated from labor hours according to the transformation problem which will be implemented in future specifications. The intention is that the Fundamental Tensor Primitive will become the fundamental unit from which all other economic data - including wages - is derived since Marxist theory revolves around labor hours and not monetary values and wages.
2. we need to make a TPRF spec
3. we need to derive the tensors from the primitive tensor (volume 2 and 3)
4. we need the hexagons on the map to scale out
5. we need to implement the network topology on the map
6. we need to validate against ai-docs/ epoch 1 and epoch 2
7. we need to update the documentation in docs/
8. we need to update ai-docs/
