Config: {"agent_counts": [5, 20, 40], "densities": [0.0, 0.1, 0.2], "disruption_type": "mixed", "repetitions": 5, "seed": 0, "strategies": ["single_agent", "local"], "width": 20, "height": 14, "tasks_per_robot": 1, "block_duration_min": 6, "block_duration_max": 14, "targeted_fraction": 0.5, "n_breakdowns": 1, "n_emergencies": 1, "max_time": 500}

Total runs: 90, wall time 8 s

### Success rate (share of runs completing all tasks)
| N \ rho | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:100% B:100% | A:100% B:100% | A:80% B:80% |
| 20 | A:100% B:100% | A:100% B:100% | A:100% B:100% |
| 40 | A:80% B:80% | A:40% B:40% | A:0% B:100% |

### Flowtime vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:137±31<br>B:137±31 | A:179±42<br>B:178±40 | A:206±27<br>B:206±29 |
| 20 | A:495±23<br>B:495±23 | A:635±43<br>B:632±51 | A:700±13<br>B:701±18 |
| 40 | A:946±69<br>B:948±72 | A:1062±40<br>B:1060±43 | A:-<br>B:1303±76 |

### Modified agents vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:3.0±0.0<br>B:3.0±0.0 | A:5.0±0.0<br>B:5.0±0.0 | A:5.0±0.0<br>B:5.0±0.0 |
| 20 | A:2.8±0.4<br>B:2.8±0.4 | A:16.4±1.1<br>B:16.4±1.1 | A:19.0±1.0<br>B:19.0±1.0 |
| 40 | A:4.0±1.4<br>B:4.8±1.7 | A:20.0±4.2<br>B:20.0±4.2 | A:-<br>B:35.0±1.2 |

### Repair time (ms) vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:17±6<br>B:22±7 | A:54±33<br>B:55±28 | A:65±30<br>B:78±30 |
| 20 | A:19±1<br>B:27±5 | A:163±41<br>B:195±33 | A:304±173<br>B:388±273 |
| 40 | A:19±9<br>B:31±17 | A:160±34<br>B:148±6 | A:-<br>B:1273±248 |

### Messages vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:1.0±0.0<br>B:1.0±0.0 | A:1.8±0.8<br>B:3.2±2.9 | A:2.0±0.8<br>B:3.5±3.1 |
| 20 | A:1.2±0.4<br>B:1.2±0.4 | A:11.8±1.9<br>B:13.6±3.0 | A:14.2±4.9<br>B:20.2±7.9 |
| 40 | A:2.5±1.9<br>B:6.8±4.2 | A:16.5±7.8<br>B:16.5±7.8 | A:-<br>B:56.4±11.4 |

### Affected-set expansions per run vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.20±0.45 | A:0.00±0.00<br>B:0.25±0.50 |
| 20 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.20±0.45 | A:0.00±0.00<br>B:0.80±0.84 |
| 40 | A:0.00±0.00<br>B:0.75±0.50 | A:0.00±0.00<br>B:0.00±0.00 | A:-<br>B:1.60±0.55 |

### Largest |A_d| of any repair vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:1.0±0.0<br>B:1.0±0.0 | A:1.6±0.5<br>B:1.6±0.5 | A:2.0±0.8<br>B:2.2±1.0 |
| 20 | A:1.2±0.4<br>B:1.2±0.4 | A:4.2±0.8<br>B:4.2±0.8 | A:3.2±0.4<br>B:3.4±0.5 |
| 40 | A:2.5±1.9<br>B:2.5±1.7 | A:4.0±1.4<br>B:4.0±1.4 | A:-<br>B:6.8±1.3 |

### Modified ratio vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0.60±0.00<br>B:0.60±0.00 | A:1.00±0.00<br>B:1.00±0.00 | A:1.00±0.00<br>B:1.00±0.00 |
| 20 | A:0.14±0.02<br>B:0.14±0.02 | A:0.82±0.06<br>B:0.82±0.06 | A:0.95±0.05<br>B:0.95±0.05 |
| 40 | A:0.10±0.04<br>B:0.12±0.04 | A:0.50±0.11<br>B:0.50±0.11 | A:-<br>B:0.88±0.03 |

### Failure reasons
| strategy | failure reason | runs |
|---|---|---|
| B local negotiated | no feasible route even if neighbours yield / group unsolvable | 5 |
| A single-agent | conflict with an unchanged plan (negotiation disabled) | 10 |


### Paired comparison, B (local) vs A (single-agent)
- pairs: 35
- mean_modified_local: 8.857
- mean_modified_single_agent: 8.771
- mean_flowtime_local: 498.571
- mean_flowtime_single_agent: 498.914
- mean_repair_ms_local: 119.230
- mean_repair_ms_single_agent: 98.291
- local_modifies_fewer_or_equal: 0.914
- single_agent_lower_flowtime: 0.171
