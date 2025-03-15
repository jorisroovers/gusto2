import os
import pandas as pd
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import requests
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Notion API configuration
NOTION_API_TOKEN = os.environ.get("NOTION_API_TOKEN")
NOTION_MEALPLAN_PAGE_ID = os.environ.get("NOTION_MEALPLAN_PAGE_ID")

# Path to the data directory
DATA_DIR = "/app/data"
MEALS_CSV = os.path.join(DATA_DIR, "meals.csv")
CHANGESET_FILE = os.path.join(DATA_DIR, "changeset.csv")
CHANGED_INDICES_FILE = os.path.join(DATA_DIR, "changed_indices.txt")
# Store Notion page IDs for each row to enable updates
NOTION_PAGE_IDS_FILE = os.path.join(DATA_DIR, "notion_page_ids.json")

# Global variables to store loaded data
all_meals_df = None
changeset_df = None  # Store the changeset persistently
changed_indices = set()  # Track which meal indices have been modified
notion_page_ids = {}  # Map dates to Notion page IDs

# Model for meal data
class Meal(BaseModel):
    Name: Optional[str] = None
    Date: Optional[str] = None
    Tags: Optional[str] = None
    Notes: Optional[str] = None

# Load Notion page IDs mapping if it exists
def load_notion_page_ids():
    global notion_page_ids
    if os.path.exists(NOTION_PAGE_IDS_FILE):
        try:
            with open(NOTION_PAGE_IDS_FILE, 'r') as f:
                notion_page_ids = json.load(f)
            logger.info(f"Loaded {len(notion_page_ids)} Notion page IDs from file")
        except Exception as e:
            logger.error(f"Error loading Notion page IDs: {e}")
            notion_page_ids = {}
    return notion_page_ids

# Save Notion page IDs mapping to file
def save_notion_page_ids():
    try:
        with open(NOTION_PAGE_IDS_FILE, 'w') as f:
            json.dump(notion_page_ids, f)
        logger.info(f"Saved {len(notion_page_ids)} Notion page IDs to file")
    except Exception as e:
        logger.error(f"Error saving Notion page IDs: {e}")

def fetch_from_notion():
    """Fetch meal data from Notion database and save to local file"""
    global notion_page_ids
    
    if not NOTION_API_TOKEN or not NOTION_MEALPLAN_PAGE_ID:
        logger.warning("Notion API token or page ID not provided. Skipping Notion fetch.")
        return False
    
    try:
        # Set up headers for Notion API
        headers = {
            "Authorization": f"Bearer {NOTION_API_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"  # Use the current Notion API version
        }
        
        # Query the database using Notion's REST API
        logger.info(f"Fetching meals from Notion database: {NOTION_MEALPLAN_PAGE_ID}")
        
        # API endpoint for querying a database
        url = f"https://api.notion.com/v1/databases/{NOTION_MEALPLAN_PAGE_ID}/query"
        
        # Collect all pages with pagination
        has_more = True
        start_cursor = None
        all_results = []
        
        # Reset the page IDs mapping
        notion_page_ids = {}
        
        while has_more:
            # Prepare query with sort by date
            query_data = {
                "sorts": [{"property": "Date", "direction": "ascending"}]
            }
            
            # Add start_cursor for pagination if we have one
            if start_cursor:
                query_data["start_cursor"] = start_cursor
                
            # Make the API request
            response = requests.post(url, headers=headers, json=query_data)
            
            # Check for successful response
            if response.status_code != 200:
                logger.error(f"Failed to fetch from Notion API: {response.status_code} - {response.text}")
                return False
            
            # Parse the JSON response
            data = response.json()
            
            # Add results to our collection
            all_results.extend(data.get("results", []))
            
            # Check if there are more pages
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
            
            logger.info(f"Fetched {len(data.get('results', []))} meals from Notion, has_more: {has_more}")
        
        logger.info(f"Total meals fetched from Notion: {len(all_results)}")
        
        # Process the response into a DataFrame
        meals_data = []
        
        for page in all_results:
            page_id = page.get("id")
            properties = page.get("properties", {})
            meal = {}
            
            # Extract date if exists
            date_str = None
            if "Date" in properties:
                date_prop = properties["Date"]
                if date_prop["type"] == "date" and date_prop.get("date"):
                    date_str = date_prop["date"].get("start")
                    if date_str:
                        # Convert from ISO format to our expected format
                        try:
                            date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            meal["Date"] = date_obj.strftime('%Y/%m/%d')
                            
                            # Store the page ID mapped to the date string for later updates
                            notion_page_ids[meal["Date"]] = page_id
                        except ValueError:
                            meal["Date"] = None
            
            # Extract name if exists
            if "Name" in properties:
                name_prop = properties["Name"]
                if name_prop["type"] == "title" and name_prop.get("title"):
                    title_parts = [part.get("plain_text", "") for part in name_prop.get("title", [])]
                    meal["Name"] = " ".join(title_parts).strip()
            
            # Extract tags if exists
            if "Tags" in properties:
                tags_prop = properties["Tags"]
                if tags_prop["type"] == "multi_select" and tags_prop.get("multi_select"):
                    tags = [tag.get("name", "") for tag in tags_prop.get("multi_select", [])]
                    meal["Tags"] = ", ".join(tags)
            
            # Extract notes if exists
            if "Notes" in properties:
                notes_prop = properties["Notes"]
                if notes_prop["type"] == "rich_text" and notes_prop.get("rich_text"):
                    notes_parts = [part.get("plain_text", "") for part in notes_prop.get("rich_text", [])]
                    meal["Notes"] = " ".join(notes_parts).strip()
                    
            meals_data.append(meal)
        
        # Create DataFrame
        if not meals_data:
            logger.warning("No meal data found in Notion database")
            return False
            
        meals_df = pd.DataFrame(meals_data)
        
        # Convert Date to datetime for sorting
        if 'Date' in meals_df.columns:
            meals_df['Date'] = pd.to_datetime(meals_df['Date'], errors='coerce')
            
        # Sort by date (although we already requested sorted data from Notion)
        # This ensures proper ordering in case some dates were invalid
        if 'Date' in meals_df.columns:
            meals_df = meals_df.sort_values(by='Date')
        
        # Add Weekday column
        if 'Date' in meals_df.columns and meals_df['Date'].notna().any():
            # Create a Weekday column with the day name
            meals_df['Weekday'] = meals_df['Date'].apply(
                lambda x: x.day_name() if pd.notna(x) else None
            )
            
        # Convert Date back to string format for saving
        if 'Date' in meals_df.columns:
            meals_df['Date'] = meals_df['Date'].apply(
                lambda x: x.strftime('%Y/%m/%d') if pd.notna(x) else None
            )
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(MEALS_CSV), exist_ok=True)
        
        # Save to CSV
        columns = ['Weekday', 'Date', 'Name', 'Tags', 'Notes']
        columns = [col for col in columns if col in meals_df.columns]
        meals_df.to_csv(MEALS_CSV, index=False, columns=columns)
        
        # Save the mapping of dates to Notion page IDs
        save_notion_page_ids()
        
        logger.info(f"Successfully saved {len(meals_data)} meals from Notion to {MEALS_CSV}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to fetch meal data from Notion: {str(e)}")
        return False

def save_to_notion(meals_df, changed_indices_set):
    """Save changed meal rows back to Notion"""
    if not NOTION_API_TOKEN:
        logger.warning("Notion API token not provided. Skipping Notion update.")
        return False
    
    # Load the Notion page IDs mapping if not already loaded
    if not notion_page_ids:
        load_notion_page_ids()
    
    if not notion_page_ids:
        logger.warning("No Notion page IDs mapping available. Cannot update Notion.")
        return False
    
    try:
        # Set up headers for Notion API
        headers = {
            "Authorization": f"Bearer {NOTION_API_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        success_count = 0
        
        # Get only the changed meals by their indices
        for idx in changed_indices_set:
            if idx >= len(meals_df):
                logger.warning(f"Index {idx} is out of bounds for meals dataframe of length {len(meals_df)}")
                continue
                
            # Get the meal data at this index
            meal = meals_df.iloc[idx].to_dict()
            
            # Skip if no date (we need the date to find the Notion page ID)
            if 'Date' not in meal or not meal['Date'] or pd.isna(meal['Date']):
                logger.warning(f"Meal at index {idx} has no valid date, skipping Notion update")
                continue
                
            # Convert date to string format if it's not already
            if isinstance(meal['Date'], pd.Timestamp):
                date_str = meal['Date'].strftime('%Y/%m/%d')
            else:
                date_str = str(meal['Date'])
            
            # Check if we have the page ID for this date
            if date_str not in notion_page_ids:
                logger.warning(f"No Notion page ID found for date {date_str}, skipping update")
                continue
                
            page_id = notion_page_ids[date_str]
            
            # Prepare the update payload
            properties = {}
            
            # Add Name property (title)
            if 'Name' in meal and meal['Name'] and not pd.isna(meal['Name']):
                properties["Name"] = {
                    "title": [
                        {
                            "type": "text",
                            "text": {"content": meal['Name']}
                        }
                    ]
                }
            else:
                # Clear the title if Name is empty
                properties["Name"] = {"title": []}
            
            # Add Notes property (rich text)
            if 'Notes' in meal and meal['Notes'] and not pd.isna(meal['Notes']):
                properties["Notes"] = {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": meal['Notes']}
                        }
                    ]
                }
            else:
                # Clear the notes if empty
                properties["Notes"] = {"rich_text": []}
            
            # Add Tags property (multi-select)
            if 'Tags' in meal and meal['Tags'] and not pd.isna(meal['Tags']):
                tags = [tag.strip() for tag in meal['Tags'].split(',') if tag.strip()]
                properties["Tags"] = {
                    "multi_select": [{"name": tag} for tag in tags]
                }
            else:
                # Clear tags if empty
                properties["Tags"] = {"multi_select": []}
            
            # Create the update request payload
            update_data = {
                "properties": properties
            }
            
            # Make the API request to update the page
            update_url = f"https://api.notion.com/v1/pages/{page_id}"
            response = requests.patch(update_url, headers=headers, json=update_data)
            
            # Check for successful response
            if response.status_code == 200:
                logger.info(f"Successfully updated Notion page for date {date_str}")
                success_count += 1
            else:
                logger.error(f"Failed to update Notion page for date {date_str}: {response.status_code} - {response.text}")
        
        logger.info(f"Updated {success_count} meal(s) in Notion out of {len(changed_indices_set)} changed indices")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Failed to save changes to Notion: {str(e)}")
        return False

def read_meals():
    global all_meals_df
    
    # If meals are already loaded, return the cached data
    if all_meals_df is not None:
        return all_meals_df
    
    # Load directly from meals.csv file (assume it exists)
    all_meals = pd.read_csv(MEALS_CSV)
    all_meals = all_meals.replace({pd.NA: None, pd.NaT: None})
    
    # Drop Weekday column if it exists
    if 'Weekday' in all_meals.columns:
        all_meals = all_meals.drop('Weekday', axis=1)
    
    # Convert Date column to datetime if it exists
    if 'Date' in all_meals.columns:
        all_meals['Date'] = pd.to_datetime(all_meals['Date'], errors='coerce')
    
    # Store in global variable for future use
    all_meals_df = all_meals
    
    return all_meals

def get_changed_indices():
    """Load the set of changed meal indices from file"""
    global changed_indices
    
    if changed_indices:
        return changed_indices
    
    # Check if changed indices file exists
    if os.path.exists(CHANGED_INDICES_FILE):
        try:
            with open(CHANGED_INDICES_FILE, 'r') as f:
                indices = f.read().strip().split(',')
                # Filter out empty strings and convert to integers
                changed_indices = {int(idx) for idx in indices if idx.strip().isdigit()}
                return changed_indices
        except Exception as e:
            print(f"Error loading changed indices: {e}")
            changed_indices = set()
            return changed_indices
    
    # If file doesn't exist, return empty set
    changed_indices = set()
    return changed_indices

def save_changed_indices(indices_set):
    """Save the set of changed meal indices to file"""
    global changed_indices
    
    # Update the global variable
    changed_indices = indices_set
    
    # Save to file
    try:
        with open(CHANGED_INDICES_FILE, 'w') as f:
            if indices_set:
                f.write(','.join(str(idx) for idx in indices_set))
            else:
                f.write('')
    except Exception as e:
        print(f"Error saving changed indices: {e}")

def get_changeset():
    """Get the current changeset, loading it from disk if necessary"""
    global changeset_df
    
    if changeset_df is not None:
        return changeset_df
    
    # Check if changeset file exists
    if os.path.exists(CHANGESET_FILE):
        try:
            # Load the changeset from file
            cs = pd.read_csv(CHANGESET_FILE)
            
            # Convert Date column to datetime if it exists
            if 'Date' in cs.columns:
                cs['Date'] = pd.to_datetime(cs['Date'], errors='coerce')
                
            changeset_df = cs
            return cs
        except Exception as e:
            print(f"Error loading changeset: {e}")
            # Return empty DataFrame if there was an error
            changeset_df = pd.DataFrame()
            return changeset_df
    else:
        # If no changeset exists, create an empty one
        changeset_df = pd.DataFrame()
        return changeset_df

def save_changeset(meals_df):
    """Save the changeset DataFrame to disk"""
    global changeset_df
    
    # Store the changeset in memory
    changeset_df = meals_df.copy()
    
    # Format the Date column back to YYYY/MM/DD before saving
    if 'Date' in meals_df.columns:
        formatted_df = meals_df.copy()
        formatted_df['Date'] = formatted_df['Date'].apply(
            lambda x: x.strftime('%Y/%m/%d') if pd.notna(x) else None
        )
    else:
        formatted_df = meals_df.copy()
    
    # Save to CSV
    formatted_df.to_csv(CHANGESET_FILE, index=False)
    
    return True

def update_changeset(index, meal):
    """Update a single meal in the changeset"""
    changeset = get_changeset()
    
    # If changeset is empty, initialize it with the current meals
    if changeset.empty:
        changeset = read_meals().copy()
    
    # Update the meal at the given index
    for key, value in meal.items():
        if key in changeset.columns:
            changeset.at[index, key] = value
    
    # Save the updated changeset
    save_changeset(changeset)
    
    # Add this index to the set of changed indices
    changed_indices = get_changed_indices()
    changed_indices.add(index)
    save_changed_indices(changed_indices)
    
    return changeset
        
def df_to_json(df):
    if not df.empty:
        return df.to_dict(orient='records')
    return []

def save_meals_to_csv(meals_df):
    """Save the updated meals dataframe to CSV file."""
    global all_meals_df
    
    # Add back the Weekday column if it was in the original file
    # We can derive it from the Date
    if meals_df['Date'].notna().any():
        # Create a Weekday column with the day name
        meals_df['Weekday'] = meals_df['Date'].apply(
            lambda x: x.day_name() if pd.notna(x) else None
        )
    
    # Format the Date column back to YYYY/MM/DD before saving
    if 'Date' in meals_df.columns:
        meals_df['Date'] = meals_df['Date'].apply(
            lambda x: x.strftime('%Y/%m/%d') if pd.notna(x) else None
        )
    
    # Save to CSV
    # Define column order to match original file
    columns = ['Weekday', 'Date', 'Name', 'Tags', 'Notes']
    # Only include columns that exist in our dataframe
    columns = [col for col in columns if col in meals_df.columns]
    
    meals_df.to_csv(MEALS_CSV, index=False, columns=columns)
    
    # Reset the cached dataframe to force reloading
    all_meals_df = None
    
    # Clear the changeset after saving
    if os.path.exists(CHANGESET_FILE):
        try:
            os.remove(CHANGESET_FILE)
        except Exception as e:
            print(f"Error removing changeset file: {e}")
    
    # Clear the changed indices file
    if os.path.exists(CHANGED_INDICES_FILE):
        try:
            os.remove(CHANGED_INDICES_FILE)
        except Exception as e:
            print(f"Error removing changed indices file: {e}")
    
    # Reset the changeset and changed indices in memory
    global changeset_df, changed_indices
    changeset_df = None
    changed_indices = set()
    
    return True

# Initialize by loading page IDs
load_notion_page_ids()

@app.get("/api/hello")
async def hello_world():
    # First, check if there's a changeset
    changeset = get_changeset()
    changed_indices = get_changed_indices()
    
    # If changeset exists and is not empty, return that
    if not changeset.empty:
        return {
            "meals": df_to_json(changeset), 
            "hasChanges": len(changed_indices) > 0,
            "changedIndices": list(changed_indices)
        }
    
    # Otherwise, return the original meals
    meals = read_meals()
    return {
        "meals": df_to_json(meals), 
        "hasChanges": False, 
        "changedIndices": []
    }

@app.put("/api/meal/{index}")
async def update_meal(index: int, meal: Dict[str, Any] = Body(...)):
    """Update a meal at the given index in the changeset."""
    try:
        # Convert index to integer
        index = int(index)
        
        # Update the meal in the changeset
        update_changeset(index, meal)
        
        # Return the updated changed indices
        changed_indices = get_changed_indices()
        
        return {
            "status": "success", 
            "message": "Meal updated in changeset", 
            "changedIndices": list(changed_indices)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update meal: {str(e)}")

@app.post("/api/meals/save")
async def save_meals(meals: List[Dict[str, Any]] = Body(...)):
    """Save all meals from the changeset to the CSV file and update Notion."""
    try:
        # Create a DataFrame from the received meals
        meals_df = pd.DataFrame(meals)
        
        # Convert Date column to datetime if it exists
        if 'Date' in meals_df.columns:
            meals_df['Date'] = pd.to_datetime(meals_df['Date'], errors='coerce')
        
        # Get the set of changed indices before saving
        changed_indices = get_changed_indices()
        
        # Update Notion with only the changed rows
        notion_updated = False
        if changed_indices:
            notion_updated = save_to_notion(meals_df, changed_indices)
        
        # Save to CSV
        save_meals_to_csv(meals_df)
        
        return {
            "status": "success", 
            "message": "All meals saved successfully" + (" and updated in Notion" if notion_updated else ""),
            "notionUpdated": notion_updated
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save meals: {str(e)}")

@app.get("/api/meals/reload")
async def reload_meals():
    """Force reload meals from the CSV file, discarding any unsaved changes.
    Also attempts to fetch updated data from Notion if configured."""
    try:
        # Force reload by resetting the cached DataFrame
        global all_meals_df, changeset_df, changed_indices
        all_meals_df = None
        changeset_df = None
        changed_indices = set()
        
        # Remove the changeset file if it exists
        if os.path.exists(CHANGESET_FILE):
            try:
                os.remove(CHANGESET_FILE)
            except Exception as e:
                logger.error(f"Error removing changeset file: {e}")
        
        # Remove the changed indices file if it exists
        if os.path.exists(CHANGED_INDICES_FILE):
            try:
                os.remove(CHANGED_INDICES_FILE)
            except Exception as e:
                logger.error(f"Error removing changed indices file: {e}")
        
        # First try to fetch fresh data from Notion
        notion_fetch_success = fetch_from_notion()
        
        # Read the meals from the CSV file (either the newly fetched one or the existing one)
        meals = read_meals()
        
        return {
            "status": "success", 
            "message": "Meals reloaded successfully" + (" (updated from Notion)" if notion_fetch_success else " (from local file)"), 
            "meals": df_to_json(meals),
            "notionUpdated": notion_fetch_success
        }
        
    except Exception as e:
        logger.error(f"Failed to reload meals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload meals: {str(e)}")

@app.get("/api/meals/changes")
async def get_changes():
    """Get the current changeset and changed indices."""
    try:
        changeset = get_changeset()
        changed_indices = get_changed_indices()
        
        # If changeset exists and is not empty, return that
        if not changeset.empty:
            return {
                "changes": df_to_json(changeset), 
                "hasChanges": len(changed_indices) > 0,
                "changedIndices": list(changed_indices)
            }
        
        # Otherwise, return an empty array
        return {
            "changes": [], 
            "hasChanges": False, 
            "changedIndices": []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get changeset: {str(e)}")

@app.post("/api/meals/add-to-changeset")
async def add_to_changeset(meals: List[Dict[str, Any]] = Body(...)):
    """Add meals to the changeset."""
    try:
        # Create a DataFrame from the received meals
        meals_df = pd.DataFrame(meals)
        
        # Convert Date column to datetime if it exists
        if 'Date' in meals_df.columns:
            meals_df['Date'] = pd.to_datetime(meals_df['Date'], errors='coerce')
        
        # Save the changeset
        save_changeset(meals_df)
        
        return {"status": "success", "message": "Changes stored successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add to changeset: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

