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

# Import from our database module
from gusto2 import database

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

# Pydantic models for request/response
class Meal(BaseModel):
    Name: Optional[str] = None
    Date: Optional[str] = None
    Tags: Optional[str] = None
    Notes: Optional[str] = None

class Recipe(BaseModel):
    Name: str
    Tags: Optional[str] = None

def fetch_from_notion():
    """Fetch meal data from Notion database and save to database"""
    
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
        database.notion_page_ids = {}
        
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
        
        # Process the response
        meals_data = []
        
        for page in all_results:
            page_id = page.get("id")
            properties = page.get("properties", {})
            meal = {}
            meal["notion_page_id"] = page_id
            
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
                            meal["date"] = date_obj
                            meal["weekday"] = date_obj.strftime('%A')  # Get day name
                            
                            # Store the page ID mapped to the date string for later updates
                            database.notion_page_ids[date_obj.strftime('%Y/%m/%d')] = page_id
                        except ValueError:
                            meal["date"] = None
                            meal["weekday"] = None
            
            # Extract name if exists
            if "Name" in properties:
                name_prop = properties["Name"]
                if name_prop["type"] == "title" and name_prop.get("title"):
                    title_parts = [part.get("plain_text", "") for part in name_prop.get("title", [])]
                    meal["name"] = " ".join(title_parts).strip()
            
            # Extract tags if exists
            if "Tags" in properties:
                tags_prop = properties["Tags"]
                if tags_prop["type"] == "multi_select" and tags_prop.get("multi_select"):
                    tags = [tag.get("name", "") for tag in tags_prop.get("multi_select", [])]
                    meal["tags"] = ", ".join(tags)
            
            # Extract notes if exists
            if "Notes" in properties:
                notes_prop = properties["Notes"]
                if notes_prop["type"] == "rich_text" and notes_prop.get("rich_text"):
                    notes_parts = [part.get("plain_text", "") for part in notes_prop.get("rich_text", [])]
                    meal["notes"] = " ".join(notes_parts).strip()
                    
            meals_data.append(meal)
        
        if not meals_data:
            logger.warning("No meal data found in Notion database")
            return False
        
        # Clear existing meals from the database and insert new data from Notion
        with database.SessionLocal() as db:
            # Delete all existing meals
            db.query(database.MealModel).delete()
            db.commit()
            
            # Insert new meals
            for meal_data in meals_data:
                meal_obj = database.MealModel(**meal_data)
                db.add(meal_obj)
            
            # Commit the transaction
            db.commit()
        
        # Save the mapping of dates to Notion page IDs
        database.save_notion_page_ids()
        
        logger.info(f"Successfully saved {len(meals_data)} meals from Notion to database")
        return True
        
    except Exception as e:
        logger.error(f"Failed to fetch meal data from Notion: {str(e)}")
        return False

def save_to_notion(meals_df, changed_indices_set):
    """Save changed meal rows back to Notion"""
    if not NOTION_API_TOKEN:
        logger.warning("Notion API token not provided. Skipping Notion update.")
        return False
    
    # Load notion page IDs
    database.load_notion_page_ids()
    
    # Set up headers for Notion API
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"  # Use the current Notion API version
    }
    
    update_success_count = 0
    update_count = 0
    
    # Process each changed index
    for idx in changed_indices_set:
        try:
            if idx < 0 or idx >= len(meals_df):
                logger.warning(f"Invalid index {idx}, skipping")
                continue
            
            meal_row = meals_df.iloc[idx]
            
            # Skip if no date (we need it to find the corresponding Notion page)
            if pd.isna(meal_row.get('Date')):
                logger.warning(f"No date for meal at index {idx}, skipping")
                continue
            
            date_str = meal_row['Date'].strftime('%Y/%m/%d')
            
            # Find Notion page ID for this date
            page_id = database.notion_page_ids.get(date_str)
            if not page_id:
                logger.warning(f"No Notion page ID found for date {date_str}, skipping")
                continue
            
            # Prepare properties to update
            properties = {}
            
            # Update name if it exists
            if not pd.isna(meal_row.get('Name')):
                properties["Name"] = {
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": meal_row['Name']
                            }
                        }
                    ]
                }
            
            # Update tags if they exist
            if not pd.isna(meal_row.get('Tags')):
                tags = [tag.strip() for tag in meal_row['Tags'].split(',') if tag.strip()]
                properties["Tags"] = {
                    "multi_select": [{"name": tag} for tag in tags]
                }
            
            # Update notes if they exist
            if not pd.isna(meal_row.get('Notes')):
                properties["Notes"] = {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": meal_row['Notes']
                            }
                        }
                    ]
                }
            
            # Skip if no properties to update
            if not properties:
                logger.info(f"No properties to update for meal at index {idx}, skipping")
                continue
            
            update_count += 1
            
            # Update the page using Notion API
            url = f"https://api.notion.com/v1/pages/{page_id}"
            payload = {"properties": properties}
            
            response = requests.patch(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                logger.error(f"Failed to update Notion page: {response.status_code} - {response.text}")
            else:
                update_success_count += 1
                logger.info(f"Updated meal at date {date_str} in Notion")
                
        except Exception as e:
            logger.error(f"Error updating meal at index {idx} in Notion: {str(e)}")
    
    logger.info(f"Updated {update_success_count}/{update_count} meals in Notion")
    return update_success_count > 0

# Initialize database on startup
database.init_db()

# Initialize by loading page IDs
database.load_notion_page_ids()

@app.get("/api/meals")
async def get_meals():
    """Get all meals directly from the database without fetching from Notion.
    This is more efficient for normal page loads where we don't need fresh Notion data."""
    try:
        # Read meals directly from the database
        meals = database.read_meals()
        
        return {
            "status": "success", 
            "message": "Meals retrieved from database", 
            "meals": database.df_to_json(meals)
        }
        
    except Exception as e:
        logger.error(f"Failed to get meals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get meals: {str(e)}")

@app.put("/api/meal/{index}")
async def update_meal(index: int, meal: Dict[str, Any] = Body(...)):
    """Update a meal at the given index."""
    try:
        update_successful = database.update_changeset(index, meal)
        if not update_successful:
            raise HTTPException(status_code=404, detail="Meal not found")
        
        # Return the updated meal and the set of changed indices
        return {
            "status": "success",
            "message": "Meal updated",
            "changedIndices": list(database.get_changed_indices())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update meal: {str(e)}")

@app.post("/api/meals/save")
async def save_meals(meals: List[Dict[str, Any]] = Body(...)):
    """Save all meals to the database and update Notion."""
    try:
        # Convert to DataFrame for compatibility with existing code
        meals_df = pd.DataFrame(meals)
        
        # Convert Date column to datetime if it exists
        if 'Date' in meals_df.columns:
            meals_df['Date'] = pd.to_datetime(meals_df['Date'], errors='coerce')
        
        # Get the set of changed indices before saving
        changed_indices_set = database.get_changed_indices()
        
        # Update Notion with only the changed rows
        notion_updated = False
        if changed_indices_set:
            notion_updated = save_to_notion(meals_df, changed_indices_set)
        
        # Save to database
        db_save_successful = database.save_meals_to_db(meals_df)
        if not db_save_successful:
            raise HTTPException(status_code=500, detail="Failed to save meals to database")
        
        # Reset changed indices after saving
        database.save_changed_indices(set())
        
        return {
            "status": "success", 
            "message": "All meals saved successfully" + (" and updated in Notion" if notion_updated else ""),
            "notionUpdated": notion_updated
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save meals: {str(e)}")

@app.get("/api/meals/reload")
async def reload_meals():
    """Force reload meals from database, discarding any unsaved changes.
    Also attempts to fetch updated data from Notion if configured."""
    try:
        # Force reload by resetting changed indices
        database.save_changed_indices(set())
        
        # First try to fetch fresh data from Notion
        notion_fetch_success = fetch_from_notion()
        
        # Read the meals from the database
        meals = database.read_meals()
        
        return {
            "status": "success", 
            "message": "Meals reloaded successfully" + (" (updated from Notion)" if notion_fetch_success else " (from database)"), 
            "meals": database.df_to_json(meals),
            "notionUpdated": notion_fetch_success
        }
        
    except Exception as e:
        logger.error(f"Failed to reload meals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload meals: {str(e)}")

@app.get("/api/meals/changes")
async def get_changes():
    """Get the current changeset and changed indices."""
    try:
        return {
            "status": "success",
            "changedIndices": list(database.get_changed_indices())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get changes: {str(e)}")

@app.post("/api/meals/add-to-changeset")
async def add_to_changeset(meals: List[Dict[str, Any]] = Body(...)):
    """Add meals to the changeset."""
    try:
        # Not implemented for SQLite version - we're tracking changes in memory
        return {
            "status": "success",
            "message": "Changes tracked in memory"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add to changeset: {str(e)}")

@app.get("/api/recipes")
async def get_recipes():
    """Get all recipes"""
    try:
        recipes = database.read_recipes()
        return {"recipes": database.df_to_json(recipes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recipes: {str(e)}")

@app.post("/api/recipes")
async def create_recipe(recipe: Recipe):
    """Create a new recipe"""
    try:
        # Read existing recipes
        recipes_df = database.read_recipes()
        
        # Check if recipe already exists
        if not recipes_df.empty and recipe.Name in recipes_df['Name'].values:
            raise HTTPException(status_code=400, detail=f"Recipe '{recipe.Name}' already exists")
        
        # Add new recipe
        new_recipe = pd.DataFrame({
            "Name": [recipe.Name],
            "Tags": [recipe.Tags]
        })
        
        updated_recipes = pd.concat([recipes_df, new_recipe], ignore_index=True)
        database.save_recipes(updated_recipes)
        
        return {
            "status": "success",
            "message": f"Recipe '{recipe.Name}' created successfully"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create recipe: {str(e)}")

@app.delete("/api/recipes/{name}")
async def delete_recipe(name: str):
    """Delete a recipe by name"""
    try:
        # Read existing recipes
        recipes_df = database.read_recipes()
        
        # Check if recipe exists
        if recipes_df.empty or name not in recipes_df['Name'].values:
            raise HTTPException(status_code=404, detail=f"Recipe '{name}' not found")
        
        # Delete recipe
        updated_recipes = recipes_df[recipes_df['Name'] != name]
        database.save_recipes(updated_recipes)
        
        return {
            "status": "success",
            "message": f"Recipe '{name}' deleted successfully"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete recipe: {str(e)}")

@app.put("/api/recipes/{name}")
async def update_recipe(name: str, recipe: Recipe):
    """Update a recipe by name"""
    try:
        # Read existing recipes
        recipes_df = database.read_recipes()
        
        # Check if recipe exists
        if recipes_df.empty or name not in recipes_df['Name'].values:
            raise HTTPException(status_code=404, detail=f"Recipe '{name}' not found")
        
        # If name changed, check if new name already exists
        if name != recipe.Name and recipe.Name in recipes_df['Name'].values:
            raise HTTPException(status_code=400, detail=f"Recipe '{recipe.Name}' already exists")
        
        # Update recipe
        recipes_df.loc[recipes_df['Name'] == name, 'Name'] = recipe.Name
        recipes_df.loc[recipes_df['Name'] == recipe.Name, 'Tags'] = recipe.Tags
        
        database.save_recipes(recipes_df)
        
        return {
            "status": "success",
            "message": f"Recipe '{name}' updated successfully"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update recipe: {str(e)}")

@app.post("/api/recipes/populate")
async def populate_recipes():
    """Populate recipes from unique meals in the meal plan"""
    try:
        recipes = database.populate_recipes_from_meals()
        return {
            "status": "success",
            "message": "Recipes populated successfully",
            "recipes": database.df_to_json(recipes)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to populate recipes: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

