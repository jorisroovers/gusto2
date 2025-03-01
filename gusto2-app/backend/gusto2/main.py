import os
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you should specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def read_meals():
    data_dir = "/app/data/input"
    all_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.csv')]
    df_list = [pd.read_csv(file) for file in all_files]

    all_meals = pd.concat(df_list, ignore_index=True)
    all_meals = all_meals.replace({pd.NA: None, pd.NaT: None})
    # Drop Weekday column if it exists
    if 'Weekday' in all_meals.columns:
        all_meals = all_meals.drop('Weekday', axis=1)
    
    # Convert Date column to datetime if it exists
    if 'Date' in all_meals.columns:
        all_meals['Date'] = pd.to_datetime(all_meals['Date'], errors='coerce')
    
    return all_meals
        
def df_to_json(df):
    if not df.empty:
        return df.to_dict(orient='records')
    return []

@app.get("/api/hello")
async def hello_world():
    meals = read_meals()
    return {"meals" : df_to_json(meals)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

