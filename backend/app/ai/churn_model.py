import os
import pickle
import datetime
import logging
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from app.core.config import settings

logger = logging.getLogger("app.ai.churn")

class ChurnModel:
    def __init__(self):
        self.model_dir = os.path.join(settings.BASE_DIR, "app_data", "models")
        os.makedirs(self.model_dir, exist_ok=True)
        self.model_path = os.path.join(self.model_dir, "churn_randomforest.pkl")
        self.model = None

    def parse_days_ago(self, date_str, baseline_date):
        if not date_str or str(date_str).lower() == 'nan' or date_str == "":
            return 180.0
        try:
            date_val = datetime.datetime.strptime(str(date_str).strip(), "%d-%m-%Y")
            delta = baseline_date - date_val
            return float(max(0, delta.days))
        except Exception:
            return 180.0

    def train(self, csv_path: str):
        logger.info(f"Training churn model using Dataset.csv at {csv_path}...")
        if not os.path.exists(csv_path):
            csv_path = os.path.join(settings.BASE_DIR, "..", "Dataset.csv")
            if not os.path.exists(csv_path):
                logger.error("Dataset.csv not found, skipping training.")
                return

        df = pd.read_csv(csv_path)
        baseline = datetime.datetime(2026, 6, 6)

        # Preprocessing
        df['donations_till_date'] = pd.to_numeric(df['donations_till_date'], errors='coerce').fillna(0).astype(int)
        df['total_calls'] = pd.to_numeric(df['total_calls'], errors='coerce').fillna(0).astype(int)
        df['cycle_of_donations'] = pd.to_numeric(df['cycle_of_donations'], errors='coerce').fillna(0).astype(int)
        
        df['days_since_last_donation'] = df['last_donation_date'].apply(lambda x: self.parse_days_ago(x, baseline))
        
        # Engagement score (0 to 100)
        df['engagement_score'] = df.apply(
            lambda r: min(100.0, (r['donations_till_date'] / max(1, r['total_calls'])) * 50.0 + r['cycle_of_donations']),
            axis=1
        )
        
        # Active status (1 if Active, 0 otherwise)
        df['user_donation_active_status'] = df['user_donation_active_status'].fillna('Active').astype(str)
        df['active_status'] = (df['user_donation_active_status'].str.lower() == 'active').astype(int)
        
        # Mock response rate based on calls vs donations (or generate it)
        # response_rate = donations_till_date / max(1, total_calls) capped at 1.0
        df['response_rate'] = df.apply(
            lambda r: min(1.0, float(r['donations_till_date']) / max(1.0, float(r['total_calls']))),
            axis=1
        )

        # Target definition: high churn risk if inactive, long time since last donation, low response rate
        # 1.0 if highly likely to churn (inactive or not participating)
        df['target_churn'] = df.apply(
            lambda r: 1.0 - (r['active_status'] * 0.4 + r['response_rate'] * 0.4 + (0.2 if r['days_since_last_donation'] <= 120 else 0.0)),
            axis=1
        )
        
        features = ['engagement_score', 'days_since_last_donation', 'active_status', 'response_rate']
        X = df[features].fillna(0)
        y = df['target_churn']

        logger.info("Fitting RandomForest regressor for donor churn...")
        model = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X, y)

        self.model = model
        with open(self.model_path, "wb") as f:
            pickle.dump(model, f)
        logger.info(f"Churn model saved to {self.model_path}")

    def load_model(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
                logger.info("Loaded churn model from cache.")
                return True
            except Exception as e:
                logger.error(f"Failed to load churn model: {e}")
        return False

    def predict(self, engagement_score: float, days_since_last_donation: float, active_status: bool, response_rate: float) -> float:
        if self.model is None:
            if not self.load_model():
                # Heuristic fallback
                active_mult = 0.2 if active_status else 0.9
                engagement_mult = (100.0 - engagement_score) / 100.0
                recency_mult = min(1.0, days_since_last_donation / 365.0)
                response_mult = 1.0 - response_rate
                
                score = (active_mult * 0.4) + (engagement_mult * 0.2) + (recency_mult * 0.2) + (response_mult * 0.2)
                return float(np.round(np.clip(score, 0.0, 1.0), 2))

        active_val = 1 if active_status else 0
        x_in = pd.DataFrame([{
            'engagement_score': float(engagement_score),
            'days_since_last_donation': float(days_since_last_donation),
            'active_status': active_val,
            'response_rate': float(response_rate)
        }])
        
        try:
            pred = self.model.predict(x_in)[0]
            return float(np.clip(np.round(pred, 2), 0.0, 1.0))
        except Exception as e:
            logger.error(f"Error predicting churn: {e}")
            return 0.3

churn_engine = ChurnModel()
