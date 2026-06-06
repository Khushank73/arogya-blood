import os
import boto3
import json
import logging
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from app.core.config import settings

logger = logging.getLogger("app.aws")

class MockBoto3Client:
    def __init__(self, service_name):
        self.service_name = service_name
        # Simple local persistence paths
        self.mock_dir = os.path.join(".", "app_data", "mock_aws")
        os.makedirs(self.mock_dir, exist_ok=True)
        
        # Local DynamoDB file
        self.dynamo_path = os.path.join(self.mock_dir, "dynamodb_memory.json")
        if not os.path.exists(self.dynamo_path):
            with open(self.dynamo_path, "w") as f:
                json.dump({}, f)

    # --- S3 MOCKS ---
    def put_object(self, Bucket, Key, Body, **kwargs):
        s3_dir = os.path.join(self.mock_dir, "s3", Bucket)
        os.makedirs(os.path.dirname(os.path.join(s3_dir, Key)), exist_ok=True)
        with open(os.path.join(s3_dir, Key), "wb") as f:
            if isinstance(Body, str):
                f.write(Body.encode("utf-8"))
            else:
                f.write(Body)
        logger.info(f"[Mock S3] Uploaded to {Bucket}/{Key}")
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def get_object(self, Bucket, Key, **kwargs):
        s3_path = os.path.join(self.mock_dir, "s3", Bucket, Key)
        if os.path.exists(s3_path):
            with open(s3_path, "rb") as f:
                return {"Body": f}
        raise FileNotFoundError(f"[Mock S3] Key {Key} not found in {Bucket}")

    # --- DYNAMODB MOCKS ---
    def put_item(self, TableName, Item, **kwargs):
        data = {}
        with open(self.dynamo_path, "r") as f:
            data = json.load(f)
        
        # Parse Pydantic/Dynamo format: e.g. {"user_id": {"S": "123"}}
        parsed_item = {}
        for k, v in Item.items():
            val_type = list(v.keys())[0]
            parsed_item[k] = v[val_type]
        
        key = parsed_item.get("user_id") or parsed_item.get("session_id")
        if not key:
            # Fallback to general indexing
            key = str(hash(frozenset(parsed_item.items())))

        data[key] = parsed_item
        with open(self.dynamo_path, "w") as f:
            json.dump(data, f)
        logger.info(f"[Mock DynamoDB] Put item in {TableName}: {key}")
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    def get_item(self, TableName, Key, **kwargs):
        data = {}
        with open(self.dynamo_path, "r") as f:
            data = json.load(f)
        
        # Key: e.g. {"user_id": {"S": "123"}}
        key_name = list(Key.keys())[0]
        key_val = Key[key_name]["S"]
        
        item = data.get(key_val)
        if not item:
            return {}
        
        # Format back to DynamoDB syntax
        formatted_item = {}
        for k, v in item.items():
            formatted_item[k] = {"S": str(v)}
            
        return {"Item": formatted_item}

    # --- BEDROCK MOCKS ---
    def invoke_model(self, modelId, body, **kwargs):
        logger.info(f"[Mock Bedrock] Invoking model {modelId}")
        payload = json.loads(body)
        prompt = payload.get("inputText", payload.get("prompt", ""))
        
        # High quality simulation response matching the prompt contents
        response_text = ""
        prompt_lower = prompt.lower()
        if "thalassemia" in prompt_lower or "hplc" in prompt_lower:
            if "risk" in prompt_lower or "genetic" in prompt_lower:
                response_text = json.dumps({
                    "risk_category": "HIGH",
                    "counseling_recommendations": "Both partners carry Beta Thalassemia Trait. Pre-marital genetic counseling and pre-implantation diagnosis (PGD) or prenatal diagnosis are advised.",
                    "awareness_material": "Carrier status means you are healthy but carry a genetic mutation. Passing this to offspring requires careful testing."
                })
            elif "analyze" in prompt_lower or "report" in prompt_lower:
                response_text = json.dumps({
                    "hba": 91.2,
                    "hba2": 5.4,
                    "hbf": 3.4,
                    "classification": "Carrier",
                    "recommendations": "A elevated level of HbA2 (5.4%) confirms the presence of Beta-Thalassemia Trait. Partner screening is essential."
                })
            else:
                response_text = "Thalassemia is an inherited blood disorder where the body produces an abnormal amount of hemoglobin. HPLC screening (High-Performance Liquid Chromatography) detects carriers of the thalassemia gene."
        elif "campaign" in prompt_lower or "content" in prompt_lower or "whatsapp" in prompt_lower:
            response_text = json.dumps({
                "content_text": "🚨 Prevent Thalassemia! Did you know a simple HPLC blood test can save your future child? Get screened before marriage. Let's make India Thalassemia-free by 2035! 🩸",
                "suggested_visuals": "An image showing a happy family holding hands with a blood drop outline.",
                "campaign_type": "WhatsApp Message",
                "language": "English"
            })
        else:
            response_text = f"Thank you for contacting the Blood Warriors Care assistant. We are here to support blood bridges, donation matching, and screening efforts. Let us know how we can coordinate availability or prevent thalassemia."

        # Return byte response matching Bedrock structure
        mock_body_out = json.dumps({
            "results": [{"outputText": response_text}],
            "completion": response_text
        })
        
        class MockResponse:
            def read(self):
                return mock_body_out.encode("utf-8")
        
        return {"body": MockResponse()}

    # --- STEP FUNCTIONS MOCKS ---
    def start_execution(self, stateMachineArn, input, **kwargs):
        execution_arn = f"arn:aws:states:us-east-1:123456789012:execution:OutreachWorkflowState:{random.randint(1000, 9999)}"
        logger.info(f"[Mock Step Functions] Started execution {execution_arn} with inputs {input}")
        return {
            "executionArn": execution_arn,
            "startDate": "2026-06-06T12:00:00Z"
        }

# Helper method to get AWS or Mock Client
def get_aws_client(service_name):
    if settings.USE_LOCAL_MOCKS:
        return MockBoto3Client(service_name)
        
    try:
        session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        # Verify connectivity
        client = session.client(service_name)
        return client
    except (NoCredentialsError, PartialCredentialsError) as e:
        logger.warning(f"AWS credentials not found. Falling back to local mock client for: {service_name}")
        return MockBoto3Client(service_name)
    except Exception as e:
        logger.error(f"Error creating AWS client {service_name}: {e}. Falling back to mocks.")
        return MockBoto3Client(service_name)
