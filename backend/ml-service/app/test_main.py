from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

# Create the FastAPI app instance - THIS MUST BE NAMED 'app'
app = FastAPI(title="ML Test Service")

class SimplePredictionRequest(BaseModel):
    data: str

@app.get("/")
def read_root():
    return {"message": "ML Service is running successfully!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "ML Prediction API"}

@app.post("/predict")
def predict(request: SimplePredictionRequest):
    return {"prediction": f"Received: {request.data}", "status": "success"}

# This part is only needed if running directly with python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)