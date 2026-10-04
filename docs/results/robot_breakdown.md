Config: {"agent_counts": [5, 20, 40], "densities": [0.0, 0.1, 0.2], "disruption_type": "robot_breakdown", "repetitions": 5, "seed": 0, "strategies": ["single_agent", "local"], "width": 20, "height": 14, "tasks_per_robot": 1, "block_duration_min": 6, "block_duration_max": 14, "targeted_fraction": 0.5, "n_breakdowns": 1, "n_emergencies": 1, "max_time": 500}

Total runs: 90, wall time 5 s

### Success rate (share of runs completing all tasks)
| N \ rho | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:100% B:100% | A:100% B:100% | A:100% B:100% |
| 20 | A:100% B:100% | A:100% B:100% | A:100% B:100% |
| 40 | A:100% B:100% | A:80% B:100% | A:60% B:80% |

### Flowtime vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:116±27<br>B:116±27 | A:151±33<br>B:151±33 | A:181±22<br>B:181±22 |
| 20 | A:482±23<br>B:482±23 | A:603±28<br>B:603±28 | A:680±46<br>B:681±46 |
| 40 | A:952±56<br>B:952±56 | A:1140±27<br>B:1121±51 | A:1271±16<br>B:1258±31 |

### Modified agents vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:2.2±0.4<br>B:2.2±0.4 | A:4.6±0.9<br>B:4.6±0.9 | A:5.0±0.0<br>B:5.0±0.0 |
| 20 | A:2.4±0.5<br>B:2.4±0.5 | A:14.4±2.3<br>B:14.4±2.3 | A:18.6±0.5<br>B:18.6±0.5 |
| 40 | A:4.8±2.8<br>B:4.8±2.8 | A:24.8±2.6<br>B:25.6±3.0 | A:31.7±3.8<br>B:31.8±3.1 |

### Repair time (ms) vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:4±2<br>B:4±1 | A:11±3<br>B:11±3 | A:24±5<br>B:24±6 |
| 20 | A:6±2<br>B:5±2 | A:118±59<br>B:119±55 | A:213±90<br>B:213±97 |
| 40 | A:20±27<br>B:19±24 | A:225±93<br>B:226±88 | A:576±209<br>B:628±226 |

### Messages vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0.2±0.4<br>B:0.2±0.4 | A:0.2±0.4<br>B:0.2±0.4 | A:0.6±0.9<br>B:0.6±0.9 |
| 20 | A:0.4±0.5<br>B:0.4±0.5 | A:9.2±3.8<br>B:9.2±3.8 | A:13.0±3.8<br>B:13.6±3.8 |
| 40 | A:2.8±2.8<br>B:2.8±2.8 | A:21.5±1.7<br>B:22.6±3.8 | A:44.3±8.1<br>B:46.8±7.9 |

### Affected-set expansions per run vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.00±0.00 |
| 20 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.00±0.00 |
| 40 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.20±0.45 | A:0.00±0.00<br>B:0.25±0.50 |

### Largest |A_d| of any repair vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:1.2±0.4<br>B:1.2±0.4 | A:1.2±0.4<br>B:1.2±0.4 | A:1.4±0.5<br>B:1.4±0.5 |
| 20 | A:1.4±0.5<br>B:1.4±0.5 | A:3.8±0.4<br>B:3.8±0.4 | A:3.6±0.5<br>B:3.6±0.5 |
| 40 | A:3.8±2.8<br>B:3.8±2.8 | A:5.2±0.5<br>B:5.4±0.5 | A:5.0±1.0<br>B:5.5±1.3 |

### Modified ratio vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0.44±0.09<br>B:0.44±0.09 | A:0.92±0.18<br>B:0.92±0.18 | A:1.00±0.00<br>B:1.00±0.00 |
| 20 | A:0.12±0.03<br>B:0.12±0.03 | A:0.72±0.12<br>B:0.72±0.12 | A:0.93±0.03<br>B:0.93±0.03 |
| 40 | A:0.12±0.07<br>B:0.12±0.07 | A:0.62±0.07<br>B:0.64±0.07 | A:0.79±0.09<br>B:0.79±0.08 |

### Failure reasons
| strategy | failure reason | runs |
|---|---|---|
| B local negotiated | no feasible route even if neighbours yield / group unsolvable | 1 |
| A single-agent | conflict with an unchanged plan (negotiation disabled) | 3 |


### Paired comparison, B (local) vs A (single-agent)
- pairs: 42
- mean_modified_local: 10.810
- mean_modified_single_agent: 10.810
- mean_flowtime_local: 575.048
- mean_flowtime_single_agent: 576.214
- mean_repair_ms_local: 113.590
- mean_repair_ms_single_agent: 109.621
- local_modifies_fewer_or_equal: 1.000
- single_agent_lower_flowtime: 0.071
