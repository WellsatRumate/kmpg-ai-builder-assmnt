# rota-engine
Constraint-based scheduler for shift workers. Handles 200+ workers. Has an
uncertainty threshold: when the solver confidence is low it escalates to a human
rather than guessing. 14 months of commit history. A separate `rota-constraints`
package was extracted and is imported by two other depots' forks. Tests cover the
escalation path. README is plain but the code is real and documented.
