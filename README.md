# ChurnAI — Predict. Understand. Retain.

<p align="center">
  <strong>AI-Powered Customer Churn Prediction & Retention Intelligence Platform</strong>
</p>

<p align="center">
  Predict customer churn, understand why customers are at risk, and turn machine-learning predictions into actionable business insights.
</p>

<p align="center">
  🌐 <a href="https://khanova.tech">Live Application</a> &nbsp;•&nbsp;
  💻 <a href="https://github.com/bahawal-khan/churn-ai">GitHub Repository</a>
</p>

---

## 📌 Overview

**ChurnAI** is an end-to-end AI-powered customer churn prediction and retention intelligence platform.

The system helps organizations identify customers who are likely to leave, understand the factors contributing to their churn risk, and analyze customer behavior through an interactive web application.

Instead of building only a machine-learning notebook, this project was developed as a complete production-style application covering:

**Data → Feature Engineering → Machine Learning → Explainable AI → REST API → Database → Frontend → Deployment**

---

## 🚀 Live Application

### 🌐 https://khanova.tech

ChurnAI is deployed on a Linux VPS with:

* HTTPS / SSL
* Nginx reverse proxy
* Next.js frontend
* Flask REST API
* Gunicorn
* Database integration
* Production ML model
* SHAP explainability
* Authentication
* Session management
* systemd services

---

# ✨ Key Features

## 🎯 Customer Churn Prediction

Predict the probability that a customer is likely to churn using the production Random Forest model.

The system returns:

* Churn probability
* Predicted class
* Risk level
* Decision threshold
* Model information
* Prediction ID
* Explainability information

---

## 👤 Single Customer Prediction

Users can enter the details of an individual customer and receive an instant churn prediction.

The prediction includes:

* Probability of churn
* High / medium / low risk classification
* Model decision threshold
* Top factors influencing the prediction
* SHAP-based explanation

---

## 📊 Batch Prediction

Businesses can upload customer data through CSV files and generate predictions for multiple customers.

The batch system:

1. Validates the uploaded file
2. Matches columns against the model schema
3. Performs data-quality validation
4. Stores the uploaded dataset
5. Generates predictions
6. Persists prediction results
7. Allows prediction results to be downloaded as CSV

---

## 🔍 Explainable AI

ChurnAI uses **SHAP (SHapley Additive exPlanations)** to explain individual model predictions.

Instead of only saying:

> "This customer is likely to churn."

the system can also explain:

> "These features contributed most strongly to the predicted churn risk."

The API provides:

* Base value
* Model output
* Feature-level SHAP values
* Top contributing factors
* Direction of influence
* Additivity check

**Important:** SHAP explains patterns learned by the model. It identifies model relationships and correlations, not proven causation.

---

## 📈 Analytics Dashboard

The platform provides analytical views for understanding customer churn patterns.

Analytics include:

* Overall dashboard
* Risk distribution
* Churn trends
* Top churn drivers
* Customer segments
* Prediction summaries

---

## 🔐 Authentication

ChurnAI includes an authentication system with:

* User registration
* Login
* Logout
* Session management
* Password validation
* Forgot-password workflow
* Password reset
* Organization-based access

---

## 📁 Dataset Management

Organizations can upload and manage customer datasets through the application.

The backend performs:

* CSV validation
* Schema matching
* Data-quality checks
* Customer record creation
* Dataset persistence

---

## 📑 Reports

The system provides report-generation endpoints for customer and prediction summaries.

---

# 🧠 Machine Learning

## Original Project Direction

The original plan for ChurnAI was to build the production churn prediction system using an **Artificial Neural Network (ANN)**.

The goal was to demonstrate a neural-network-based solution for customer churn prediction.

However, rather than selecting ANN simply because it was the original architecture, several machine-learning models were trained and evaluated using the same development pipeline.

The evaluated models were:

* Logistic Regression
* Random Forest
* Gradient Boosting
* Artificial Neural Network (ANN)

The ANN performed well and remained a strong candidate.

However, the Random Forest achieved slightly better validation performance, particularly in the metrics that were important for the churn problem.

Therefore, the final production model was selected based on **actual evaluation results**, not simply model complexity.

> **The best production model is not necessarily the most complex model. It is the model that performs best for the specific problem and evaluation criteria.**

---

# 🤖 Model Selection

The models were compared using metrics appropriate for an imbalanced churn prediction problem.

### Validation Results

| Model                     | Validation PR-AUC | Observation                       |
| ------------------------- | ----------------: | --------------------------------- |
| Logistic Regression       |            ~0.578 | Strong baseline                   |
| Gradient Boosting         |            ~0.580 | Competitive                       |
| Artificial Neural Network |        **0.5847** | Strong neural-network alternative |
| **Random Forest**         |        **0.5855** | **Best validation performance**   |

Random Forest achieved the highest validation PR-AUC and stronger recall among the evaluated models.

Therefore:

### 🏆 Final Production Model: Random Forest

The ANN implementation is still included in the project as an evaluated alternative.

This model-selection process demonstrates a practical ML workflow:

```text
Initial ANN Direction
        ↓
Train Multiple Models
        ↓
Evaluate Validation Performance
        ↓
Compare PR-AUC / Recall / F1
        ↓
Select Best Candidate
        ↓
Evaluate on Unseen Test Data
        ↓
Deploy Production Model
```

---

# 🏆 Production Model

### Random Forest — `random_forest_v1`

The final production model achieved the following results on the unseen test set:

| Metric    |      Score |
| --------- | ---------: |
| Accuracy  | **65.85%** |
| Precision | **46.54%** |
| Recall    | **82.00%** |
| F1 Score  | **59.38%** |
| ROC-AUC   | **0.7777** |
| PR-AUC    | **0.5930** |

---

# 🎚️ Decision Threshold

The classification threshold was not blindly set to `0.50`.

Instead, the threshold was selected using the validation dataset by maximizing F1 score.

### Production Threshold

```text
0.37
```

This allows the system to identify more potential churners, which is useful because failing to identify a customer who is likely to churn can be more costly than contacting a customer who ultimately stays.

The test set remained completely separate from threshold selection to avoid data leakage.

---

# 🔍 SHAP Explainability

For every prediction, ChurnAI can provide feature-level explanations.

For example, a prediction may look like:

```json
{
  "algorithm": "random_forest",
  "churn_probability": 0.863787,
  "customer_id": "TEST-001",
  "decision_threshold": 0.37,
  "predicted_class": 1,
  "risk_level": "high",
  "model_id": "random_forest_v1"
}
```

The system can then provide the most influential factors behind the prediction.

Example factors can include:

* Contract type
* Tenure
* Payment method
* Monthly charges
* Technical support
* Internet service
* Payment risk
* Contract risk
* Service/add-on behavior

---

# 📊 Input Features

The production model uses customer demographic, service, contract, and billing information.

## Customer Information

* Gender
* Senior Citizen
* Partner
* Dependents
* Tenure Months

## Services

* Phone Service
* Multiple Lines
* Internet Service
* Online Security
* Online Backup
* Device Protection
* Tech Support
* Streaming TV
* Streaming Movies

## Contract & Billing

* Contract
* Paperless Billing
* Payment Method
* Monthly Charges
* Total Charges

---

# ⚙️ Feature Engineering

The raw customer dataset is transformed into additional features before model prediction.

Engineered features include:

* `tenure_group`
* `has_internet`
* `active_addon_count`
* `has_protection_addon`
* `has_streaming_addon`
* `avg_monthly_value`
* `contract_risk_flag`
* `payment_risk_flag`
* `family_flag`

These features help the model capture higher-level patterns in customer behavior.

---

# 🔄 Machine Learning Pipeline

```text
                 Raw Customer Data
                         │
                         ▼
                 Data Validation
                         │
                         ▼
                Feature Engineering
                         │
                         ▼
                   Preprocessing
                         │
                         ▼
                   Random Forest
                         │
                         ▼
                 Churn Probability
                         │
                         ▼
                Decision Threshold
                     0.37
                         │
                         ▼
                 Risk Classification
                         │
                         ▼
                  SHAP Explanation
```

---

# 🏗️ System Architecture

```text
                         INTERNET
                            │
                            ▼
                  ┌──────────────────┐
                  │      NGINX       │
                  │ Reverse Proxy    │
                  │   HTTPS / SSL    │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │     Next.js      │
                  │    Frontend      │
                  │    Port 3000     │
                  └────────┬─────────┘
                           │
                           │ REST API
                           ▼
                  ┌──────────────────┐
                  │ Flask + Gunicorn │
                  │     Backend      │
                  │    Port 5000     │
                  └────────┬─────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌───────────┐ ┌──────────┐
        │ Database │ │ ML Model  │ │   SHAP   │
        │          │ │ Random    │ │ Explain. │
        │          │ │ Forest    │ │          │
        └──────────┘ └───────────┘ └──────────┘
```

---

# 🛠️ Technology Stack

## Frontend

* Next.js
* React
* TypeScript
* CSS
* Server-side rendering

## Backend

* Python
* Flask
* Gunicorn
* Pydantic
* SQLAlchemy

## Machine Learning

* Python
* Pandas
* NumPy
* Scikit-learn
* Random Forest
* Artificial Neural Network
* Gradient Boosting
* Logistic Regression
* SHAP
* Joblib

## Database

* SQLAlchemy
* Production database configuration

## DevOps & Deployment

* Ubuntu Linux
* Nginx
* Gunicorn
* systemd
* Let's Encrypt
* HTTPS
* VPS
* Git
* GitHub

---

# 🔌 REST API

ChurnAI provides REST endpoints for authentication, predictions, datasets, analytics, models, reports, and training.

## Authentication

```text
POST /api/auth/signup
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/session
POST /api/auth/forgot-password
POST /api/auth/reset-password
```

## Predictions

```text
POST /api/predictions/single
POST /api/predictions/batch
GET  /api/predictions
GET  /api/predictions/batch/<batch_job_id>
GET  /api/predictions/batch/<batch_job_id>/download
```

## Analytics

```text
GET /api/analytics/dashboard
GET /api/analytics/risk-distribution
GET /api/analytics/churn-trend
GET /api/analytics/top-drivers
GET /api/analytics/segments
```

## Datasets

```text
POST /api/datasets
GET  /api/datasets
GET  /api/datasets/<dataset_id>
```

## Models

```text
GET  /api/models
GET  /api/models/<model_id>
POST /api/models/<model_id>/activate
POST /api/models/<model_id>/deactivate
```

## Reports

```text
POST /api/reports/generate
GET  /api/reports
GET  /api/reports/<report_id>/download
```

## Health

```text
GET /api/health
```

---

# 🧪 Example Prediction

A customer can be submitted to the API with their demographic, service, contract, and billing information.

Example response:

```json
{
  "algorithm": "random_forest",
  "churn_probability": 0.8637874265,
  "customer_id": "TEST-001",
  "decision_threshold": 0.37,
  "predicted_class": 1,
  "risk_level": "high",
  "model_id": "random_forest_v1"
}
```

The response can also contain SHAP explanations identifying the features that contributed most strongly to the prediction.

---

# 📁 Project Structure

```text
churn-ai/
│
├── backend/
│   ├── routes/
│   │   ├── auth.py
│   │   ├── predictions.py
│   │   ├── analytics.py
│   │   ├── datasets.py
│   │   ├── models.py
│   │   ├── reports.py
│   │   └── training.py
│   │
│   ├── services/
│   ├── validation/
│   ├── db/
│   ├── auth/
│   └── ...
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── middleware.ts
│   └── ...
│
├── ml/
│   ├── data_quality/
│   ├── eda/
│   ├── features/
│   ├── preprocessing/
│   └── ...
│
├── data/
├── tests/
├── docs/
│
├── requirements.txt
├── .gitignore
└── README.md
```

Production ML artifacts are intentionally excluded from Git because the trained model binaries are large and are deployed separately to the production server.

---

# 🔐 Security & Validation

ChurnAI implements multiple layers of application and data validation.

### Authentication

* Session-based authentication
* HTTP-only cookies
* Password complexity requirements
* Login validation
* Organization-based access

### Request Validation

* Pydantic request schemas
* Dynamic ML feature validation
* CSV schema validation
* Data-quality validation

### Infrastructure

* HTTPS
* Nginx reverse proxy
* Environment-based configuration
* Gitignored environment files
* Production ML artifacts separated from source control

---

# 🚀 Production Deployment

ChurnAI is deployed on an Ubuntu VPS using a production-style architecture.

### Production Services

```text
churnai-backend.service
churnai-frontend.service
nginx.service
```

The services are managed using `systemd` and configured to start automatically after server reboot.

### Production Request Flow

```text
User
 │
 ▼
https://khanova.tech
 │
 ▼
Nginx
 │
 ├──────────────► Next.js Frontend
 │
 └──────────────► Flask API
                         │
                         ├── Database
                         ├── Random Forest
                         └── SHAP
```

---

# 🧭 Development Journey

ChurnAI was developed as a complete end-to-end AI application.

## Phase 1 — Dataset Foundation

* Audited the original customer churn dataset
* Added synthetic regional development data
* Built data-generation utilities
* Added automated tests

## Phase 2 — Data Quality

* Implemented missing-value validation
* Added business-rule validation
* Added dataset quality checks

## Phase 3 — Feature Engineering

* Created domain-specific features
* Added tenure groups
* Added contract-risk indicators
* Added payment-risk indicators
* Added service/add-on features

## Phase 4 — Preprocessing

* Built preprocessing pipelines
* Created train/validation/test splits
* Prevented data leakage
* Saved preprocessing artifacts

## Phase 5 — Model Development

* Trained Logistic Regression
* Trained Random Forest
* Trained Gradient Boosting
* Trained Artificial Neural Network
* Compared validation performance
* Selected Random Forest

## Application Development

* Built Flask REST API
* Added authentication
* Added database persistence
* Added prediction services
* Added SHAP explanations
* Built Next.js frontend
* Added analytics
* Added batch prediction
* Added reporting
* Deployed application to production

---

# 🧠 Important Engineering Decisions

## Why Random Forest Instead of ANN?

The initial plan was to use an Artificial Neural Network.

However, after training and evaluating multiple models, Random Forest produced better validation performance, particularly in recall and PR-AUC.

Therefore, Random Forest was selected as the final production model.

The ANN was not discarded because it was a bad model. It was simply not the best-performing candidate for this particular dataset and evaluation objective.

---

## Why Not Use Accuracy Alone?

Churn datasets can contain an imbalance between customers who churn and customers who do not churn.

Because of this, accuracy alone can be misleading.

ChurnAI therefore considers metrics such as:

* Precision
* Recall
* F1
* ROC-AUC
* PR-AUC

Recall is particularly important because failing to identify a customer who is likely to churn can represent a lost retention opportunity.

---

## Why Use a 0.37 Threshold?

A default threshold of `0.50` was not assumed to be optimal.

The threshold was selected using the validation dataset by maximizing F1 score.

This produced the final decision threshold:

```text
0.37
```

The test set was not used for threshold selection.

---

## Why SHAP?

A prediction without an explanation is difficult for a business user to act upon.

SHAP provides visibility into the features influencing individual predictions and makes the ML system more interpretable.

---

## Why Separate ML Artifacts from Git?

The production Random Forest model is approximately 50 MB.

Keeping the model artifacts outside Git:

* Keeps the repository lightweight
* Avoids unnecessary binary files in source control
* Allows models to be deployed independently
* Separates source code from production artifacts

---

# 🧪 Testing

The project includes automated tests covering important machine-learning and backend functionality.

Testing includes:

* Data validation
* Feature engineering
* Preprocessing
* Model behavior
* API validation
* Authentication
* Backend services

### ML Development Test Status

```text
131 tests passed
```

---

# 🎯 Project Objectives

The main objective was to transform a machine-learning model into a complete AI-powered software product.

ChurnAI demonstrates practical experience with:

* Python
* Machine Learning
* Deep Learning
* Explainable AI
* Data preprocessing
* Feature engineering
* Model evaluation
* REST APIs
* Flask
* Next.js
* React
* TypeScript
* Databases
* Authentication
* Linux
* Nginx
* Gunicorn
* systemd
* HTTPS
* Git/GitHub
* Production deployment

---

# 🔮 Future Improvements

Possible future improvements include:

* Automated model retraining
* Model monitoring
* Data drift detection
* Model drift detection
* Advanced retention recommendations
* A/B testing for retention strategies
* Additional machine-learning models
* Customer lifetime value analysis
* Real-time analytics
* Automated alerts
* Cloud-native deployment

---

# 🌟 What Makes ChurnAI Different?

ChurnAI is more than a churn prediction model.

It connects the complete machine-learning product lifecycle:

```text
                 DATA
                  │
                  ▼
          FEATURE ENGINEERING
                  │
                  ▼
           MODEL DEVELOPMENT
                  │
                  ▼
           MODEL EVALUATION
                  │
                  ▼
          PRODUCTION MODEL
                  │
                  ▼
        EXPLAINABLE AI / SHAP
                  │
                  ▼
             REST API
                  │
                  ▼
             DATABASE
                  │
                  ▼
             FRONTEND
                  │
                  ▼
        PRODUCTION DEPLOYMENT
```

The project demonstrates how a machine-learning solution can move beyond a notebook and become a usable software product.

---

# 👨‍💻 Author

## Bahawal Khan

Computer Science Student | AI / ML Developer

### Links

* 🌐 Live Application: https://khanova.tech
* 💻 GitHub: https://github.com/bahawal-khan/churn-ai

---

# 📄 License

This project is developed for educational, portfolio, and demonstration purposes.
