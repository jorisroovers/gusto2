import os
import pandas as pd
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
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
DATA_DIR = "/app/data/input"

# Model for meal data
class Meal(BaseModel):
    Name: Optional[str] = None
    Date: Optional[str] = None
    Tags: Optional[str] = None
    Notes: Optional[str] = None

# Global variable to store loaded meals
all_meals_df = None

def read_meals():
    global all_meals_df
    
    # If meals are already loaded, return the cached data
    if all_meals_df is not None:
        return all_meals_df
        
    # Otherwise, load from files
    all_files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    df_list = [pd.read_csv(file) for file in all_files]

    all_meals = pd.concat(df_list, ignore_index=True)
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
        
def df_to_json(df):
    if not df.empty:
        return df.to_dict(orient='records')
    return []

def save_meals_to_csv(meals_df):
    """Save the updated meals dataframe to CSV file."""
    global all_meals_df
    
    # Get the latest CSV file in the directory
    all_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    if not all_files:
        raise HTTPException(status_code=500, detail="No CSV file found to update")
    
    # Use the most recent file for updates
    latest_file = sorted(all_files)[-1]
    output_path = os.path.join(DATA_DIR, latest_file)
    
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
    
    meals_df.to_csv(output_path, index=False, columns=columns)
    
    # Reset the cached dataframe to force reloading
    all_meals_df = None
    
    return True

@app.get("/api/hello")
async def hello_world():
    meals = read_meals()
    return {"meals" : df_to_json(meals)}

@app.put("/api/meal/{index}")
async def update_meal(index: int, meal: Dict[str, Any] = Body(...)):
    """Update a meal at the given index."""
    try:
        # Read the current meals data
        meals_df = read_meals()
        
        if index < 0 or index >= len(meals_df):
            raise HTTPException(status_code=404, detail="Meal index out of range")
            
        # Update the meal at the specified index
        for key, value in meal.items():
            if key in meals_df.columns:
                meals_df.at[index, key] = value
        
        # Save the updated dataframe back to CSV
        save_meals_to_csv(meals_df)
        
        return {"status": "success", "message": "Meal updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update meal: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

