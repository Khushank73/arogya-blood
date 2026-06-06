import os
import pickle
import datetime
import logging
import pandas as pd
import numpy as np
from app.core.config import settings

logger = logging.getLogger("app.ai.availability")

# Standard imports for ML models
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    logger.warning("xgboost is not installed. Falling back to RandomForest for availability prediction.")
    from sklearn.ensemble import RandomForestRegressor
    HAS_XGB = False

class AvailabilityModel:
    def __init__(self):
        self.model_dir = os.path.join(settings.BASE_DIR, "app_data", "models")
        os.makedirs(self.model_dir, exist_ok=True)
        self.model_path = os.path.join(self.model_dir, "availability_xgboost.pkl")
        self.model = None

    def parse_days_ago(self, date_str, baseline_date):
        if not date_str or str(date_str).lower() == 'nan' or date_str == "":
            return 180.0  # Default to 6 months ago if no contact info
        try:
            date_val = datetime.datetime.strptime(str(date_str).strip(), "%d-%m-%Y")
            delta = baseline_date - date_val
            return float(max(0, delta.days))
        except Exception:
            return 180.0

    def train(self, csv_path: str):
        logger.info(f"Training availability model using Dataset.csv at {csv_path}...")
        if not os.path.exists(csv_path):
            csv_path = os.path.join(settings.BASE_DIR, "..", "Dataset.csv")
            if not os.path.exists(csv_path):
                logger.error("Dataset.csv not found, skipping training.")
                return

        df = pd.read_csv(csv_path)
        baseline = datetime.datetime(2026, 6, 6)

        # Build feature columns
        df['donations_till_date'] = pd.to_numeric(df['donations_till_date'], errors='coerce').fillna(0).astype(int)
        df['total_calls'] = pd.to_numeric(df['total_calls'], errors='coerce').fillna(0).astype(int)
        df['cycle_of_donations'] = pd.to_numeric(df['cycle_of_donations'], errors='coerce').fillna(0).astype(int)
        
        # Calculate days since last donation
        df['days_since_last_donation'] = df['last_donation_date'].apply(lambda x: self.parse_days_ago(x, baseline))
        
        # Calculate engagement score (0 to 100)
        df['engagement_score'] = df.apply(
            lambda r: min(100.0, (r['donations_till_date'] / max(1, r['total_calls'])) * 50.0 + r['cycle_of_donations']),
            axis=1
        )
        
        # Active status (1 if Active, 0 otherwise)
        df['user_donation_active_status'] = df['user_donation_active_status'].fillna('Active').astype(str)
        df['active_status'] = (df['user_donation_active_status'].str.lower() == 'active').astype(int)
        
        # Eligibility
        df['eligibility_status'] = df['eligibility_status'].fillna('not eligible').astype(str)
        df['is_eligible'] = (df['eligibility_status'].str.lower() == 'eligible').astype(int)

        # Target: continuous availability metric based on active status and eligibility
        # 1.0 if both active and eligible, drops down if inactive or ineligible
        df['target_availability'] = df.apply(
            lambda r: (r['active_status'] * 0.5) + (r['is_eligible'] * 0.4) + (0.1 if r['days_since_last_donation'] > 90 else 0.0),
            axis=1
        )
        
        features = ['days_since_last_donation', 'donations_till_date', 'engagement_score', 'active_status']
        X = df[features].fillna(0)
        y = df['target_availability']

        if HAS_XGB:
            logger.info("Fitting XGBoost regressor for availability...")
            model = xgb.XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)
            model.fit(X, y)
        else:
            logger.info("Fitting RandomForest fallback regressor...")
            model = RandomForestRegressor(n_estimators=50, max_depth=4, random_state=42)
            model.fit(X, y)

        self.model = model
        with open(self.model_path, "wb") as f:
            pickle.dump(model, f)
        logger.info(f"Model successfully saved to {self.model_path}")

    def load_model(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
                logger.info("Loaded availability model from cache.")
                return True
            except Exception as e:
                logger.error(f"Failed to load availability model: {e}")
        return False

    def predict(self, days_since_last_donation: float, donations_till_date: int, engagement_score: float, active_status: bool) -> float:
        if self.model is None:
            # Try loading it
            if not self.load_model():
                # Fallback to smart heuristic if model files are missing
                status_mult = 1.0 if active_status else 0.2
                eligibility_mult = 1.0 if days_since_last_donation >= 90 else 0.1
                score = (engagement_score / 100.0 * 0.4) + (min(10, donations_till_date) / 10.0 * 0.6)
                return float(np.round(score * status_mult * eligibility_mult, 2))
        
        active_val = 1 if active_status else 0
        x_in = pd.DataFrame([{
            'days_since_last_donation': float(days_since_last_donation),
            'donations_till_date': int(donations_till_date),
            'engagement_score': float(engagement_score),
            'active_status': active_val
        }])
        
        try:
            pred = self.model.predict(x_in)[0]
            return float(np.clip(np.round(pred, 2), 0.0, 1.0))
        except Exception as e:
            logger.error(f"Error predicting availability: {e}")
            return 0.5

availability_engine = AvailabilityModel()
