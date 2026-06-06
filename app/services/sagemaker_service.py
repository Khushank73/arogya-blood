import os
import pickle
import datetime
import logging
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from app.core.config import settings

logger = logging.getLogger("app.sagemaker")

class SageMakerService:
    def __init__(self):
        self.model_dir = os.path.join(".", "app_data", "models")
        os.makedirs(self.model_dir, exist_ok=True)
        
        self.availability_model_path = os.path.join(self.model_dir, "availability_model.pkl")
        self.churn_model_path = os.path.join(self.model_dir, "churn_model.pkl")
        
        self.csv_path = "./Dataset.csv"
        
        # Load or train models
        self.availability_model = None
        self.churn_model = None
        
        try:
            self.load_or_train_models()
        except Exception as e:
            logger.error(f"Error loading or training models: {e}. Fallback to mock logic.")

    def parse_days_ago(self, date_str, baseline_date):
        if not date_str or str(date_str).lower() == 'nan' or date_str == "":
            return 180.0  # Default to 6 months ago if no contact info
        try:
            # Try DD-MM-YYYY format
            date_val = datetime.datetime.strptime(str(date_str).strip(), "%d-%m-%Y")
            delta = baseline_date - date_val
            return float(max(0, delta.days))
        except Exception:
            return 180.0

    def load_or_train_models(self):
        if os.path.exists(self.availability_model_path) and os.path.exists(self.churn_model_path):
            logger.info("Loading pre-trained SageMaker models from local cache...")
            with open(self.availability_model_path, "rb") as f:
                self.availability_model = pickle.load(f)
            with open(self.churn_model_path, "rb") as f:
                self.churn_model = pickle.load(f)
            return

        logger.info("Local models not found. Initiating local SageMaker training pipeline on Dataset.csv...")
        if not os.path.exists(self.csv_path):
            logger.warning("Dataset.csv not found. Skipping training, utilizing heuristics.")
            return

        df = pd.read_csv(self.csv_path)
        
        # Preprocessing
        baseline = datetime.datetime(2026, 6, 6) # local time baseline
        
        # Handle numeric casts
        df['donations_till_date'] = pd.to_numeric(df['donations_till_date'], errors='coerce').fillna(0).astype(int)
        df['total_calls'] = pd.to_numeric(df['total_calls'], errors='coerce').fillna(0).astype(int)
        df['frequency_in_days'] = pd.to_numeric(df['frequency_in_days'], errors='coerce').fillna(0).astype(int)
        df['calls_to_donations_ratio'] = pd.to_numeric(df['calls_to_donations_ratio'], errors='coerce').fillna(0.0).astype(float)
        
        # Date column conversion -> days since event
        df['days_since_last_contacted'] = df['last_contacted_date'].apply(lambda x: self.parse_days_ago(x, baseline))
        
        # Clean label mapping
        df['user_donation_active_status'] = df['user_donation_active_status'].fillna('Active').astype(str)
        df['is_active_donor'] = (df['user_donation_active_status'].str.lower() == 'active').astype(int)
        
        df['eligibility_status'] = df['eligibility_status'].fillna('not eligible').astype(str)
        df['is_eligible'] = (df['eligibility_status'].str.lower() == 'eligible').astype(int)
        
        # Target definitions
        # 1. Availability: eligible AND active
        df['target_available'] = ((df['is_eligible'] == 1) & (df['is_active_donor'] == 1)).astype(int)
        # 2. Churn: user active status is Inactive
        df['target_churn'] = (df['is_active_donor'] == 0).astype(int)
        
        features = [
            'donations_till_date', 
            'total_calls', 
            'calls_to_donations_ratio', 
            'frequency_in_days', 
            'days_since_last_contacted',
            'is_active_donor'
        ]
        
        X = df[features].fillna(0)
        
        # Train Availability Model
        logger.info("Training Donor Availability Prediction Model...")
        y_avail = df['target_available']
        clf_avail = RandomForestClassifier(n_estimators=50, random_state=42)
        clf_avail.fit(X, y_avail)
        self.availability_model = clf_avail
        with open(self.availability_model_path, "wb") as f:
            pickle.dump(clf_avail, f)
            
        # Train Churn Model
        logger.info("Training Donor Churn Prediction Model...")
        y_churn = df['target_churn']
        # For churn, we do not include active_donor directly to make it predictive on other behavior
        features_churn = [
            'donations_till_date', 
            'total_calls', 
            'calls_to_donations_ratio', 
            'frequency_in_days', 
            'days_since_last_contacted'
        ]
        X_churn = df[features_churn].fillna(0)
        clf_churn = RandomForestClassifier(n_estimators=50, random_state=42)
        clf_churn.fit(X_churn, y_churn)
        self.churn_model = clf_churn
        with open(self.churn_model_path, "wb") as f:
            pickle.dump(clf_churn, f)
            
        logger.info("Models trained and cached successfully!")

    def predict_availability_prob(self, features_dict: dict) -> float:
        """
        Input keys: donations_till_date, total_calls, calls_to_donations_ratio,
                    frequency_in_days, last_contacted_date, user_donation_active_status
        """
        if not self.availability_model:
            # Fallback heuristic if not trained
            status = str(features_dict.get("user_donation_active_status", "Active")).lower()
            if status != "active":
                return 0.15
            ratio = float(features_dict.get("calls_to_donations_ratio", 1.0))
            if ratio > 5.0:
                return 0.40
            return 0.85

        # Feature prep
        baseline = datetime.datetime(2026, 6, 6)
        days_contacted = self.parse_days_ago(features_dict.get("last_contacted_date"), baseline)
        is_active = 1 if str(features_dict.get("user_donation_active_status", "Active")).lower() == "active" else 0
        
        x_in = [[
            int(features_dict.get("donations_till_date", 0)),
            int(features_dict.get("total_calls", 0)),
            float(features_dict.get("calls_to_donations_ratio", 0.0)),
            int(features_dict.get("frequency_in_days", 0)),
            days_contacted,
            is_active
        ]]
        
        # Get probability of class 1
        prob = self.availability_model.predict_proba(x_in)[0][1]
        return float(np.round(prob, 2))

    def predict_churn_prob(self, features_dict: dict) -> float:
        """
        Input keys: donations_till_date, total_calls, calls_to_donations_ratio,
                    frequency_in_days, last_contacted_date
        """
        if not self.churn_model:
            # Fallback heuristic
            ratio = float(features_dict.get("calls_to_donations_ratio", 1.0))
            if ratio > 3.0:
                return 0.75
            return 0.20

        baseline = datetime.datetime(2026, 6, 6)
        days_contacted = self.parse_days_ago(features_dict.get("last_contacted_date"), baseline)
        
        x_in = [[
            int(features_dict.get("donations_till_date", 0)),
            int(features_dict.get("total_calls", 0)),
            float(features_dict.get("calls_to_donations_ratio", 0.0)),
            int(features_dict.get("frequency_in_days", 0)),
            days_contacted
        ]]
        
        prob = self.churn_model.predict_proba(x_in)[0][1]
        return float(np.round(prob, 2))

sagemaker_service = SageMakerService()
