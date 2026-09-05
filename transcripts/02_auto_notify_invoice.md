# Transcript 02: Auto-Notify Invoice

**Situation:** Internal invoice forward.
**Planner Confidence:** 0.85
**Learned Policy (forward_internal_invoice):** N=12, S=0.88

**Decider Lattice:**
- Policy Level: `AUTO_NOTIFY` (S=0.85, N=12)
- Guard Floor: `AUTO_NOTIFY` (internal send)
- Final Decision: `max(AUTO_NOTIFY, AUTO_NOTIFY) = AUTO_NOTIFY`

**Result:** Invoice forwarded, user receives a notification with an undo button.
