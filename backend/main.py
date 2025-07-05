from fastapi import FastAPI
from .api import targets, science_planner

app = FastAPI()

app.include_router(targets.router)
app.include_router(science_planner.router)

@app.post("/workflow/run")
async def run_workflow():
    return {"message": "Workflow running"}

@app.get("/ligand/find")
async def find_ligand():
    return {"message": "Ligand found"}

@app.post("/dock/run")
async def run_docking():
    return {"message": "Docking running"}

@app.post("/simulate/run")
async def run_simulation():
    return {"message": "Simulation running"}

@app.post("/predict/admet")
async def predict_admet():
    return {"message": "ADMET predicted"}
