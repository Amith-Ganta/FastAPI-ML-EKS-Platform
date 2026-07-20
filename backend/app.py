"""
Insurance Premium Category Predictor — FastAPI service.

Exposes a single ML inference endpoint (`/predict`) plus lightweight liveness
probes (`/` and `/health`). The model is a scikit-learn pipeline that maps a
person's profile to an insurance premium category (Low / Medium / High) and the
service returns the predicted class together with a confidence score and the
full class-probability distribution.

This is the single source of truth behind the published image
`tweakster24/insurance-premium-api:latest`.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, computed_field
from typing import Literal, Annotated
import pickle
import pandas as pd
from pathlib import Path

# --------------------------------------------------------------------------- #
# Model loading
# --------------------------------------------------------------------------- #
model_path = Path(__file__).parent / 'model.pkl'
with open(model_path, 'rb') as f:
    model = pickle.load(f)

MODEL_VERSION = "1.0.0"

app = FastAPI(
    title="Insurance Premium Category Predictor",
    description="Predicts an insurance premium category (Low / Medium / High) "
                "from a user's demographic and lifestyle profile.",
    version=MODEL_VERSION,
)

# --------------------------------------------------------------------------- #
# Reference data for feature engineering
# --------------------------------------------------------------------------- #
tier_1_cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Pune"]
tier_2_cities = [
    "Jaipur", "Chandigarh", "Indore", "Lucknow", "Patna", "Ranchi", "Visakhapatnam", "Coimbatore",
    "Bhopal", "Nagpur", "Vadodara", "Surat", "Rajkot", "Jodhpur", "Raipur", "Amritsar", "Varanasi",
    "Agra", "Dehradun", "Mysore", "Jabalpur", "Guwahati", "Thiruvananthapuram", "Ludhiana", "Nashik",
    "Allahabad", "Udaipur", "Aurangabad", "Hubli", "Belgaum", "Salem", "Vijayawada", "Tiruchirappalli",
    "Bhavnagar", "Gwalior", "Dhanbad", "Bareilly", "Aligarh", "Gaya", "Kozhikode", "Warangal",
    "Kolhapur", "Bilaspur", "Jalandhar", "Noida", "Guntur", "Asansol", "Siliguri"
]


# --------------------------------------------------------------------------- #
# Request schema — Pydantic validation + derived features
# --------------------------------------------------------------------------- #
class UserInput(BaseModel):

    age: Annotated[int, Field(..., gt=0, lt=120, description='Age of the user')]
    weight: Annotated[float, Field(..., gt=0, description='Weight of the user in kg')]
    height: Annotated[float, Field(..., gt=0, lt=2.5, description='Height of the user in metres')]
    income_lpa: Annotated[float, Field(..., gt=0, description='Annual income of the user in LPA')]
    smoker: Annotated[bool, Field(..., description='Is the user a smoker')]
    city: Annotated[str, Field(..., description='The city the user belongs to')]
    occupation: Annotated[Literal['retired', 'freelancer', 'student', 'government_job',
       'business_owner', 'unemployed', 'private_job'], Field(..., description='Occupation of the user')]

    @computed_field
    @property
    def bmi(self) -> float:
        return self.weight / (self.height ** 2)

    @computed_field
    @property
    def lifestyle_risk(self) -> str:
        if self.smoker and self.bmi > 30:
            return "high"
        elif self.smoker or self.bmi > 27:
            return "medium"
        else:
            return "low"

    @computed_field
    @property
    def age_group(self) -> str:
        if self.age < 25:
            return "young"
        elif self.age < 45:
            return "adult"
        elif self.age < 60:
            return "middle_aged"
        return "senior"

    @computed_field
    @property
    def city_tier(self) -> int:
        if self.city in tier_1_cities:
            return 1
        elif self.city in tier_2_cities:
            return 2
        else:
            return 3


# --------------------------------------------------------------------------- #
# Liveness / readiness probes (used by Docker, CI smoke tests and load balancers)
# --------------------------------------------------------------------------- #
@app.get('/')
def root():
    return {"service": "insurance-premium-api", "status": "ok", "version": MODEL_VERSION}


@app.get('/health')
def health():
    return JSONResponse(status_code=200, content={"status": "healthy", "model_version": MODEL_VERSION})


# --------------------------------------------------------------------------- #
# Inference endpoint
# --------------------------------------------------------------------------- #
@app.post('/predict')
def predict_premium(data: UserInput):

    input_df = pd.DataFrame([{
        'bmi': data.bmi,
        'age_group': data.age_group,
        'lifestyle_risk': data.lifestyle_risk,
        'city_tier': data.city_tier,
        'income_lpa': data.income_lpa,
        'occupation': data.occupation
    }])

    predicted_category = model.predict(input_df)[0]
    probabilities = model.predict_proba(input_df)[0]

    class_probabilities = {
        str(cls): round(float(prob), 2)
        for cls, prob in zip(model.classes_, probabilities)
    }
    confidence = round(float(max(probabilities)), 2)

    return JSONResponse(status_code=200, content={
        "response": {
            "predicted_category": predicted_category,
            "confidence": confidence,
            "class_probabilities": class_probabilities,
        }
    })
