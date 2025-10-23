# Agent Bricks Lab: Build, Orchestrate, and Improve Multi-Agent Systems

In this lab, you’ll learn how to create and refine AI agents using **Databricks Agent Bricks**. You’ll start by building a **Knowledge Assistant** grounded in company product docs and historical support tickets, then expand it with a **Genie-powered structured data agent**. Finally, you’ll orchestrate them together with a **Multi-Agent Supervisor** and guide the system to produce better, user-friendly responses.

---

## Part 1: Build Your First Knowledge Assistant  

### 1.1 Create a Vector Search Index  
- **Why Vector Search?**  
  - Provides efficient retrieval of relevant chunks of data for grounding LLM responses.  
  - Two common types:  
    - **Triggered updates** (for static knowledge bases like FAQs/policies).  
    - **Continuous updates** (for dynamic sources like support tickets).  
- **Demo:** Indexes are pre-built for this lab, but you’ll see how easy it is to create one.

### 1.2 Build the Knowledge Assistant Agent  
- **Navigate to “Agents”** in the UI.  
- **Create a new Knowledge Assistant** using the two pre-built vector search indices:  
  - **Knowledge Base** – Company details, FAQs, policies, and procedures.  
  - **Support Tickets** – Historical tickets and their resolutions.  
- **Example setup:**  
  - **Name:** `[your_initials]-BricksLab-TechnicalSupport`  
  - **Description:** Provides telco product support using company docs and historical tickets.  

### 1.3 Test the Knowledge Assistant  
- **Sample Question:** *How do I know if my 5G is working?*  
- Observe the verbose answer with citations and traces.  
- Explore how the assistant grounds responses in living company data.  

---

## Part 2: Expand with Genie for Structured Data  

### 2.1 Query Structured Data with Genie  
- **Genie spaces** allow natural language queries over structured data (SQL tables).  
- Genie is pre-configured to access **billing and customer tables**.  
- **Try It Out:**  
  - Ask *“What is the average total bill?”*  
  - Guide Genie with examples/instructions to better align with your data structures.  

### 2.2 Treat Genie as an Agent  
- Genie rooms can be registered as agents, enabling them to participate in multi-agent workflows.  
- Use Genie when customer-specific or billing data is required.  

---

## Part 3: Orchestrate with a Multi-Agent Supervisor  

### 3.1 Create a Multi-Agent Supervisor (MAS)  
- Combines multiple agents to intelligently route queries.  
- **Setup:**  
  - **MAS Name:** `[your_initials]-BricksLab-MultiAgent`  
  - **Description:** Provides telco support across both product and billing questions.  
  - **Add Agents:**  
    - Genie Agent → Billing and customer data.  
    - Knowledge Assistant → Product and support documentation.  

### 3.2 Test the MAS  
- **Billing Question:** *Why did my bill go up this month?*  
  - Add context: *Assume user ID = `CUS-10001`, date = June 2025*.  
  - MAS should route query to Genie for customer-specific data.  
- **Support Question:** *My phone is getting hot — what does hotspot mean, and how do I turn it off?*  
  - MAS routes to Knowledge Assistant for product guidance.  

---

## Part 4: Improve Quality with Feedback  

### 4.1 Identify Response Issues  
- Some answers may be too verbose or technical for end users.  
- Example: The hotspot explanation may be correct but overly long.

### 4.2 Provide Feedback via Labeling Session  
- Click **“Improve Quality”** on the agent.  
- Add the question: *“What does hotspot mean and how do I turn it off?”*  
- Open labeling session → Leave feedback:  
  - *“Keep the response very short, two sentences max.”*  
- Save feedback and merge changes into the agent.  

### 4.3 Re-test the Agent  
- Verify concise responses are now produced.  
- Observe how natural language feedback guides behavior without coding.  

---

## Next Steps  
- **Governance & Permissions:** Use Unity Catalog to control agent access on behalf of users.  
- **Real-World Extension:** Continuously stream support tickets into your knowledge base.  
- **Multi-Agent Patterns:** Add more specialized agents (e.g., troubleshooting, recommendations).  
- **Production Deployment:** Register agents, monitor with MLflow, and integrate with apps or support portals.  

---

🎉 Congratulations! You’ve built a **multi-agent system with Agent Bricks** that combines structured and unstructured data, routes intelligently, and adapts with user feedback. Time to add *“Agent Bricks Master”* to your LinkedIn!  
