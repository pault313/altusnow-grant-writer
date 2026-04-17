# AI Grant Writer -- Product Opportunity Brief

**To:** Ashleigh Walters, CEO
**From:** Paul Trahan, CFO
**Date:** April 10, 2026
**Re:** Grant Writing AI Tool -- Internal Use + SaaS Revenue Opportunity

---

## What We Built

We have a working prototype of an AI-powered grant writing tool that takes a federal RFP (PDF), combines it with our Engage Together VPI data, and produces a complete grant application draft -- including needs statement, program design, budget narrative, compliance checklist, and quality scorecard.

**Test run results (real OVC solicitation, OVC-2025-172523):**
- Input: 34-page RFP + Alabama VPI data
- Output: Complete application draft with detailed budget, goals/objectives, and capabilities section
- Cost: $3.00 in API fees
- Time: 28 minutes (fully automated, no human input after upload)
- The tool correctly positioned Engage Together, Justice U, and JIT throughout the application

The draft needs human review and polish -- language cleanup, fact verification, length trimming -- but it gets a grant writer from blank page to 80% done in under 30 minutes for $3.

---

## Why This Matters for Altus

### Immediate Value (Now)
Altus writes grants to fund its own programs and deployments. This tool cuts the time from weeks to hours per application, freeing staff to focus on relationships and program delivery instead of narrative writing.

### Revenue Opportunity (6-12 Months)
No grant writing tool exists for the anti-trafficking, SDOH, or social justice sector. The generic tools (Instrumentl, GrantScout) help organizations *find* grants -- none of them *write* applications with sector-specific compliance, trauma-informed language, or evidence-based needs statements. Three independent market analyses confirmed this gap in a $3B+ market growing 8-10% annually.

Our competitive moat is the VPI data. A needs statement backed by county-level vulnerability analysis across 37 indicators from 14 validated data sources is dramatically stronger than the anecdotal narratives most organizations submit.

---

## Product Strategy: Three Tiers

The key question is how external customers use the tool when they don't have their own VPI data. The answer creates a natural upsell path to Engage Together:

| Tier | What They Get | Price | Target Customer |
|------|--------------|-------|-----------------|
| **Starter** | Grant writer + customer uploads their own data | $99/mo | Small nonprofits, local coalitions |
| **Professional** | Grant writer + auto-generated public data for their state (ACS, FBI UCR, HUD, etc.) | $299/mo | Regional coalitions, mid-size nonprofits |
| **Enterprise** | Grant writer + full Engage Together VPI assessment | $799/mo | State agencies, large task forces |

**The grant writer becomes the wedge product that sells Engage Together.** Customers start at Starter because they need to write grants faster. They see how much stronger a data-driven needs statement is. They upgrade to Professional for automated public data. They win grants. They use that funding to buy a full Engage Together assessment at Enterprise tier.

---

## Revenue Projection (Conservative, Year 1 of SaaS Launch)

| Tier | Customers | Monthly Revenue | Annual Revenue |
|------|-----------|----------------|----------------|
| Starter | 50 | $4,950 | $59,400 |
| Professional | 30 | $8,970 | $107,640 |
| Enterprise | 10 | $7,990 | $95,880 |
| **Total** | **90** | **$21,910** | **$262,920** |

Enterprise customers would also purchase Engage Together assessments separately ($15-25K per state), adding $150-250K in consulting revenue on top of SaaS subscriptions.

API costs run $5-15 per grant application. At average usage of 3-5 applications per customer per month, gross margins are 85-90%.

---

## Investment Required

| Phase | Cost | Timeline | Outcome |
|-------|------|----------|---------|
| **Phase 1** (done) | ~$3K (staff time + API costs) | Complete | Working internal tool |
| **Phase 2** | $15-30K | 8-12 weeks | Multi-agent AI, organizational memory, FastAPI backend, pilot with 2-3 partners |
| **Phase 3** | $40-80K | 12-18 months | Full SaaS platform (Next.js, Supabase, Stripe billing, multi-tenant) |

Phase 2 can be funded from existing budget. Phase 3 investment can be partially offset by early Enterprise customers paying for Engage Together assessments.

---

## What I Need From You

1. **Green light to use the tool internally** for upcoming grant applications (zero additional cost beyond the ~$3-15 per run in API fees we're already set up for)

2. **Directional approval on the SaaS path** -- should we build Phase 2 with the intent to offer this externally, or keep it internal-only for now?

3. **Two or three coalition/task force partners** you'd want to pilot with during Phase 2 -- organizations in our network who write grants regularly and would give us honest feedback

---

*A working demo is available anytime you'd like to see it.*
