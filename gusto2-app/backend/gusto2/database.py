import os
import pandas as pd
from datetime import datetime
import json
from sqlalchemy import create_engine, Column, Integer, String, Date, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Path to the data directory - with fallback to a writable location
DEFAULT_DATA_DIR = "/app/data"
if not os.path.exists(DEFAULT_DATA_DIR) or not os.access(DEFAULT_DATA_DIR, os.W_OK):
    # Fallback to a directory we know is writable
    home_dir = os.path.expanduser("~")
    DATA_DIR = os.path.join(home_dir, ".gusto2")
else:
    DATA_DIR = DEFAULT_DATA_DIR

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Database setup
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'gusto2.db')}"

# Global variables
notion_page_ids = {}  # Map dates to Notion page IDs (in-memory cache)

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define SQLAlchemy models
class MealModel(Base):
    __tablename__ = "meals"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True)
    weekday = Column(String)
    name = Column(String, index=True)
    tags = Column(String)
    notes = Column(Text)
    notion_page_id = Column(String, index=True)

class RecipeModel(Base):
    __tablename__ = "recipes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    tags = Column(String)

class NotionPageIdModel(Base):
    __tablename__ = "notion_page_ids"
    
    id = Column(Integer, primary_key=True, index=True)
    date_str = Column(String, unique=True, index=True)
    page_id = Column(String, index=True)

class ChangedIndexModel(Base):
    __tablename__ = "changed_indices"
    
    id = Column(Integer, primary_key=True, index=True)
    index = Column(Integer, unique=True, index=True)

class IngredientModel(Base):
    __tablename__ = "ingredients"
    
    id = Column(Integer, primary_key=True, index=True)
    meal_name = Column(String, unique=True, index=True)
    ingredients_json = Column(Text)
    last_updated = Column(Date, default=datetime.now)

# Create tables if they don't exist
def init_db():
    try:
        # Only create tables if they don't exist, don't drop existing tables
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        raise

# Load Notion page IDs from database to in-memory cache
def load_notion_page_ids():
    global notion_page_ids
    try:
        with SessionLocal() as db:
            page_id_records = db.query(NotionPageIdModel).all()
            
            # Populate in-memory cache
            notion_page_ids = {record.date_str: record.page_id for record in page_id_records}
    except Exception as e:
        notion_page_ids = {}
    
    return notion_page_ids

# Save Notion page ID to database
def save_notion_page_id(date_str, page_id):
    try:
        with SessionLocal() as db:
            # Check if record exists
            existing = db.query(NotionPageIdModel).filter_by(date_str=date_str).first()
            
            if existing:
                # Update existing record
                existing.page_id = page_id
            else:
                # Create new record
                new_record = NotionPageIdModel(date_str=date_str, page_id=page_id)
                db.add(new_record)
            
            db.commit()
            
            # Update in-memory cache
            global notion_page_ids
            notion_page_ids[date_str] = page_id
            
        return True
    except Exception as e:
        return False

# Save all Notion page IDs to database
def save_notion_page_ids():
    if not notion_page_ids:
        return
    
    try:
        with SessionLocal() as db:
            # For each page ID in memory
            for date_str, page_id in notion_page_ids.items():
                # Check if record exists
                existing = db.query(NotionPageIdModel).filter_by(date_str=date_str).first()
                
                if existing:
                    # Update existing record
                    existing.page_id = page_id
                else:
                    # Create new record
                    new_record = NotionPageIdModel(date_str=date_str, page_id=page_id)
                    db.add(new_record)
            
            db.commit()
            
        return True
    except Exception as e:
        return False

# Get Notion page ID for a specific date
def get_notion_page_id(date_str):
    # First check in-memory cache
    if date_str in notion_page_ids:
        return notion_page_ids[date_str]
    
    # If not in cache, try to load from database
    try:
        with SessionLocal() as db:
            record = db.query(NotionPageIdModel).filter_by(date_str=date_str).first()
            if record:
                # Update in-memory cache and return
                notion_page_ids[date_str] = record.page_id
                return record.page_id
    except Exception as e:
        pass
    
    return None

def read_meals():
    """Read all meals from the database"""
    try:
        with SessionLocal() as db:
            meals = db.query(MealModel).order_by(MealModel.date).all()
        
        # Convert to pandas DataFrame for compatibility with existing code
        meals_data = []
        for meal in meals:
            meals_data.append({
                "Date": meal.date,
                "Weekday": meal.weekday,
                "Name": meal.name,
                "Tags": meal.tags,
                "Notes": meal.notes,
                "notion_page_id": meal.notion_page_id
            })
        
        # Create DataFrame
        if not meals_data:
            # Return empty dataframe with expected columns
            return pd.DataFrame(columns=["Date", "Weekday", "Name", "Tags", "Notes"])
        
        meals_df = pd.DataFrame(meals_data)
        
        # Replace None with NaN for pandas operations
        meals_df = meals_df.replace({None: pd.NA})
        
        # Drop notion_page_id column as it's not needed for the frontend
        if 'notion_page_id' in meals_df.columns:
            meals_df = meals_df.drop('notion_page_id', axis=1)
        
        return meals_df
    except Exception as e:
        # Return empty dataframe
        return pd.DataFrame(columns=["Date", "Weekday", "Name", "Tags", "Notes"])

def get_changed_indices():
    """Load the set of changed meal indices from the database"""
    try:
        with SessionLocal() as db:
            changed_indices_records = db.query(ChangedIndexModel).all()
            return {record.index for record in changed_indices_records}
    except Exception as e:
        return set()

def save_changed_indices(indices_set):
    """Save the set of changed meal indices to the database"""
    try:
        with SessionLocal() as db:
            # Delete all existing changed indices
            db.query(ChangedIndexModel).delete()
            
            # Add new indices
            for index in indices_set:
                db.add(ChangedIndexModel(index=index))
            
            db.commit()
            
        return True
    except Exception as e:
        return False

def df_to_json(df):
    """Convert DataFrame to JSON format suitable for API responses"""
    # Handle NaT/NaN values before converting to JSON
    df_copy = df.replace({pd.NA: None, pd.NaT: None})
    
    # Convert datetime columns to string format
    if 'Date' in df_copy.columns:
        df_copy['Date'] = df_copy['Date'].apply(
            lambda x: x.strftime('%Y/%m/%d') if pd.notna(x) and x is not None else None
        )
    
    # Convert to records format (list of dicts)
    return df_copy.to_dict('records')

def update_changeset(index, meal):
    """Update a single meal in the database"""
    try:
        with SessionLocal() as db:
            # Get all meals to find the one at the specified index
            meals = db.query(MealModel).order_by(MealModel.date).all()
            
            if index < 0 or index >= len(meals):
                return False
            
            # Get the meal to update
            db_meal = meals[index]
            
            # Update meal attributes
            if 'Name' in meal and meal['Name'] is not None:
                db_meal.name = meal['Name']
            if 'Tags' in meal and meal['Tags'] is not None:
                # Normalize tags to lowercase
                if meal['Tags']:
                    meal['Tags'] = ','.join([tag.strip().lower() for tag in meal['Tags'].split(',') if tag.strip()])
                db_meal.tags = meal['Tags']
            if 'Notes' in meal and meal['Notes'] is not None:
                db_meal.notes = meal['Notes']
            if 'Date' in meal and meal['Date'] is not None:
                try:
                    # Try to parse the date consistently
                    if isinstance(meal['Date'], str):
                        date_obj = pd.to_datetime(meal['Date'], format='%Y/%m/%d')
                    else:
                        date_obj = pd.to_datetime(meal['Date'])
                    db_meal.date = date_obj
                    db_meal.weekday = date_obj.strftime('%A')
                except Exception as e:
                    return False
            
            # Check if index already exists in changed_indices
            existing_index = db.query(ChangedIndexModel).filter_by(index=index).first()
            
            # Only add to changed_indices if it doesn't already exist
            if not existing_index:
                changed_index = ChangedIndexModel(index=index)
                db.add(changed_index)
            
            # Save changes
            db.commit()
            
        return True
    except Exception as e:
        return False

def read_recipes():
    """Read recipes from database"""
    try:
        with SessionLocal() as db:
            recipes = db.query(RecipeModel).order_by(RecipeModel.name).all()
        
        # Convert to pandas DataFrame for compatibility with existing code
        recipes_data = []
        for recipe in recipes:
            recipes_data.append({
                "Name": recipe.name,
                "Tags": recipe.tags
            })
        
        # Create DataFrame
        if not recipes_data:
            # Return empty dataframe with expected columns
            return pd.DataFrame(columns=["Name", "Tags"])
        
        recipes_df = pd.DataFrame(recipes_data)
        
        # Replace None with NaN for pandas operations
        recipes_df = recipes_df.replace({None: pd.NA})
        
        return recipes_df
    except Exception as e:
        # Return empty dataframe
        return pd.DataFrame(columns=["Name", "Tags"])

def save_recipes(df):
    """Save recipes to database"""
    try:
        with SessionLocal() as db:
            # For each recipe in the dataframe
            for _, row in df.iterrows():
                # Handle NA/NaN values by converting them to None
                name = row.get('Name') if pd.notna(row.get('Name')) else None
                tags = row.get('Tags') if pd.notna(row.get('Tags')) else None
                
                if not name:  # Skip if no name provided
                    continue
                
                # Check if recipe already exists
                existing_recipe = db.query(RecipeModel).filter_by(name=name).first()
                
                if existing_recipe:
                    # Update existing recipe
                    existing_recipe.tags = tags
                else:
                    # Create new recipe
                    recipe = RecipeModel(
                        name=name,
                        tags=tags
                    )
                    db.add(recipe)
            
            # Commit the transaction
            db.commit()
        
        return True
    except Exception as e:
        return False

def populate_recipes_from_meals():
    """Populate recipes database with unique meals from the meal plan"""
    meals = read_meals()
    existing_recipes = read_recipes()
    
    # Get unique meals with their tags
    unique_meals = meals[['Name', 'Tags']].dropna(subset=['Name']).drop_duplicates()
    
    # Create a dictionary of existing recipe names to their rows for faster lookup
    existing_recipe_dict = {}
    if not existing_recipes.empty:
        for _, row in existing_recipes.iterrows():
            if pd.notna(row.get('Name')):
                existing_recipe_dict[row.get('Name')] = row
    
    # Dictionary to track all recipes that need to be created or updated
    recipes_to_update = {}
    
    # Process each unique meal to either create or update a recipe
    for _, row in unique_meals.iterrows():
        name = row.get('Name')
        if not name:
            continue
            
        # Get tags and normalize to lowercase
        tags = row.get('Tags')
        if pd.notna(tags) and tags:
            # Split tags, trim whitespace, convert to lowercase, then rejoin
            tags = ','.join([tag.strip().lower() for tag in tags.split(',') if tag.strip()])
        
        # If recipe exists, we'll update it with new tags from meals
        # If multiple meals have the same name but different tags, the last one will be used
        recipes_to_update[name] = tags
    
    # Convert the tracked recipes to a DataFrame and save
    if recipes_to_update:
        recipes_df = pd.DataFrame({
            "Name": list(recipes_to_update.keys()),
            "Tags": list(recipes_to_update.values())
        })
        save_recipes(recipes_df)
    
    return read_recipes()

def save_meals_to_db(meals_df):
    """Save meals DataFrame to database"""
    try:
        with SessionLocal() as db:
            # Delete all existing meals
            db.query(MealModel).delete()
            db.commit()
            
            # Insert new meals
            for _, row in meals_df.iterrows():
                date_obj = None
                weekday = None
                date_str = None
                
                # Handle date conversion
                if 'Date' in row and pd.notna(row['Date']) and not pd.isna(row['Date']):
                    try:
                        # Try to parse the date - it might be a string or already a datetime
                        if isinstance(row['Date'], str):
                            date_obj = pd.to_datetime(row['Date'], format='%Y/%m/%d')
                        else:
                            date_obj = pd.to_datetime(row['Date'])
                            
                        weekday = date_obj.strftime('%A')
                        date_str = date_obj.strftime('%Y/%m/%d')
                    except Exception as e:
                        continue
                
                # Get notion page id if available
                notion_page_id = get_notion_page_id(date_str) if date_str else None
                
                # Handle NaN/NaT values for other fields
                name = row.get('Name') if pd.notna(row.get('Name')) else None
                tags = row.get('Tags') if pd.notna(row.get('Tags')) else None
                notes = row.get('Notes') if pd.notna(row.get('Notes')) else None
                
                meal = MealModel(
                    date=date_obj,
                    weekday=weekday,
                    name=name,
                    tags=tags,
                    notes=notes,
                    notion_page_id=notion_page_id
                )
                db.add(meal)
            
            # Commit the transaction
            db.commit()
        
        return True
    except Exception as e:
        return False