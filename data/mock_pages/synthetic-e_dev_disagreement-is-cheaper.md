# Disagreement is cheaper than labels
Short technical post. Argues that a single model's confidence score is unreliable on
out-of-distribution inputs, so the usual "escalate when confidence < X" breaks
exactly when you need it. The insight: run two weak models and use their DISAGREEMENT
as the routing signal instead — it sidesteps the calibration problem and needs no
labels. Walks through the self-calibrating threshold (tracks the rolling disagreement
rate) and shows the cost/accuracy audit. Explicit about limits: correlated errors
(both weak models wrong the same way) are invisible to the method, so it pairs the
router with a small random-sample human audit to catch that. Reasoning is original
and the constraint (no labels, no budget) is what forced the clever solution.
