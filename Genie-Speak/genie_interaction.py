import logging
import requests
import time
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Load environment variables
load_dotenv()

# Global constants
DEBUG = False
BASE_URL = os.getenv('GENIE_BASE_URL')
MAX_WAIT_SECONDS = 15  # Reduced timeout
POLL_INTERVAL = 0.05  # 50 milliseconds between polling attempts
DEFAULT_ACCESS_TOKEN = os.getenv('GENIE_ACCESS_TOKEN')
DEFAULT_SPACE_ID = os.getenv('GENIE_SPACE_ID')
DEFAULT_MAX_ROWS = 3  # Default maximum rows to display

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def debug_print(message):
    if DEBUG:
        print(f"DEBUG: {message}", flush=True)
        logger.info(f"DEBUG: {message}")

class GenieError(Exception):
    """Custom exception for Genie API errors."""

class GenieClient:
    """A client to interact with Databricks Genie Conversation API."""
    
    def __init__(self, base_url: str, access_token: str, space_id: str):
        self.base_url = base_url.rstrip("/")
        self.space_id = space_id
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def start_conversation(self, prompt: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/2.0/genie/spaces/{self.space_id}/start-conversation"
        payload = {"content": prompt}
        
        debug_print(f"Starting conversation with URL: {url}")
        debug_print(f"Prompt: {prompt}")
        
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 403:
            raise GenieError(f"Access forbidden: Check your access token and permissions. URL: {url}")
        response.raise_for_status()
        return response.json()
    
    def get_message_status(self, conversation_id: str, message_id: str) -> Dict[str, Any]:
        url = (f"{self.base_url}/api/2.0/genie/spaces/{self.space_id}/"
               f"conversations/{conversation_id}/messages/{message_id}")
        
        response = requests.get(url, headers=self.headers)
        if response.status_code == 403:
            raise GenieError("Access forbidden: Check your access token and permissions.")
        response.raise_for_status()
        return response.json()
    
    def get_query_result(self, conversation_id: str, message_id: str, attachment_id: str) -> Dict[str, Any]:
        url = (f"{self.base_url}/api/2.0/genie/spaces/{self.space_id}/"
               f"conversations/{conversation_id}/messages/{message_id}/"
               f"attachments/{attachment_id}/query-result")
        
        response = requests.get(url, headers=self.headers)
        if response.status_code == 403:
            raise GenieError("Access forbidden: Check your access token and permissions.")
        response.raise_for_status()
        return response.json()
    
    def submit_prompt(
        self, 
        prompt: str, 
        max_wait_seconds: int = MAX_WAIT_SECONDS,
        poll_interval: int = POLL_INTERVAL
    ) -> Optional[Dict[str, Any]]:
        start_resp = self.start_conversation(prompt)
        conv_id = start_resp["conversation_id"]
        msg_id = start_resp["message_id"]
        
        start_time = time.time()
        while time.time() - start_time < max_wait_seconds:
            status_resp = self.get_message_status(conv_id, msg_id)
            
            if isinstance(status_resp, dict):
                if "status" in status_resp:
                    current_state = status_resp["status"]
                elif "message" in status_resp and isinstance(status_resp["message"], dict):
                    current_state = status_resp["message"].get("status", "UNKNOWN")
                else:
                    current_state = "UNKNOWN"
            else:
                current_state = "UNKNOWN"
            
            if current_state == "COMPLETED":
                attachments = []
                if "attachments" in status_resp:
                    attachments = status_resp["attachments"]
                elif "message" in status_resp and "attachments" in status_resp["message"]:
                    attachments = status_resp["message"]["attachments"]
                    
                if attachments and len(attachments) > 0:
                    attachment = attachments[0]
                    attachment_id = attachment["attachment_id"]
                    
                    if "text" in attachment:
                        return {"text_response": attachment["text"]["content"]}
                    else:
                        return self.get_query_result(conv_id, msg_id, attachment_id)
                else:
                    return status_resp
            elif current_state == "FAILED":
                error_msg = status_resp.get("error", {}).get("message", "Unknown error")
                raise GenieError(f"Query failed: {error_msg}")
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"No result after {max_wait_seconds} seconds")
    
    @staticmethod
    def parse_result(result: Dict[str, Any], max_rows: int = DEFAULT_MAX_ROWS) -> str:
        if "text_response" in result:
            return result["text_response"]
        
        if "statement_response" in result:
            statement = result["statement_response"]
            
            if "result" in statement and "data_array" in statement["result"]:
                data_array = statement["result"]["data_array"]
                
                if not data_array:
                    return "No results found."
                
                total_rows = len(data_array)
                
                column_name = "Value"
                if ("manifest" in statement and 
                    "schema" in statement["manifest"] and 
                    "columns" in statement["manifest"]["schema"] and 
                    statement["manifest"]["schema"]["columns"]):
                    column_name = statement["manifest"]["schema"]["columns"][0]["name"]
                
                rows_to_show = min(total_rows, max_rows)
                output_rows = []
                
                for i in range(rows_to_show):
                    if data_array[i] and len(data_array[i]) > 0:
                        output_rows.append(f"{data_array[i][0]}")
                
                response = ""
                if total_rows > max_rows:
                    response = f"Found {total_rows} results. Showing first {rows_to_show}: "
                
                if output_rows:
                    if column_name:
                        response += f"{column_name}: " + ", ".join(output_rows)
                    else:
                        response += ", ".join(output_rows)
                else:
                    response = "No results found."
                
                return response
        
        metadata = result.get("query_result_metadata", {})
        manifest = result.get("manifest", {})
        
        if not metadata.get("row_count"):
            return "No results found."
        
        rows = manifest.get("rows", [])
        columns = [col["name"] for col in manifest.get("columns", [])]
        
        if rows and columns:
            return f"{columns[0]}: {rows[0][0]}"
        elif rows:
            return f"Found {metadata['row_count']} results. First value: {rows[0][0]}"
        
        return "Data available but format unexpected."

if __name__ == "__main__":
    print("Databricks Genie Client")
    print("=======================")
    
    # Initialize client with default credentials
    genie = GenieClient(
        base_url=BASE_URL,
        access_token=DEFAULT_ACCESS_TOKEN,
        space_id=DEFAULT_SPACE_ID
    )
    
    # Query loop
    while True:
        prompt = input("\nEnter your query (or 'exit' to quit): ")
        print(f"You entered: '{prompt}'", flush=True)
        
        if prompt.lower() in ('exit', 'quit', 'q'):
            break
        
        try:
            raw_result = genie.submit_prompt(prompt)
            result_text = genie.parse_result(raw_result)
            print(f"\nGenie Response: {result_text}")
            
        except GenieError as e:
            print(f"\nError: {str(e)}")
        except TimeoutError:
            print("\nRequest timed out. Try increasing max_wait_seconds.")
        except Exception as e:
            print(f"\nUnexpected error: {str(e)}")