import os
import pandas as pd
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to the data directory
DATA_DIR = "/app/data"
MEALS_CSV = os.path.join(DATA_DIR, "meals.csv")
CHANGESET_FILE = os.path.join(DATA_DIR, "changeset.csv")
CHANGED_INDICES_FILE = os.path.join(DATA_DIR, "changed_indices.txt")

# Model for meal data
class Meal(BaseModel):
    Name: Optional[str] = None
    Date: Optional[str] = None
    Tags: Optional[str] = None
    Notes: Optional[str] = None

# Global variables to store loaded data
all_meals_df = None
changeset_df = None  # Store the changeset persistently
changed_indices = set()  # Track which meal indices have been modified

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
    """Save all meals from the changeset to the CSV file."""
    try:
        # Create a DataFrame from the received meals
        meals_df = pd.DataFrame(meals)
        
        # Convert Date column to datetime if it exists
        if 'Date' in meals_df.columns:
            meals_df['Date'] = pd.to_datetime(meals_df['Date'], errors='coerce')
        
        # Save to CSV
        save_meals_to_csv(meals_df)
        
        return {"status": "success", "message": "All meals saved successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save meals: {str(e)}")

@app.get("/api/meals/reload")
async def reload_meals():
    """Force reload meals from the CSV file, discarding any unsaved changes."""
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
                print(f"Error removing changeset file: {e}")
        
        # Remove the changed indices file if it exists
        if os.path.exists(CHANGED_INDICES_FILE):
            try:
                os.remove(CHANGED_INDICES_FILE)
            except Exception as e:
                print(f"Error removing changed indices file: {e}")
        
        # Read the meals from the CSV file
        meals = read_meals()
        
        return {"status": "success", "message": "Meals reloaded successfully", "meals": df_to_json(meals)}
        
    except Exception as e:
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

