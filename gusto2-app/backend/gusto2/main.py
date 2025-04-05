import os
import pandas as pd
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
import requests
import json
from openai import AsyncOpenAI
import random
from datetime import datetime  # Removed unused timedelta

# Import from our database module
from gusto2 import database

# Store history of previously suggested recipes to avoid repetition
SUGGESTED_RECIPES_HISTORY = []

# Example recipes will be loaded from database, but if database is empty, use these fallback examples
FALLBACK_EXAMPLE_RECIPES = [
    {"name": "Mediterranean Quinoa Bowl", "tags": ["mediterranean", "vegetarian", "healthy", "lunch", "bowl"]},
    {"name": "Spicy Thai Basil Chicken", "tags": ["thai", "spicy", "chicken", "dinner", "quick"]},
    {"name": "Classic Beef Bourguignon", "tags": ["french", "beef", "stew", "dinner", "winter"]},
    {"name": "Crispy Falafel Wrap", "tags": ["middle-eastern", "vegetarian", "lunch", "wrap"]},
    {"name": "Japanese Miso Ramen", "tags": ["japanese", "soup", "noodles", "dinner", "umami"]}
]

# Import from our rules module
try:
    from gusto2.rules.rule_engine import default_rule_engine, RuleType
except ImportError as e:
    # Configure logging if not already configured
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.error(f"Failed to import rule_engine module: {str(e)}")
    # Create a dummy rule engine for graceful fallback
    class DummyRuleEngine:
        def validate_meal_plan(self, *args, **kwargs):
            return []
        def can_add_meal(self, *args, **kwargs):
            return {"can_add": True, "constraint_results": [], "requirement_results": []}
        def suggest_meals_for_date(self, *args, **kwargs):
            return []
    default_rule_engine = DummyRuleEngine()
    
    class RuleType:
        CONSTRAINT = "CONSTRAINT"
        REQUIREMENT = "REQUIREMENT"

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

# OpenAI configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4-turbo-preview")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")

# Initialize OpenAI client with optional base_url
openai_client_kwargs = {"api_key": OPENAI_API_KEY}
if OPENAI_BASE_URL:
    openai_client_kwargs["base_url"] = OPENAI_BASE_URL
openai_client = AsyncOpenAI(**openai_client_kwargs)

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

# Pydantic models for rules API
class MealSuggestionRequest(BaseModel):
    date: str
    count: Optional[int] = 3

class MealValidator(BaseModel):
    date: Optional[str] = None

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
                            
                            # Store the page ID in database
                            formatted_date = date_obj.strftime('%Y/%m/%d')
                            database.save_notion_page_id(formatted_date, page_id)
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
        # This is only called from the reload_meals endpoint when the user explicitly clicks the "Reload" button
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
            if pd.isna(meal_row.get('Date')) or pd.isnull(meal_row.get('Date')):
                logger.warning(f"No date for meal at index {idx}, skipping")
                continue
            
            # Handle date formatting
            try:
                if isinstance(meal_row['Date'], str):
                    date_obj = pd.to_datetime(meal_row['Date'], format='%Y/%m/%d')
                else:
                    date_obj = pd.to_datetime(meal_row['Date'])
                date_str = date_obj.strftime('%Y/%m/%d')
            except Exception as e:
                logger.error(f"Error parsing date for index {idx}: {e}")
                continue
            
            # Find Notion page ID for this date
            page_id = database.get_notion_page_id(date_str)
            if not page_id:
                logger.warning(f"No Notion page ID found for date {date_str}, skipping")
                continue
            
            # Prepare properties to update
            properties = {}
            
            # Update name if it exists and is not NaN
            if not pd.isna(meal_row.get('Name')):
                properties["Name"] = {
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": str(meal_row['Name'])
                            }
                        }
                    ]
                }
            
            # Update tags if they exist and are not NaN
            if not pd.isna(meal_row.get('Tags')):
                tags = [tag.strip() for tag in str(meal_row['Tags']).split(',') if tag.strip()]
                properties["Tags"] = {
                    "multi_select": [{"name": tag} for tag in tags]
                }
            
            # Update notes if they exist and are not NaN
            if not pd.isna(meal_row.get('Notes')):
                properties["Notes"] = {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": str(meal_row['Notes'])
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

# Initialize by loading page IDs from database
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
        
        # Convert Date column to datetime if it exists, ensuring consistent format
        if 'Date' in meals_df.columns:
            meals_df['Date'] = pd.to_datetime(meals_df['Date'], format='%Y/%m/%d', errors='coerce')
        
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
        logger.error(f"Failed to save meals: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save meals: {str(e)}")

@app.get("/api/meals/reload")
async def reload_meals():
    """Force reload meals from database, discarding any unsaved changes.
    Also attempts to fetch updated data from Notion if configured.
    Also reloads recipes based on the reloaded meals."""
    try:
        # Force reload by resetting changed indices
        database.save_changed_indices(set())
        
        # First try to fetch fresh data from Notion
        notion_fetch_success = fetch_from_notion()
        
        # Read the meals from the database
        meals = database.read_meals()
        
        # Reload recipes based on the newly loaded meals
        try:
            database.populate_recipes_from_meals()
            logger.info("Recipes reloaded based on updated meals.")
        except Exception as recipe_e:
            # Log the error but don't fail the whole request
            logger.error(f"Failed to reload recipes after reloading meals: {recipe_e}")

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

@app.get("/api/rules")
async def get_rules():
    """Get all meal planning rules"""
    try:
        rules = default_rule_engine.get_rules()
        return {
            "status": "success",
            "rules": [
                {
                    "name": rule.name,
                    "description": rule.description,
                    "type": rule.type.name,
                    "scope": rule.scope.name,
                    "enabled": rule.enabled,
                }
                for rule in rules
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get rules: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get rules: {str(e)}")

@app.post("/api/rules/validate")
async def validate_meal_plan(validator: MealValidator):
    """Validate a meal plan against rules"""
    try:
        # Get meals from database
        meals_df = database.read_meals()
        
        date = None
        if validator.date:
            try:
                date = datetime.strptime(validator.date, "%Y/%m/%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY/MM/DD")
        
        # Validate against rules
        validation_results = default_rule_engine.validate_meal_plan(meals_df, date)
        
        # Group results by rule type
        constraints = []
        requirements = []
        
        for result in validation_results:
            if result["rule_type"] == RuleType.CONSTRAINT.name:
                constraints.append(result)
            else:
                requirements.append(result)
                
        return {
            "status": "success",
            "constraints": constraints,
            "requirements": requirements,
            "all_constraints_met": all(r["is_valid"] for r in constraints),
            "all_requirements_met": all(r["is_valid"] for r in requirements),
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to validate meal plan: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to validate meal plan: {str(e)}")

@app.post("/api/rules/suggest-meals")
async def suggest_meals(suggestion_request: MealSuggestionRequest):
    """Get meal suggestions based on rules"""
    try:
        # Parse the date
        try:
            date = datetime.strptime(suggestion_request.date, "%Y/%m/%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY/MM/DD")
        
        # Get meals from database for context
        meals_df = database.read_meals()
        
        # Get available recipes
        recipes_df = database.read_recipes()
        
        if recipes_df.empty:
            raise HTTPException(status_code=404, detail="No recipes found")
        
        # Convert recipes to the format expected by the rule engine
        available_meals = []
        for _, recipe in recipes_df.iterrows():
            if pd.notna(recipe['Name']):
                meal = {
                    "name": recipe['Name'],
                    "tags": recipe['Tags'] if pd.notna(recipe['Tags']) else ""
                }
                available_meals.append(meal)
        
        # Get suggestions
        count = suggestion_request.count or 3
        suggestions = default_rule_engine.suggest_meals_for_date(
            date=date,
            available_meals=available_meals,
            meals_df=meals_df,
            count=count
        )
        
        # Format the response
        response_suggestions = []
        for suggestion in suggestions:
            response_suggestions.append({
                "meal": suggestion["meal"],
                "score": suggestion["requirement_score"],
                "reasons": [
                    result["reason"] 
                    for result in suggestion["validation_result"]["requirement_results"]
                    if "helps meet" in result["reason"]
                ]
            })
        
        return {
            "status": "success",
            "suggestions": response_suggestions,
            "date": suggestion_request.date
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to get meal suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get meal suggestions: {str(e)}")

@app.get("/api/suggest-recipe")
async def suggest_recipe():
    """Get a recipe suggestion using OpenAI"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    try:
        # Get 5 random example recipes for the prompt
        example_recipes = random.sample(FALLBACK_EXAMPLE_RECIPES, 5)
        
        # Create history context
        history_context = ""
        if SUGGESTED_RECIPES_HISTORY:
            history_context = "\n\nPreviously suggested recipes (DO NOT suggest these again):\n"
            history_context += json.dumps([r["name"] for r in SUGGESTED_RECIPES_HISTORY], indent=2)
        
        # Create a prompt that includes history for context
        system_prompt = """You are a cooking expert that suggests recipes. 
        You must respond with a raw JSON object (no markdown, no backticks, no formatting).
        The response must be a single JSON object with exactly this structure:
        {
            "name": "Recipe Name",
            "tags": ["tag1", "tag2", ...]
        }
        Do not include any explanation, markdown formatting, or additional text.
        The name should be descriptive and unique. Tags should include cuisine type, dietary info, etc."""
        
        user_prompt = f"""Generate a recipe suggestion as a raw JSON object.
        Make sure to suggest something different from these previously suggested recipes:{history_context}
        
        Remember to return ONLY a JSON object with 'name' and 'tags' fields.
        No markdown, no backticks, no explanation text.
        """

        logger.info("Calling OpenAI API with prompts:")
        logger.info(f"System prompt: {system_prompt}")
        logger.info(f"User prompt: {user_prompt}")
        
        # Call OpenAI API
        response = await openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=1.1,
            response_format={ "type": "json" },
            max_tokens=500
        )
        
        # Extract and clean up the suggestion
        suggestion = response.choices[0].message.content.strip().replace('```json', '').replace('```', '').strip()
        suggestion_data = json.loads(suggestion)
        
        # Generate a unique ID and add to history
        suggestion_id = f"suggestion-{random.randint(1000, 9999)}"
        SUGGESTED_RECIPES_HISTORY.append({
            "name": suggestion_data.get("name", ""),
            "tags": suggestion_data.get("tags", []),
            "id": suggestion_id
        })
        
        # Keep history limited to last 50 suggestions
        if len(SUGGESTED_RECIPES_HISTORY) > 50:
            SUGGESTED_RECIPES_HISTORY.pop(0)
        
        return {
            "recipe": {
                "name": suggestion_data.get("name", ""),
                "tags": suggestion_data.get("tags", []),
                "id": suggestion_id
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get recipe suggestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get recipe suggestion: {str(e)}")

@app.get("/api/meal/{index}/reload-from-notion")
async def reload_meal_from_notion(index: int):
    """Reload a single meal from Notion based on its index."""
    try:
        # First check if the index is valid
        meals_df = database.read_meals()
        if index < 0 or index >= len(meals_df):
            raise HTTPException(status_code=404, detail=f"Meal at index {index} not found")
        
        # Get the meal at this index
        meal_row = meals_df.iloc[index]
        
        # Skip if no date (we need it to find the corresponding Notion page)
        if pd.isna(meal_row.get('Date')) or pd.isnull(meal_row.get('Date')):
            raise HTTPException(status_code=400, detail=f"Meal at index {index} has no date, cannot reload from Notion")
        
        # Format the date for lookup
        try:
            if isinstance(meal_row['Date'], str):
                date_obj = pd.to_datetime(meal_row['Date'], format='%Y/%m/%d')
            else:
                date_obj = pd.to_datetime(meal_row['Date'])
            date_str = date_obj.strftime('%Y/%m/%d')
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing date for meal at index {index}: {str(e)}")
        
        # Find Notion page ID for this date
        page_id = database.get_notion_page_id(date_str)
        if not page_id:
            raise HTTPException(status_code=404, detail=f"No Notion page ID found for date {date_str}")
        
        # Set up headers for Notion API
        if not NOTION_API_TOKEN:
            raise HTTPException(status_code=500, detail="Notion API token not configured")
            
        headers = {
            "Authorization": f"Bearer {NOTION_API_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"  # Use the current Notion API version
        }
        
        # Fetch the page from Notion
        url = f"https://api.notion.com/v1/pages/{page_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to fetch from Notion API: {response.status_code} - {response.text}"
            )
        
        # Parse the response
        page_data = response.json()
        properties = page_data.get("properties", {})
        
        # Extract properties from Notion response
        updated_meal = {}
        
        # Extract name if exists
        if "Name" in properties:
            name_prop = properties["Name"]
            if name_prop["type"] == "title" and name_prop.get("title"):
                title_parts = [part.get("plain_text", "") for part in name_prop.get("title", [])]
                updated_meal["Name"] = " ".join(title_parts).strip()
            else:
                updated_meal["Name"] = ""  # Clear name if empty in Notion
        else:
            updated_meal["Name"] = ""
        
        # Extract tags if exists
        if "Tags" in properties:
            tags_prop = properties["Tags"]
            if tags_prop["type"] == "multi_select" and tags_prop.get("multi_select"):
                tags = [tag.get("name", "") for tag in tags_prop.get("multi_select", [])]
                updated_meal["Tags"] = ", ".join(tags)
            else:
                updated_meal["Tags"] = ""  # Clear tags if empty in Notion
        else:
            updated_meal["Tags"] = ""
        
        # Extract notes if exists
        if "Notes" in properties:
            notes_prop = properties["Notes"]
            if notes_prop["type"] == "rich_text" and notes_prop.get("rich_text"):
                notes_parts = [part.get("plain_text", "") for part in notes_prop.get("rich_text", [])]
                updated_meal["Notes"] = " ".join(notes_parts).strip()
            else:
                updated_meal["Notes"] = ""  # Clear notes if empty in Notion
        else:
            updated_meal["Notes"] = ""
        
        # Preserve the date field from our database
        updated_meal["Date"] = meal_row.get('Date')
        
        # Update the meal in our database
        update_successful = database.update_changeset(index, updated_meal)
        if not update_successful:
            raise HTTPException(status_code=500, detail="Failed to update meal in database")
        
        # Return the updated meal and the changed indices
        return {
            "status": "success",
            "message": f"Meal at date {date_str} reloaded from Notion",
            "meal": updated_meal,
            "changedIndices": list(database.get_changed_indices())
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to reload meal from Notion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reload meal from Notion: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

