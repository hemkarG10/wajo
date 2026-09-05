# Transcript 01: Auto Newsletter

**Situation:** Newsletter from known sender.
**Planner Confidence:** 0.95
**Learned Policy (archive_newsletter_newsletter):** N=50, S=0.98

**Decider Lattice:**
- Policy Level: `AUTO` (S=0.95, N=50)
- Guard Floor: `AUTO` (read-only action)
- Final Decision: `max(AUTO, AUTO) = AUTO`

**Result:** The email is archived silently.
