# confidence-cascade
A tiny routing primitive (~200 lines). Two cheap models score each item; agreement
is accepted, disagreement escalates that single item to a strong model. The
escalation threshold self-calibrates from the rolling disagreement rate, so it needs
no labelled data to stay tuned as the input distribution drifts. Ships with an audit
notebook showing ~80% model-cost reduction at parity accuracy vs always-strong-model
on 3,000 sampled support tickets. README links two other repos that adopted it. ~600
commits with real issues and PRs from outside contributors. The core idea —
"disagreement between two weak models is a cheaper routing signal than a single
model's confidence score" — is genuinely not the obvious design, and the README is
candid about the failure mode where both weak models err the same way.
