This lab is meant to walk users through the first two stages of their GenAI journey on Databricks - namely Prompt Engineering and RAG. 

It does require some setup:
1. Preprocessed PDF files chunked into a gold table
2. Vector Search endpoint setup and PAT created and stored as a secret scope
3. Vector Search Index created under main.default.{table_name}

Once those are done everything else should be very straight forward. Users will be broken out into their own schemas under the 'main' catalog.