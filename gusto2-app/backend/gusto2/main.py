import json
import logging
import random
from datetime import datetime  # Removed unused timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel
from supermarktconnector.ah import AHConnector

# Import from our database module
from gusto2 import database

# Import application settings
from gusto2.settings import settings

# Store history of previously suggested recipes to avoid repetition
SUGGESTED_RECIPES_HISTORY = []

# Example recipes will be loaded from database, but if database is empty, use these fallback examples
FALLBACK_EXAMPLE_RECIPES = [
    {"name": "Mediterranean Quinoa Bowl", "tags": ["mediterranean", "vegetarian", "healthy", "lunch", "bowl"]},
    {"name": "Spicy Thai Basil Chicken", "tags": ["thai", "spicy", "chicken", "dinner", "quick"]},
    {"name": "Classic Beef Bourguignon", "tags": ["french", "beef", "stew", "dinner", "winter"]},
    {"name": "Crispy Falafel Wrap", "tags": ["middle-eastern", "vegetarian", "lunch", "wrap"]},
    {"name": "Japanese Miso Ramen", "tags": ["japanese", "soup", "noodles", "dinner", "umami"]},
]

# Import from our rules module
try:
    from gusto2.rules.rule_engine import RuleType, default_rule_engine
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

# Initialize OpenAI client using settings
openai_client = AsyncOpenAI(**settings.get_openai_client_kwargs())


# Utility function for OpenAI API calls with JSON response
async def call_openai_with_json_response(system_prompt, user_prompt, temperature=0.7, max_tokens=500):
    """Generic function to call OpenAI API and get a JSON response"""
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    try:
        response = await openai_client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=temperature,
            response_format={"type": "json"},
            max_tokens=max_tokens,
        )

        content = response.choices[0].message.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()

        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to call OpenAI API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to call OpenAI API: {str(e)}")


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


# Albert Heijn product search models
class ProductSearchRequest(BaseModel):
    ingredient: str


class ProductSearchResult(BaseModel):
    products: list = []
    ingredient: str


def fetch_from_notion():
    """Fetch meal data from Notion database and save to database"""

    if not settings.notion_api_token or not settings.notion_mealplan_page_id:
        logger.warning("Notion API token or page ID not provided. Skipping Notion fetch.")
        return False

    try:
        # Set up headers for Notion API
        headers = {
            "Authorization": f"Bearer {settings.notion_api_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",  # Use the current Notion API version
        }

        # Query the database using Notion's REST API
        logger.info(f"Fetching meals from Notion database: {settings.notion_mealplan_page_id}")

        # API endpoint for querying a database
        url = f"https://api.notion.com/v1/databases/{settings.notion_mealplan_page_id}/query"

        # Collect all pages with pagination
        has_more = True
        start_cursor = None
        all_results = []

        # Reset the page IDs mapping
        database.notion_page_ids = {}

        while has_more:
            # Prepare query with sort by date
            query_data = {"sorts": [{"property": "Date", "direction": "ascending"}]}

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

        with database.SessionLocal() as db:
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
                            try:
                                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                                meal["date"] = date_obj
                                meal["weekday"] = date_obj.strftime("%A")
                                formatted_date = date_obj.strftime("%Y/%m/%d")
                                database.save_notion_page_id(formatted_date, page_id)
                            except ValueError:
                                meal["date"] = None
                                meal["weekday"] = None

                # Extract name and tags, and ensure recipe exists
                recipe_name = None
                recipe_tags = None
                if "Name" in properties:
                    name_prop = properties["Name"]
                    if name_prop["type"] == "title" and name_prop.get("title"):
                        title_parts = [part.get("plain_text", "") for part in name_prop.get("title", [])]
                        recipe_name = " ".join(title_parts).strip()
                if "Tags" in properties:
                    tags_prop = properties["Tags"]
                    if tags_prop["type"] == "multi_select" and tags_prop.get("multi_select"):
                        tags = [tag.get("name", "") for tag in tags_prop.get("multi_select", [])]
                        recipe_tags = ", ".join(tags)

                recipe = None
                if recipe_name:
                    recipe = db.query(database.RecipeModel).filter_by(name=recipe_name).first()
                    if not recipe:
                        recipe = database.RecipeModel(name=recipe_name, tags=recipe_tags)
                        db.add(recipe)
                        db.commit()
                    elif recipe_tags is not None:
                        recipe.tags = recipe_tags
                        db.commit()
                    meal["recipe_id"] = recipe.id
                else:
                    meal["recipe_id"] = None

                # Extract notes if exists
                if "Notes" in properties:
                    notes_prop = properties["Notes"]
                    if notes_prop["type"] == "rich_text" and notes_prop.get("rich_text"):
                        notes_parts = [part.get("plain_text", "") for part in notes_prop.get("rich_text", [])]
                        meal["notes"] = " ".join(notes_parts).strip()

                # Only add meal if recipe_id is not None
                if meal.get("recipe_id") is not None:
                    meals_data.append(meal)
                else:
                    logger.warning(f"Skipping meal for Notion page {page_id} because no valid recipe name was found.")

            if not meals_data:
                logger.warning("No meal data found in Notion database")
                return False

            # Clear existing meals from the database and insert new data from Notion
            db.query(database.MealModel).delete()
            db.commit()
            for meal_data in meals_data:
                meal_obj = database.MealModel(**meal_data)
                db.add(meal_obj)
            db.commit()

        logger.info(f"Successfully saved {len(meals_data)} meals from Notion to database")
        return True

    except Exception as e:
        logger.error(f"Failed to fetch meal data from Notion: {str(e)}")
        return False


def save_to_notion(meals_df, changed_indices_set):
    """Save changed meal rows back to Notion"""
    if not settings.notion_api_token:
        logger.warning("Notion API token not provided. Skipping Notion update.")
        return False

    # Set up headers for Notion API
    headers = {
        "Authorization": f"Bearer {settings.notion_api_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",  # Use the current Notion API version
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
            if pd.isna(meal_row.get("Date")) or pd.isnull(meal_row.get("Date")):
                logger.warning(f"No date for meal at index {idx}, skipping")
                continue

            # Handle date formatting
            try:
                if isinstance(meal_row["Date"], str):
                    date_obj = pd.to_datetime(meal_row["Date"], format="%Y/%m/%d")
                else:
                    date_obj = pd.to_datetime(meal_row["Date"])
                date_str = date_obj.strftime("%Y/%m/%d")
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
            if not pd.isna(meal_row.get("Name")):
                properties["Name"] = {"title": [{"type": "text", "text": {"content": str(meal_row["Name"])}}]}

            # Update tags if they exist and are not NaN
            if not pd.isna(meal_row.get("Tags")):
                tags = [tag.strip() for tag in str(meal_row["Tags"]).split(",") if tag.strip()]
                properties["Tags"] = {"multi_select": [{"name": tag} for tag in tags]}

            # Update notes if they exist and are not NaN
            if not pd.isna(meal_row.get("Notes")):
                properties["Notes"] = {"rich_text": [{"type": "text", "text": {"content": str(meal_row["Notes"])}}]}

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

# Initialize Albert Heijn connector
ah_connector = AHConnector()

# Cache for Albert Heijn product search results
ah_product_cache = {}


@app.get("/api/meals")
async def get_meals():
    """Get all meals directly from the database without fetching from Notion.
    This is more efficient for normal page loads where we don't need fresh Notion data."""
    try:
        # Read meals directly from the database
        meals = database.read_meals()

        return {"status": "success", "message": "Meals retrieved from database", "meals": database.df_to_json(meals)}

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
        return {"status": "success", "message": "Meal updated", "changedIndices": list(database.get_changed_indices())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update meal: {str(e)}")


@app.post("/api/meals/save")
async def save_meals(meals: List[Dict[str, Any]] = Body(...)):
    """Save all meals to the database and update Notion."""
    try:
        # Convert to DataFrame for compatibility with existing code
        meals_df = pd.DataFrame(meals)

        # Convert Date column to datetime if it exists, ensuring consistent format
        if "Date" in meals_df.columns:
            meals_df["Date"] = pd.to_datetime(meals_df["Date"], format="%Y/%m/%d", errors="coerce")

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
            "notionUpdated": notion_updated,
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
            "message": "Meals reloaded successfully"
            + (" (updated from Notion)" if notion_fetch_success else " (from database)"),
            "meals": database.df_to_json(meals),
            "notionUpdated": notion_fetch_success,
        }

    except Exception as e:
        logger.error(f"Failed to reload meals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reload meals: {str(e)}")


@app.get("/api/meals/changes")
async def get_changes():
    """Get the current changeset and changed indices."""
    try:
        return {"status": "success", "changedIndices": list(database.get_changed_indices())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get changes: {str(e)}")


@app.post("/api/meals/add-to-changeset")
async def add_to_changeset(meals: List[Dict[str, Any]] = Body(...)):
    """Add meals to the changeset."""
    try:
        # Not implemented for SQLite version - we're tracking changes in memory
        return {"status": "success", "message": "Changes tracked in memory"}
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
        if not recipes_df.empty and recipe.Name in recipes_df["Name"].values:
            raise HTTPException(status_code=400, detail=f"Recipe '{recipe.Name}' already exists")

        # Add new recipe
        new_recipe = pd.DataFrame({"Name": [recipe.Name], "Tags": [recipe.Tags]})

        updated_recipes = pd.concat([recipes_df, new_recipe], ignore_index=True)
        database.save_recipes(updated_recipes)

        return {"status": "success", "message": f"Recipe '{recipe.Name}' created successfully"}
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
        if recipes_df.empty or name not in recipes_df["Name"].values:
            raise HTTPException(status_code=404, detail=f"Recipe '{name}' not found")

        # Delete recipe
        updated_recipes = recipes_df[recipes_df["Name"] != name]
        database.save_recipes(updated_recipes)

        return {"status": "success", "message": f"Recipe '{name}' deleted successfully"}
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
        if recipes_df.empty or name not in recipes_df["Name"].values:
            raise HTTPException(status_code=404, detail=f"Recipe '{name}' not found")

        # If name changed, check if new name already exists
        if name != recipe.Name and recipe.Name in recipes_df["Name"].values:
            raise HTTPException(status_code=400, detail=f"Recipe '{recipe.Name}' already exists")

        # Update recipe
        recipes_df.loc[recipes_df["Name"] == name, "Name"] = recipe.Name
        recipes_df.loc[recipes_df["Name"] == recipe.Name, "Tags"] = recipe.Tags

        database.save_recipes(recipes_df)

        return {"status": "success", "message": f"Recipe '{name}' updated successfully"}
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
            "recipes": database.df_to_json(recipes),
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
            ],
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
            if pd.notna(recipe["Name"]):
                meal = {"name": recipe["Name"], "tags": recipe["Tags"] if pd.notna(recipe["Tags"]) else ""}
                available_meals.append(meal)

        # Get suggestions
        count = suggestion_request.count or 3
        suggestions = default_rule_engine.suggest_meals_for_date(
            date=date, available_meals=available_meals, meals_df=meals_df, count=count
        )

        # Format the response
        response_suggestions = []
        for suggestion in suggestions:
            response_suggestions.append(
                {
                    "meal": suggestion["meal"],
                    "score": suggestion["requirement_score"],
                    "reasons": [
                        result["reason"]
                        for result in suggestion["validation_result"]["requirement_results"]
                        if "helps meet" in result["reason"]
                    ],
                }
            )

        return {"status": "success", "suggestions": response_suggestions, "date": suggestion_request.date}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to get meal suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get meal suggestions: {str(e)}")


@app.get("/api/suggest-recipe")
async def suggest_recipe():
    """Get a recipe suggestion using OpenAI"""
    if not settings.openai_api_key:
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
            model=settings.openai_model,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=1.1,
            response_format={"type": "json"},
            max_tokens=500,
        )

        # Extract and clean up the suggestion
        suggestion = response.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
        suggestion_data = json.loads(suggestion)

        # Generate a unique ID and add to history
        suggestion_id = f"suggestion-{random.randint(1000, 9999)}"
        SUGGESTED_RECIPES_HISTORY.append(
            {"name": suggestion_data.get("name", ""), "tags": suggestion_data.get("tags", []), "id": suggestion_id}
        )

        # Keep history limited to last 50 suggestions
        if len(SUGGESTED_RECIPES_HISTORY) > 50:
            SUGGESTED_RECIPES_HISTORY.pop(0)

        return {
            "recipe": {
                "name": suggestion_data.get("name", ""),
                "tags": suggestion_data.get("tags", []),
                "id": suggestion_id,
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
        if pd.isna(meal_row.get("Date")) or pd.isnull(meal_row.get("Date")):
            raise HTTPException(status_code=400, detail=f"Meal at index {index} has no date, cannot reload from Notion")

        # Format the date for lookup
        try:
            if isinstance(meal_row["Date"], str):
                date_obj = pd.to_datetime(meal_row["Date"], format="%Y/%m/%d")
            else:
                date_obj = pd.to_datetime(meal_row["Date"])
            date_str = date_obj.strftime("%Y/%m/%d")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing date for meal at index {index}: {str(e)}")

        # Find Notion page ID for this date
        page_id = database.get_notion_page_id(date_str)
        if not page_id:
            raise HTTPException(status_code=404, detail=f"No Notion page ID found for date {date_str}")

        # Set up headers for Notion API
        if not settings.notion_api_token:
            raise HTTPException(status_code=500, detail="Notion API token not configured")

        headers = {
            "Authorization": f"Bearer {settings.notion_api_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",  # Use the current Notion API version
        }

        # Fetch the page from Notion
        url = f"https://api.notion.com/v1/pages/{page_id}"
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch from Notion API: {response.status_code} - {response.text}"
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
        updated_meal["Date"] = meal_row.get("Date")

        # Update the meal in our database
        update_successful = database.update_changeset(index, updated_meal)
        if not update_successful:
            raise HTTPException(status_code=500, detail="Failed to update meal in database")

        # Return the updated meal and the changed indices
        return {
            "status": "success",
            "message": f"Meal at date {date_str} reloaded from Notion",
            "meal": updated_meal,
            "changedIndices": list(database.get_changed_indices()),
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to reload meal from Notion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reload meal from Notion: {str(e)}")


@app.get("/api/meal/{meal_name}/ingredients")
async def get_meal_ingredients(meal_name: str):
    """Get ingredients for a specific meal using OpenAI API"""
    try:
        # Check if we already have ingredients cached for this meal
        with database.SessionLocal() as db:
            ingredient_record = (
                db.query(database.IngredientModel).filter(database.IngredientModel.meal_name == meal_name).first()
            )

            if ingredient_record:
                logger.info(f"Using cached ingredients for {meal_name}")
                return {"status": "success", "ingredients": json.loads(ingredient_record.ingredients_json)}

        # Create prompt for OpenAI
        system_prompt = """You are a cooking expert that provides ingredients for recipes.
        You must respond with a raw JSON array of ingredients (no markdown, no backticks, no formatting).
        The response must be a list of strings, each representing an ingredient.
        
        Follow these rules:
        1. Only include ingredients available at the Dutch Albert Heijn supermarket
        2. Do not include common base ingredients like salt, pepper, oil, etc.
        3. Do not include amounts, only the ingredients themselves
        4. Keep the list concise and focused on main ingredients
        5. Return ONLY a JSON array of strings, no other text
        """

        user_prompt = f"""Provide a list of ingredients for the recipe: {meal_name}
        
        Remember:
        - Ingredients should be available at Albert Heijn in the Netherlands
        - Do NOT include common ingredients like salt, pepper, oil
        - Do NOT include amounts
        - ONLY return a JSON array of strings
        """

        logger.info(f"Calling OpenAI API to get ingredients for {meal_name}")

        # Call OpenAI API using the utility function
        ingredients = await call_openai_with_json_response(system_prompt=system_prompt, user_prompt=user_prompt)

        # Store in database for future use
        with database.SessionLocal() as db:
            # Check if we already have a record
            existing = (
                db.query(database.IngredientModel).filter(database.IngredientModel.meal_name == meal_name).first()
            )

            if existing:
                # Update existing record
                existing.ingredients_json = json.dumps(ingredients)
            else:
                # Create new record
                new_ingredient = database.IngredientModel(meal_name=meal_name, ingredients_json=json.dumps(ingredients))
                db.add(new_ingredient)

            db.commit()

        return {"status": "success", "ingredients": ingredients}

    except Exception as e:
        logger.error(f"Failed to get ingredients for {meal_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get ingredients: {str(e)}")


@app.get("/api/ingredients/{ingredient}/products")
async def search_ah_products(ingredient: str):
    """Search for products at Albert Heijn based on an ingredient name"""
    try:
        # Check cache first
        if ingredient in ah_product_cache:
            logger.info(f"Using cached product results for {ingredient}")
            return ah_product_cache[ingredient]

        logger.info(f"Searching Albert Heijn for products matching: {ingredient}")

        # Clean up the ingredient name for better search results
        clean_ingredient = ingredient.strip().lower()

        # Use AH connector to search for products
        raw_products = ah_connector.search_products(clean_ingredient)

        # Process and filter the results
        processed_results = []
        product_limit = 10
        products_count = 0

        # Handle different response formats from the supermarktconnector API
        if isinstance(raw_products, dict):
            logger.info(f"Processing dictionary response for {ingredient}")
            # If it's a dictionary, extract the products list which is often in 'cards' or 'products'
            products_list = []
            # Check common keys where products might be stored
            for key in ["cards", "products", "items", "results"]:
                if key in raw_products and isinstance(raw_products[key], list):
                    products_list = raw_products[key]
                    break

            # If we found a list in the dictionary, process it
            if products_list:
                logger.info(f"Found {len(products_list)} products in dictionary under key")
                for product in products_list:
                    if products_count >= product_limit:
                        break

                    # Extract product details safely
                    try:
                        if not isinstance(product, dict):
                            continue

                        # For dictionary responses, products might be nested under 'product'
                        actual_product = product.get("product", product)
                        if not isinstance(actual_product, dict):
                            continue

                        processed_product = extract_product_data(actual_product)
                        if processed_product:
                            processed_results.append(processed_product)
                            products_count += 1
                    except Exception as e:
                        logger.warning(f"Error processing dictionary product: {str(e)}")
                        continue
        elif isinstance(raw_products, list):
            logger.info(f"Processing list response with {len(raw_products)} products for {ingredient}")
            # If it's a list, process each product directly
            for product in raw_products:
                if products_count >= product_limit:
                    break

                try:
                    if not isinstance(product, dict):
                        logger.warning(f"Skipping non-dict product: {type(product)}")
                        continue

                    processed_product = extract_product_data(product)
                    if processed_product:
                        processed_results.append(processed_product)
                        products_count += 1
                except Exception as e:
                    logger.warning(f"Error processing list product: {str(e)}")
                    continue
        else:
            logger.warning(f"Unexpected products type: {type(raw_products)}")

        # Cache the results
        result = {"status": "success", "products": processed_results, "ingredient": ingredient}
        ah_product_cache[ingredient] = result

        return result
    except Exception as e:
        logger.error(f"Failed to search Albert Heijn products for {ingredient}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search for products: {str(e)}")


def extract_product_data(product):
    """Extract product data safely from various product formats"""
    try:
        # Skip products without an ID
        product_id = str(product.get("webshopId", product.get("id", "")))
        if not product_id:
            return None

        # Extract product title
        product_name = product.get("title", product.get("name", "Unknown Product"))

        # Extract price data safely
        price = 0
        price_data = product.get("priceBeforeBonus", product.get("price", {}))
        if isinstance(price_data, dict):
            price = price_data.get("amount", price_data.get("value", 0))
        elif isinstance(price_data, (int, float)):
            price = price_data

        # Extract first image URL safely
        image_url = ""
        images = product.get("images", product.get("image", []))
        if isinstance(images, list) and len(images) > 0:
            if isinstance(images[0], dict):
                image_url = images[0].get("url", images[0].get("src", ""))
            elif isinstance(images[0], str):
                image_url = images[0]
        elif isinstance(images, dict):
            image_url = images.get("url", images.get("src", ""))
        elif isinstance(images, str):
            image_url = images

        # Check for bonus safely
        has_bonus = False
        discount = product.get("discount", product.get("bonus", {}))
        if isinstance(discount, dict):
            has_bonus = discount.get("bonusType") is not None or discount.get("isBonus", False)
        elif isinstance(discount, bool):
            has_bonus = discount

        # Get unit price safely
        unit_price = product.get("unitPriceDescription", product.get("unitPrice", ""))

        # Create a simplified product object with only the data we need
        return {
            "id": product_id,
            "name": product_name,
            "price": price,
            "unit_price": unit_price,
            "image_url": image_url,
            "url": f"https://www.ah.nl/producten/product/{product_id}",
            "bonus": has_bonus,
        }
    except Exception as e:
        logger.warning(f"Error extracting product data: {str(e)}")
        return None


@app.get("/api/meal/{meal_name}/regenerate-ingredients")
async def regenerate_meal_ingredients(meal_name: str):
    """Force the regeneration of ingredients for a specific meal using OpenAI API, ignoring any cached values."""

    try:
        logger.info(f"Regenerating ingredients for {meal_name} using OpenAI")

        # Create prompt for OpenAI
        system_prompt = """You are a cooking expert that provides ingredients for recipes.
        You must respond with a raw JSON array of ingredients (no markdown, no backticks, no formatting).
        The response must be a list of strings, each representing an ingredient.
        
        Follow these rules:
        1. Only include ingredients available at the Dutch Albert Heijn supermarket
        2. Do not include common base ingredients like salt, pepper, oil, etc.
        3. Do not include amounts, only the ingredients themselves
        4. Keep the list concise and focused on main ingredients
        5. Return ONLY a JSON array of strings, no other text
        """

        user_prompt = f"""Provide a list of ingredients for the recipe: {meal_name}
        
        Remember:
        - Ingredients should be available at Albert Heijn in the Netherlands
        - Do NOT include common ingredients like salt, pepper, oil
        - Do NOT include amounts
        - ONLY return a JSON array of strings
        """

        # Call OpenAI API using the utility function
        ingredients = await call_openai_with_json_response(system_prompt=system_prompt, user_prompt=user_prompt)

        # Update in database for future use
        with database.SessionLocal() as db:
            # Check if we already have a record
            existing = (
                db.query(database.IngredientModel).filter(database.IngredientModel.meal_name == meal_name).first()
            )

            if existing:
                # Update existing record
                existing.ingredients_json = json.dumps(ingredients)
                existing.last_updated = datetime.now()
            else:
                # Create new record
                new_ingredient = database.IngredientModel(meal_name=meal_name, ingredients_json=json.dumps(ingredients))
                db.add(new_ingredient)

            db.commit()

        return {"status": "success", "ingredients": ingredients}

    except Exception as e:
        logger.error(f"Failed to regenerate ingredients for {meal_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate ingredients: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
