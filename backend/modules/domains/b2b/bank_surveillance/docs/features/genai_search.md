# GenAI Search & Discovery Capabilities
**Dataset**: Enron Email Corpus (Fraud, Insider Trading, Collusion)

## 1. Guided Search (Query Expansion) 🌟 [SELECTED FOR DEMO]
**"The expert on your shoulder."**

Junior analysts often don't know the specific code words or entities to look for. Guided search uses GenAI to bridge the gap between a vague intent and specific, high-recall search terms.
-   **Capability**: LLM-driven query expansion and suggestion.
-   **Demo Scenario**:
    -   *User types*: "Show me financial engineering deals."
    -   *System Suggests*: "I found limited results for 'financial engineering'. However, in this dataset, the following related terms appear frequently in a high-risk context: **'Raptor'**, **'LJM'**, **'Chewco'**, **'Whitewing'**. Would you like to add these to your filter?"
    -   *Why it matters*: Enhances analyst capability by injecting domain intelligence (Enron-specific knowledge) into the search process.

## 2. Intent-Based Semantic Search
**"Find what they meant, not just what they said."**

Traditional keyword search fails when bad actors use code words or vague language.
-   **Capability**: Vector-based semantic retrieval.
-   **Demo Scenario**:
    -   *Query*: "Show me emails about hiding debt or off-balance sheet partnerships."
    -   *Result*: Matches emails discussing "Raptor", "LJM", "Special Purpose Vehicles", and "moving the loss", even if the word "debt" isn't used.
    -   *Why it matters*: Uncovers concealed intent.

## 2. "More Like This" Behavioral Pattern Matching
**"Clone the investigation vector."**

Analysts often find one "smoking gun" email and need to find similar behavioral patterns.
-   **Capability**: Embedding-based similarity search using the *style* and *intent* of a reference email.
-   **Demo Scenario**:
    -   *Action*: Highlight an email where Fastow pressures a subordinate to sign a deal without due diligence.
    -   *Click*: "Find similar coercive pressure".
    -   *Result*: List of emails from other executives using similar linguistic patterns of urgency and authority to bypass controls.

## 3. Sentiment & Pressure Heatmaps
**"Visualize the panic."**

Detect anomalies in emotional tone that correlate with fraudulent events (e.g., quarterly reporting deadlines).
-   **Capability**: Time-series sentiment analysis aggregated by department or key individual.
-   **Demo Scenario**:
    -   *Visualization*: A timeline graph of "Anxiety/Panic" scores for the Accounting Department.
    -   *Insight*: Huge spike in panic 3 days before the Q3 earnings release.
    -   *Drill-down*: Click the spike to see the specific emails reacting to the "accounting error".

## 4. Entity Knowledge Graphing (The "Who Knew?" Graph) 🌟 [SELECTED FOR DEMO]
**"Map the conspiracy."**

Understanding the subtle network of who communicates with whom about sensitive topics is critical for proving collusion.
-   **Capability**: RAG-extracted entity relationships visualized as a force-directed graph.
-   **Selected Use Case**:
    -   **Prompt**: "Visualize the network of people discussing 'LJM' partnerships."
    -   **Visual**: A central node for `Andrew Fastow`, connected by thick red lines (high frequency/sentiment) to `Michael Kopper` and `Ben Glisan`.
    -   **Interaction**: Click the edge between Fastow and Kopper -> Show the summary: *"Discussing the creation of LJM1 to absorb Enron's debt."*
    -   **Insight**: Reveal the "Inner Circle" of the fraud.


## 5. Temporal Narrative Summarization
**"Tell me the story."**

Synthesizing thousands of emails into a coherent timeline of events.
-   **Capability**: LLM-based multi-document summarization with citation.
-   **Demo Scenario**:
    -   *Prompt*: "Summarize the timeline of the California Energy Crisis discussions."
    -   *Result*: A bulleted timeline:
        -   *Aug 2000*: Traders discuss "Death Star" strategy.
        -   *Dec 2000*: Emails regarding "over-scheduling" transmission lines.
        -   *Jan 2001*: Direct communications about "creating shortages" to spike prices.
    -   *Citations*: Each point links to the source emails.
