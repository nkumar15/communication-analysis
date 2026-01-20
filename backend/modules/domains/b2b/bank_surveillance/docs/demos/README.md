# Demo Scripts

## Overview

These demo scripts are designed for different audiences and time constraints. Each script includes both a **narrative version** (for presenter notes) and a **step-by-step guide** (for self-guided demos).

---

## Demo 1: Executive Demo (5 minutes)

**Target Persona:** Sarah Chen (Head of Compliance)  
**Goal:** Prove platform is enterprise-ready, not a prototype  
**Key Message:** "This is how you'll present to regulators"

### Narrative Script

---

> **[OPEN: Dashboard]**
> 
> "Good morning. Let me show you how your team starts every day.
> 
> This dashboard gives you immediate visibility into your organization's risk posture. Notice we're showing alerts by region – you can see APAC had 12 high-priority items overnight.
> 
> **[Point to risk theme widget]**
> But what makes this different from a simple alerting system is here – *Emerging Risk Themes*. Our AI is continuously analyzing communication patterns and surfacing themes before they become problems.
> 
> **[Using sample surveillance data]**
> For example, with our predictive models, watch this: Weeks before a potential conduct event, you'd have seen 'Risk spike detected – 47% increase in secrecy-coded language.' That's the lead time you need.
> 
> **[NAVIGATE: Cases]**
> Let's look at how investigations conclude. This case – 'Pre-earnings information leakage' – was opened, investigated, and closed with full documentation. 
> 
> **[Click into case detail]**
> Notice we require a decision rationale at closure. This isn't optional – your regulators will ask for this.
> 
> **[NAVIGATE: Audit & Reports]**
> And when they do ask, here's where you generate the evidence. Every action is logged. Every search is recorded. Every case decision is preserved.
> 
> **[Click export]**
> One click – PDF for the board, or structured JSON for your internal audit team.
> 
> **[Close]**
> This is what audit-readiness looks like. Questions?"

---

### Step-by-Step Guide

| Step | Action | Talking Point |
|------|--------|---------------|
| 1 | Open Dashboard | "Daily risk overview for compliance leadership" |
| 2 | Point to Alerts widget | "12 high-priority alerts in APAC overnight" |
| 3 | Highlight Emerging Themes | "AI-detected patterns surfacing early" |
| 4 | Click region selector | "Regional view is critical for global firms" |
| 5 | Navigate to Cases | "Let's see how investigations conclude" |
| 6 | Open closed case | "Full lifecycle with required documentation" |
| 7 | Show decision rationale | "Regulator-ready evidence" |
| 8 | Navigate to Audit | "Complete audit trail" |
| 9 | Click Export | "One-click regulatory reporting" |
| 10 | End on dashboard | "This is audit-readiness. Questions?" |

---

## Demo 2: Analyst Demo (10 minutes)

**Target Persona:** Marcus Johnson (Surveillance Analyst)  
**Goal:** Show the daily workflow and AI assistance  
**Key Message:** "This is how you'll work, not how you'll learn another tool"

### Narrative Script

---

> **[OPEN: Alerts page]**
> 
> "This is your home. Every morning, you come here and see your assigned alerts. Let me show you a typical workflow.
> 
> **[Apply filter: High confidence, Last 24 hours]**
> First, I filter to focus on what matters – high confidence alerts from the last 24 hours. I've got 8 items.
> 
> **[Click top alert]**
> Let's look at this one: 'Potential earnings leakage – High confidence.'
> 
> **[NAVIGATE: Alert Detail]**
> Now watch – the system doesn't just flag the email. It tells me *why*.
> 
> **[Point to 'Why This Triggered']**
> 'Pattern match: forward-looking financial information shared outside approved channels.' The AI isn't a black box. I can validate its reasoning.
> 
> **[Point to highlighted text]**
> And look – it's highlighted exactly the phrases that triggered the alert in context. I don't have to hunt through a 50-email thread.
> 
> **[Show similar historical alerts]**
> Here's something powerful – similar historical alerts. This pattern happened 3 times before, all from the same department. That's a systemic issue, not a one-off.
> 
> **[Click 'Open Investigation']**
> 
> **[NAVIGATE: Investigation Workspace]**
> Now I'm in the investigation workspace. Three panels:
> - Left: The conversation timeline – every email in chronological order
> - Center: The email I'm reading
> - Right: AI insights
> 
> **[Point to AI Summary]**
> Look at this summary. I didn't write this – the AI synthesized a 23-email thread into 3 sentences. That's time saved.
> 
> **[Point to Risk Evolution]**
> And *this* is my favorite feature – risk evolution. Watch how the risk signals change over time in this thread. Normal... normal... then suddenly in week 3, the language shifts. That's where the problem started.
> 
> **[Point to Suggested Next Steps]**
> The AI even suggests what to do next: 'Consider interviewing department head' or 'Check for similar patterns in adjacent teams.'
> 
> **[Use Search & RAG]**
> Let me quickly check for related patterns.
> 
> **[NAVIGATE: Search & RAG]**
> 'Show communications mentioning quarterly earnings from this sender in the past 90 days.'
> 
> **[Show results]**
> 5 more conversations. This person has a pattern. Now I have enough for a case.
> 
> **[Navigate back to Investigation]**
> **[Click 'Create Case']**
> 
> **[NAVIGATE: Case detail]**
> Case created. I add my notes, attach the evidence, and assign priority.
> 
> **[Show bulk close]**
> **[NAVIGATE: Alerts]**
> And for the remaining low-risk items? Bulk select, bulk close with a standard reason. Done.
> 
> **[Close]**
> That's an hour of work in 10 minutes. Any questions about the workflow?"

---

### Step-by-Step Guide

| Step | Action | Talking Point |
|------|--------|---------------|
| 1 | Open Alerts | "Your daily home" |
| 2 | Filter: High confidence + 24h | "Focus on what matters" |
| 3 | Click top alert | "Let's investigate" |
| 4 | View Alert Detail | "Why did this trigger?" |
| 5 | Show highlighted text | "No hunting through threads" |
| 6 | Show similar historical | "Pattern detection across time" |
| 7 | Click Open Investigation | — |
| 8 | Explain 3-panel layout | "Timeline, viewer, insights" |
| 9 | Show AI Summary | "23 emails → 3 sentences" |
| 10 | Show Risk Evolution | "When did behavior change?" |
| 11 | Navigate to Search | "Let me check for patterns" |
| 12 | Run guided query | "90 days of similar comms" |
| 13 | Show results | "5 more – this is a pattern" |
| 14 | Create Case | "Evidence is ready" |
| 15 | Bulk close low-risk | "Efficient queue management" |
| 16 | End | "An hour in 10 minutes" |

---

## Demo 3: Configuration Demo (5 minutes)

**Target Persona:** Dr. Priya Sharma (Risk Officer)  
**Goal:** Demonstrate platform configurability  
**Key Message:** "You control the rules, not us"

### Narrative Script

---

> **[OPEN: Policies page]**
> 
> "Let's talk about control. The biggest concern I hear from risk teams is: 'Can we configure this for *our* business?'
> 
> The answer is yes. Let me show you.
> 
> **[Show policy list]**
> These are your active risk policies. Insider trading, market abuse, information barrier breach – each one is independently configurable.
> 
> **[Click into 'Secrecy Language Detection']**
> Let's look at secrecy language detection. This is the policy that would have flagged suspicious communications early.
> 
> **[Show threshold slider]**
> You can tune the sensitivity. High sensitivity catches more – but generates more alerts. Low sensitivity is precise but might miss edge cases. You find the balance for your organization.
> 
> **[Show region activation]**
> And look – I can activate this policy differently by region. APAC regulations are different from EMEA. You set the rules per jurisdiction.
> 
> **[Click 'Preview Impact']**
> Before I deploy any change, I can preview impact on historical data. Watch – if I increase sensitivity by 20%, I'd have seen 14 more alerts last month. Are those valuable? I can review samples before committing.
> 
> **[NAVIGATE: Teams & Access]**
> Now let me show you access control.
> 
> **[Show hierarchy]**
> Tenant → Region → Team → User. Your APAC analysts only see APAC data. Your global managers see everything. We enforce this at the database level, not just the UI.
> 
> **[Click 'Impersonate User']**
> And as an admin, I can impersonate any user to see exactly what they see. Let me switch to 'APAC Analyst'...
> 
> **[Show dashboard change]**
> Notice the dashboard changed. Different numbers, different alerts. That's real data isolation.
> 
> **[Switch back]**
> Back to admin view.
> 
> **[Close]**
> This is enterprise configurability. You own the rules. Questions?"

---

### Step-by-Step Guide

| Step | Action | Talking Point |
|------|--------|---------------|
| 1 | Open Policies | "Control is in your hands" |
| 2 | Show policy list | "Each policy is independent" |
> **[Show Secrecy Language Policy]**
> This policy detected early warning signals in historical conduct events.
| 4 | Show threshold slider | "Tune sensitivity for your risk appetite" |
| 5 | Show region toggles | "Different rules per jurisdiction" |
| 6 | Click Preview Impact | "See effects before deploying" |
| 7 | Review sample alerts | "Is this valuable? You decide" |
| 8 | Navigate to Teams | "Access control architecture" |
| 9 | Show hierarchy tree | "Tenant → Region → Team → User" |
| 10 | Click Impersonate | "See what users see" |
| 11 | Show dashboard change | "Real data isolation" |
| 12 | Switch back | — |
| 13 | End | "Enterprise configurability. Questions?" |

---

## Demo Tips

### Before the Demo
- [ ] Reset demo environment to clean state
- [ ] Pre-load investigation workspace with interesting thread
- [ ] Ensure historical surveillance data shows high-risk spikes
- [ ] Test screen sharing and resolution

### During the Demo
- Let the demo breathe – pause after key reveals
- Use "notice how" to direct attention
- Keep mouse movements slow and deliberate
- If something fails, say "let me show you an alternative view"

### Closing Lines
| Audience | Closing Line |
|----------|--------------|
| Executives | "This is regulator-ready from day one" |
| Analysts | "This is built for how you actually work" |
| Risk/IT | "This is configured for your business, not ours" |

---

## Common Questions & Answers

| Question | Suggested Answer |
|----------|------------------|
| "How long to implement?" | "Pilot in 6 weeks, full rollout in 90 days" |
| "Can we bring our own data?" | "Yes, we have email, chat, and voice ingestion connectors" |
| "What about PII/GDPR?" | "Multi-region deployment with data residency controls" |
| "Do we replace existing tools?" | "Can integrate or replace – depends on your stack" |
| "What's the AI model?" | "State-of-the-art LLMs with fine-tuning for financial comms" |
