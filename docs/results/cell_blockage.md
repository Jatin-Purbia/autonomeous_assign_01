Config: {"agent_counts": [5, 20, 40], "densities": [0.0, 0.1, 0.2], "disruption_type": "cell_blockage", "repetitions": 5, "seed": 0, "strategies": ["single_agent", "local"], "width": 20, "height": 14, "tasks_per_robot": 1, "block_duration_min": 6, "block_duration_max": 14, "targeted_fraction": 0.5, "n_breakdowns": 1, "n_emergencies": 1, "max_time": 500}

Total runs: 90, wall time 5 s

### Success rate (share of runs completing all tasks)
| N \ rho | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:100% B:100% | A:100% B:100% | A:100% B:100% |
| 20 | A:100% B:100% | A:100% B:100% | A:100% B:100% |
| 40 | A:100% B:100% | A:80% B:100% | A:20% B:100% |

### Flowtime vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:106±28<br>B:106±28 | A:163±37<br>B:163±37 | A:184±35<br>B:184±35 |
| 20 | A:472±18<br>B:472±18 | A:589±16<br>B:584±17 | A:693±64<br>B:687±66 |
| 40 | A:931±67<br>B:931±67 | A:1120±79<br>B:1132±74 | A:1272±0<br>B:1262±81 |

### Modified agents vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0.0±0.0<br>B:0.0±0.0 | A:4.4±0.5<br>B:4.4±0.5 | A:5.0±0.0<br>B:5.0±0.0 |
| 20 | A:0.0±0.0<br>B:0.0±0.0 | A:13.0±2.0<br>B:13.0±2.0 | A:17.8±1.3<br>B:17.8±1.3 |
| 40 | A:0.0±0.0<br>B:0.0±0.0 | A:25.2±3.0<br>B:25.4±2.6 | A:31.0±0.0<br>B:32.2±3.9 |

### Repair time (ms) vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0±0<br>B:0±0 | A:10±5<br>B:11±6 | A:21±2<br>B:19±3 |
| 20 | A:0±0<br>B:0±0 | A:108±65<br>B:123±71 | A:185±85<br>B:196±88 |
| 40 | A:0±0<br>B:0±0 | A:338±205<br>B:357±229 | A:420±0<br>B:397±180 |

### Messages vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0.0±0.0<br>B:0.0±0.0 | A:0.2±0.4<br>B:0.2±0.4 | A:1.2±1.3<br>B:1.2±1.3 |
| 20 | A:0.0±0.0<br>B:0.0±0.0 | A:7.6±4.2<br>B:7.4±3.8 | A:14.2±3.3<br>B:14.4±3.5 |
| 40 | A:0.0±0.0<br>B:0.0±0.0 | A:23.2±6.9<br>B:23.2±6.0 | A:35.0±0.0<br>B:52.2±10.1 |

### Affected-set expansions per run vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.00±0.00 |
| 20 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.00±0.00 |
| 40 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.20±0.45 | A:0.00±0.00<br>B:2.20±1.79 |

### Largest |A_d| of any repair vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0.0±0.0<br>B:0.0±0.0 | A:1.2±0.4<br>B:1.2±0.4 | A:1.6±0.5<br>B:1.6±0.5 |
| 20 | A:0.0±0.0<br>B:0.0±0.0 | A:3.0±0.7<br>B:3.0±0.7 | A:3.8±0.8<br>B:3.8±0.8 |
| 40 | A:0.0±0.0<br>B:0.0±0.0 | A:6.5±0.6<br>B:6.6±0.5 | A:5.0±0.0<br>B:5.2±0.4 |

### Modified ratio vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0.00±0.00<br>B:0.00±0.00 | A:0.88±0.11<br>B:0.88±0.11 | A:1.00±0.00<br>B:1.00±0.00 |
| 20 | A:0.00±0.00<br>B:0.00±0.00 | A:0.65±0.10<br>B:0.65±0.10 | A:0.89±0.07<br>B:0.89±0.07 |
| 40 | A:0.00±0.00<br>B:0.00±0.00 | A:0.63±0.07<br>B:0.64±0.07 | A:0.78±0.00<br>B:0.81±0.10 |

### Failure reasons
| strategy | failure reason | runs |
|---|---|---|
| A single-agent | conflict with an unchanged plan (negotiation disabled) | 5 |


### Paired comparison, B (local) vs A (single-agent)
- pairs: 40
- mean_modified_local: 8.325
- mean_modified_single_agent: 8.325
- mean_flowtime_local: 535.275
- mean_flowtime_single_agent: 536.075
- mean_repair_ms_local: 95.257
- mean_repair_ms_single_agent: 84.817
- local_modifies_fewer_or_equal: 1.000
- single_agent_lower_flowtime: 0.025
