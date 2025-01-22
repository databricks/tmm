### Hands-On Lab: Building Agent Systems with Databricks

This lab is split into two parts. In **Part 1**, you will build and test a Databricks agent with various tool calls for a customer service scenario. In **Part 2**, you will create a more streamlined agent that answers product questions and focus on evaluating its performance.

---

### Part 1: Architect Your First Agent
##### Notebook: 01_create_tools\01_create_tools

#### 1.1 Build Tools
- **SQL Functions**  
  - Write queries to access data critical for handling a customer service return workflow.  
  - These SQL functions are easy to call from within a notebook or an agent.
- **Simple Python Function**  
  - Create a Python function to address common limitations of language models.  
  - Register it as a “tool” so the agent can call it on demand.

#### 1.2 Integrate with an LLM [AI Playground]
- **Combine Tools & LLM**  
  - Use the Databricks AI Playground to bring together your SQL/Python tools and the Language Model (LLM).  
  - Model: Meta Llama 3.3 70B
  - Tools: labuser##_##_vocareum_com.agents.*
  - Backup Tools: agents_lab.product.* (Use this if you can't find your tools)

#### 1.3 Test the Agent [AI Playground]
- **System Prompt**: Call tools until you are confident that all company policies have been satisfied.
- **Ask a Question**: Based on our company policies should we accept the latest return in the queue?
  - Observe the agent’s step-by-step reasoning and final response.
- **Explore MLflow Traces**  
  - Inspect agent runs in MLflow to understand how each tool is being called.  
  
---

### Part 2: Agent Evaluation
##### Notebook: 02_agent_eval\agent

#### 2.1 Define a New Agent and Retriever Tool
- **Vector Search**  
  - We have pre-staged a Vector Search index that retrieves relevant product documentation.  
  - This VS Index can be found at agents_lab.product.product_docs_index
- **Create Retriever Function**  
  - Wrap this Vector Search Index into a function your LLM can call to look up product info.  
  - Use the same LLM for final responses.

##### Notebook: 02_agent_eval/driver

#### 2.2 Define Evaluation Dataset
- **Use Provided Dataset**  
  - Leverage the example evaluation dataset to test your agent’s ability to answer product questions.  
  - (Optional) Experiment with [synthetic data generation](https://www.databricks.com/blog/streamline-ai-agent-evaluation-with-new-synthetic-data-capabilities).

#### 2.3 Evaluate Agent
- **Run `MLflow.evaluate()`** 
  - MLflow compares your agent’s responses to a ground truth dataset.  
  - LLM-based judges score each response, collecting feedback for easy review.

#### 2.4 Refine and Re-Evaluate
- **Improve Retrieval**  
  - Adjust retriever settings (change k=5 to k=1) based on evaluation feedback.  
- **Re-run Evals**  
  - Start a new MLflow run
  - Execute `MLflow.evaluate()` again and compare results.  
  - Observe performance gains in MLflow eval UI

---

### Next Steps
- **Leave Lab Feedback**: We would love to know how we can improve! Plese leave any feedback in our [survey](https://www.surveymonkey.com/r/ZNW8KT7). 
- **Explore More Tools**: Extend your agent with APIs, advanced Python functions, or additional SQL endpoints.  
- **Production Deployment**: Integrate CI/CD for continuous improvement, monitor performance in MLflow, and manage model versions.

---

Congratulations on building and evaluating your agent system in Databricks!
