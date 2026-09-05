# Transcript 04: Escalate Invoice Payment

**Situation:** Request to pay a contractor invoice.
**Planner Confidence:** 0.90
**Learned Policy (pay_invoice_external):** N=20, S=0.95

**Decider Lattice:**
- Policy Level: `AUTO` (S=0.90, N=20)
- Guard Floor: `ESCALATE` (financial transaction)
- Final Decision: `max(AUTO, ESCALATE) = ESCALATE`

**Result:** Even though the agent is highly confident and historically accurate, the hard floor forces an escalation due to financial safety rules.
