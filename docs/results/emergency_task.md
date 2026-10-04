Config: {"agent_counts": [5, 20, 40], "densities": [0.0, 0.1, 0.2], "disruption_type": "emergency_task", "repetitions": 5, "seed": 0, "strategies": ["single_agent", "local"], "width": 20, "height": 14, "tasks_per_robot": 1, "block_duration_min": 6, "block_duration_max": 14, "targeted_fraction": 0.5, "n_breakdowns": 1, "n_emergencies": 1, "max_time": 500}

Total runs: 90, wall time 7 s

### Success rate (share of runs completing all tasks)
| N \ rho | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:100% B:100% | A:100% B:100% | A:100% B:100% |
| 20 | A:100% B:100% | A:100% B:100% | A:100% B:100% |
| 40 | A:100% B:100% | A:80% B:100% | A:40% B:100% |

### Flowtime vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:125±27<br>B:125±27 | A:181±17<br>B:176±14 | A:207±35<br>B:197±32 |
| 20 | A:491±20<br>B:491±20 | A:618±59<br>B:614±54 | A:677±23<br>B:672±16 |
| 40 | A:949±68<br>B:949±69 | A:1114±85<br>B:1116±78 | A:1272±76<br>B:1253±63 |

### Modified agents vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:1.0±0.0<br>B:1.0±0.0 | A:4.8±0.4<br>B:4.8±0.4 | A:5.0±0.0<br>B:5.0±0.0 |
| 20 | A:1.0±0.0<br>B:1.0±0.0 | A:15.2±1.9<br>B:15.2±1.9 | A:18.4±0.9<br>B:18.4±0.9 |
| 40 | A:1.0±0.0<br>B:1.4±0.5 | A:24.5±2.1<br>B:24.4±1.8 | A:30.5±0.7<br>B:31.0±1.2 |

### Repair time (ms) vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:6±1<br>B:9±2 | A:17±1<br>B:23±2 | A:29±3<br>B:36±9 |
| 20 | A:7±1<br>B:11±2 | A:141±121<br>B:122±77 | A:254±233<br>B:302±294 |
| 40 | A:12±6<br>B:25±22 | A:316±208<br>B:456±293 | A:599±324<br>B:634±214 |

### Messages vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:1.0±0.0<br>B:1.0±0.0 | A:1.4±0.5<br>B:1.4±0.5 | A:2.4±0.9<br>B:3.4±3.2 |
| 20 | A:1.0±0.0<br>B:1.0±0.0 | A:10.8±2.7<br>B:12.8±6.6 | A:13.8±4.5<br>B:18.8±7.3 |
| 40 | A:1.0±0.0<br>B:3.4±3.3 | A:20.5±3.4<br>B:27.0±6.4 | A:33.5±14.8<br>B:43.8±11.2 |

### Affected-set expansions per run vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.20±0.45 |
| 20 | A:0.00±0.00<br>B:0.00±0.00 | A:0.00±0.00<br>B:0.20±0.45 | A:0.00±0.00<br>B:0.80±0.84 |
| 40 | A:0.00±0.00<br>B:0.40±0.55 | A:0.00±0.00<br>B:0.80±0.84 | A:0.00±0.00<br>B:0.80±1.30 |

### Largest |A_d| of any repair vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:1.0±0.0<br>B:1.0±0.0 | A:1.4±0.5<br>B:1.4±0.5 | A:1.8±0.4<br>B:1.8±0.4 |
| 20 | A:1.0±0.0<br>B:1.0±0.0 | A:3.2±0.4<br>B:3.2±0.4 | A:3.4±0.5<br>B:3.6±0.5 |
| 40 | A:1.0±0.0<br>B:1.4±0.5 | A:5.2±0.5<br>B:5.4±0.5 | A:6.5±2.1<br>B:6.4±1.1 |

### Modified ratio vs agent count (rows) and density (columns); mean±std over successful runs
| n_agents \ density | 0.0 | 0.1 | 0.2 |
|---|---|---|---|
| 5 | A:0.20±0.00<br>B:0.20±0.00 | A:0.96±0.09<br>B:0.96±0.09 | A:1.00±0.00<br>B:1.00±0.00 |
| 20 | A:0.05±0.00<br>B:0.05±0.00 | A:0.76±0.10<br>B:0.76±0.10 | A:0.92±0.04<br>B:0.92±0.04 |
| 40 | A:0.03±0.00<br>B:0.04±0.01 | A:0.61±0.05<br>B:0.61±0.05 | A:0.76±0.02<br>B:0.78±0.03 |

### Failure reasons
| strategy | failure reason | runs |
|---|---|---|
| A single-agent | conflict with an unchanged plan (negotiation disabled) | 4 |


### Paired comparison, B (local) vs A (single-agent)
- pairs: 41
- mean_modified_local: 9.585
- mean_modified_single_agent: 9.537
- mean_flowtime_local: 562.000
- mean_flowtime_single_agent: 566.756
- mean_repair_ms_local: 127.987
- mean_repair_ms_single_agent: 116.896
- local_modifies_fewer_or_equal: 0.951
- single_agent_lower_flowtime: 0.049
