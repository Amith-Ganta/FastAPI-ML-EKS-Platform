# API Documentation

## Overview

The Insurance Premium Category Predictor API is built with FastAPI and provides REST endpoints for predicting insurance premium categories based on user data.

## Base URL

**Local Development:** `http://localhost:8000`  
**Live demo:** `http://204.236.207.23:8000`

## Interactive Documentation

FastAPI automatically generates interactive API documentation:
- **Swagger UI**: `GET /docs`
- **ReDoc**: `GET /redoc`
- **OpenAPI Schema**: `GET /openapi.json`

## Endpoints

### 1. Readiness / Docs

**Endpoint:** `GET /docs`

FastAPI's interactive Swagger UI, also used as the readiness probe by Docker and
the CI smoke tests. `GET /redoc` and `GET /openapi.json` are available too.

### 2. Predict Premium Category

**Endpoint:** `POST /predict`

Predicts insurance premium category based on user demographics and health metrics.

#### Request Body

```json
{
  "age": 30,
  "weight": 65.0,
  "height": 1.75,
  "income_lpa": 10.0,
  "smoker": false,
  "city": "Mumbai",
  "occupation": "private_job"
}
```

#### Request Parameters

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `age` | integer | User's age | 0 < age < 120 |
| `weight` | float | Weight in kilograms | > 0 |
| `height` | float | Height in meters | 0 < height < 2.5 |
| `income_lpa` | float | Annual income in Lakh Per Annum | > 0 |
| `smoker` | boolean | Smoker status | true or false |
| `city` | string | City name | Any city string |
| `occupation` | string | Occupation type | See occupation options |

#### Occupation Options

- `retired`
- `freelancer`
- `student`
- `government_job`
- `business_owner`
- `unemployed`
- `private_job`

#### Response

**Status:** `200 OK`

```json
{
  "response": {
    "predicted_category": "Low",
    "confidence": 0.66,
    "class_probabilities": {
      "High": 0.01,
      "Low": 0.66,
      "Medium": 0.33
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `response.predicted_category` | string | Most likely premium category (`Low` / `Medium` / `High`) |
| `response.confidence` | float | Probability of the predicted category (0 to 1, rounded to 2 dp) |
| `response.class_probabilities` | object | Probability for every category, summing to ~1.0 |

#### Example Request

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 35,
    "weight": 70.0,
    "height": 1.80,
    "income_lpa": 15.0,
    "smoker": false,
    "city": "Bangalore",
    "occupation": "private_job"
  }'
```

#### Example Response

```json
{
  "response": {
    "predicted_category": "Medium",
    "confidence": 0.58,
    "class_probabilities": {
      "High": 0.12,
      "Low": 0.30,
      "Medium": 0.58
    }
  }
}
```

## Computed Fields

The API automatically calculates derived metrics from input data:

### BMI (Body Mass Index)
```
BMI = weight / (height²)
```

### Lifestyle Risk
- **High**: Smoker AND BMI > 30
- **Medium**: Smoker OR BMI > 27
- **Low**: Neither condition met

### Age Group
- **young**: age < 25
- **adult**: 25 ≤ age < 45
- **middle_aged**: 45 ≤ age < 60
- **senior**: age ≥ 60

### City Tier
- **Tier 1**: Major metros (Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune)
- **Tier 2**: Major cities (~50 Indian cities)
- **Tier 3**: All others

## Error Responses

### 422 Unprocessable Entity

Returned when validation fails:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "age"],
      "msg": "ensure this value is greater than 0",
      "input": -5
    }
  ]
}
```

## Rate Limiting

Currently no rate limiting is implemented. Subject to change in future versions.

## Authentication

No authentication is currently required. Future versions may require API keys.

## CORS

The API has CORS disabled by default. Configure in `backend/app.py` if needed:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Specify domains in production
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Version

Current API Version: **1.0**

## Support

For bugs, feature requests, or questions, please open an issue on GitHub.
