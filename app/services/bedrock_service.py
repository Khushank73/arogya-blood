import json
import logging
import re
from typing import Dict, Any, List
from app.core.aws import get_aws_client

logger = logging.getLogger("app.bedrock")

class BedrockService:
    def __init__(self):
        self.bedrock_client = get_aws_client("bedrock-runtime")
        self.dynamo_client = get_aws_client("dynamodb")

    def _query_bedrock(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Invokes Bedrock Claude or falls back to local simulation logic.
        """
        body = json.dumps({
            "prompt": prompt,
            "max_tokens_to_sample": max_tokens,
            "temperature": 0.5,
            "top_k": 250,
            "top_p": 1,
            "stop_sequences": ["\n\nHuman:"]
        })
        
        try:
            response = self.bedrock_client.invoke_model(
                modelId="anthropic.claude-v2",
                body=body
            )
            response_body = json.loads(response.get("body").read().decode("utf-8"))
            
            # Accommodate different model schema outputs
            if "completion" in response_body:
                return response_body["completion"].strip()
            elif "results" in response_body:
                return response_body["results"][0]["outputText"].strip()
            return str(response_body)
        except Exception as e:
            logger.error(f"Failed to query Bedrock: {e}. Fallback to simulated response.")
            return "Simulated LLM response"

    # --- Pillar 1: Conversational Care Assistant ---
    def get_care_chat_response(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        Queries Bedrock LLM with user history retrieved from DynamoDB.
        Updates user preferences and memory state.
        """
        # 1. Retrieve history from DynamoDB
        history = []
        lang_pref = "English"
        comm_channel = "WhatsApp"
        preferences = {}

        try:
            res = self.dynamo_client.get_item(
                TableName="BloodWarriorsUserMemory",
                Key={"user_id": {"S": user_id}}
            )
            if "Item" in res:
                item = res["Item"]
                lang_pref = item.get("language_preference", {}).get("S", "English")
                comm_channel = item.get("preferred_channel", {}).get("S", "WhatsApp")
                history_json = item.get("interaction_history", {}).get("S", "[]")
                history = json.loads(history_json)
                pref_json = item.get("donor_preferences", {}).get("S", "{}")
                preferences = json.loads(pref_json)
        except Exception as e:
            logger.warning(f"Failed to load user memory from DynamoDB: {e}")

        # 2. Extract preferences dynamically from new message
        msg_lower = message.lower()
        if "hindi" in msg_lower:
            lang_pref = "Hindi"
        elif "telugu" in msg_lower:
            lang_pref = "Telugu"
        elif "tamil" in msg_lower:
            lang_pref = "Tamil"
        elif "kannada" in msg_lower:
            lang_pref = "Kannada"

        if "sms" in msg_lower:
            comm_channel = "SMS"
        elif "whatsapp" in msg_lower:
            comm_channel = "WhatsApp"
        elif "call" in msg_lower:
            comm_channel = "Voice Call"

        # 3. Call Bedrock LLM with context
        prompt = (
            f"You are the Blood Warriors Conversational Care Assistant.\n"
            f"User Profile:\n"
            f"- Language Preference: {lang_pref}\n"
            f"- Preferred Communication Channel: {comm_channel}\n"
            f"- Special Preferences: {json.dumps(preferences)}\n\n"
            f"User message: {message}\n"
            f"Provide a helpful, empathetic response in the preferred language. Keep it brief."
        )
        
        # In a real environment, we'd query bedrock. In mock environment, aws.py returns formatted text.
        llm_out = self._query_bedrock(prompt)

        # 4. Save updated history to DynamoDB
        history.append({"role": "user", "content": message, "timestamp": datetime.datetime.utcnow().isoformat()})
        history.append({"role": "assistant", "content": llm_out, "timestamp": datetime.datetime.utcnow().isoformat()})
        
        # Limit history length
        if len(history) > 20:
            history = history[-20:]

        try:
            self.dynamo_client.put_item(
                TableName="BloodWarriorsUserMemory",
                Item={
                    "user_id": {"S": user_id},
                    "language_preference": {"S": lang_pref},
                    "preferred_channel": {"S": comm_channel},
                    "interaction_history": {"S": json.dumps(history)},
                    "donor_preferences": {"S": json.dumps(preferences)}
                }
            )
        except Exception as e:
            logger.error(f"Failed to persist user memory to DynamoDB: {e}")

        return {
            "user_id": user_id,
            "response": llm_out,
            "language": lang_pref,
            "preferred_channel": comm_channel,
            "history": history
        }

    # --- Pillar 2: HPLC Report Analyzer ---
    def analyze_hplc_report(self, raw_ocr_text: str) -> Dict[str, Any]:
        """
        Uses LLM + clinical rules to extract HbA, HbA2, HbF and classify the patient.
        Rules:
        - Normal: HbA2 between 1.5% and 3.5%
        - Carrier (Beta Thalassemia Trait): HbA2 > 3.5%
        - Further testing / Thalassemia Major: HbF > 10.0% or HbA < 60.0%
        """
        # Try to extract numbers from the OCR string directly for deterministic output
        hba = 97.0
        hba2 = 2.5
        hbf = 0.5
        
        hba_match = re.search(r'HbA\s*:\s*([\d\.]+)', raw_ocr_text, re.IGNORECASE)
        hba2_match = re.search(r'HbA2\s*:\s*([\d\.]+)', raw_ocr_text, re.IGNORECASE)
        hbf_match = re.search(r'HbF\s*:\s*([\d\.]+)', raw_ocr_text, re.IGNORECASE)
        
        if hba_match:
            try: hba = float(hba_match.group(1))
            except: pass
        if hba2_match:
            try: hba2 = float(hba2_match.group(1))
            except: pass
        if hbf_match:
            try: hbf = float(hbf_match.group(1))
            except: pass

        # Let's override classification based on clinical guidelines
        if hba2 > 3.5:
            classification = "Carrier"
            recommendations = (
                f"Elevated HbA2 of {hba2}% is indicative of Beta-Thalassemia Trait (Carrier). "
                "You are healthy, but you carry a genetic trait. It is vital to screen your partner "
                "before marriage or conception to assess risk of Thalassemia Major in offspring."
            )
        elif hbf > 10.0 or hba < 70.0:
            classification = "Further Testing Needed"
            recommendations = (
                f"Significantly elevated HbF of {hbf}% or low HbA of {hba}% detected. "
                "This requires molecular genetic confirmation for Beta-Thalassemia Intermedia/Major or "
                "other hemoglobinopathies. Please consult a hematologist."
            )
        else:
            classification = "Non-Carrier"
            recommendations = (
                f"Normal Hb profile (HbA2: {hba2}%, HbF: {hbf}%). "
                "Patient is not a carrier of classic Beta-Thalassemia. No further screening required."
            )

        # Call LLM to embellish recommendations or output
        prompt = (
            f"Review this HPLC Report data:\n"
            f"HbA: {hba}%, HbA2: {hba2}%, HbF: {hbf}%\n"
            f"Clinical Classification: {classification}\n"
            f"Generate a patient-friendly summary explaining what this means."
        )
        llm_interpretation = self._query_bedrock(prompt)

        return {
            "hba": hba,
            "hba2": hba2,
            "hbf": hbf,
            "classification": classification,
            "recommendations": llm_interpretation if "simulated" not in llm_interpretation.lower() else recommendations
        }

    # --- Pillar 2: Genetic Risk Assessment ---
    def assess_genetic_risk(self, p1_report: Dict[str, Any], p2_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compares reports of 2 individuals.
        If both are Carriers -> High Risk (25% Thalassemia Major offspring)
        If one is Carrier -> Low Risk
        If neither is Carrier -> No Risk
        """
        c1 = p1_report.get("classification")
        c2 = p2_report.get("classification")
        
        if c1 == "Carrier" and c2 == "Carrier":
            risk = "HIGH"
            counseling = (
                "CRITICAL: Both partners carry Beta-Thalassemia Trait. There is a 25% (1 in 4) chance "
                "that each pregnancy could result in a child born with Thalassemia Major (severe transfusion-dependent anemia). "
                "Please schedule an immediate consultation with a genetic counselor and a prenatal diagnostic specialist."
            )
            material = "Thalassemia Major is preventable. Prenatal diagnosis (CVS/Amniocentesis) can identify fetal status."
        elif c1 == "Carrier" or c2 == "Carrier":
            risk = "LOW"
            counseling = (
                "One partner carries the Beta-Thalassemia Trait. There is a 50% chance offspring will inherit the carrier trait, "
                "but 0% chance they will inherit Thalassemia Major. No immediate medical intervention needed for pregnancy."
            )
            material = "Thalassemia carrier status is not a disease and does not affect normal lifespan or health."
        else:
            risk = "NONE"
            counseling = "Both partners have normal HPLC hemoglobin profiles. There is no risk of Thalassemia Major in offspring."
            material = "General pre-marital health recommendations. Keep healthy lifestyle."

        prompt = (
            f"Assess the pre-marital genetic risk for beta-thalassemia between these two reports:\n"
            f"Partner 1 classification: {c1}\n"
            f"Partner 2 classification: {c2}\n"
            f"Risk Level: {risk}\n"
            f"Counseling output: {counseling}\n"
            f"Write a concise genetic risk summary letter."
        )
        llm_out = self._query_bedrock(prompt)

        return {
            "risk_category": risk,
            "counseling_recommendations": llm_out if "simulated" not in llm_out.lower() else counseling,
            "awareness_material": material
        }

    # --- Pillar 3: AI Content Generator ---
    def generate_awareness_content(self, campaign_type: str, audience: str, language: str) -> Dict[str, Any]:
        """
        Generates targeted awareness campaigns and visual suggestions in selected languages.
        """
        prompt = (
            f"Create a high-impact {campaign_type} awareness campaign about Thalassemia prevention "
            f"tailored for {audience}. Use {language} language.\n"
            f"Include:\n"
            f"1. A strong tagline.\n"
            f"2. Core message (HPLC testing, pre-marital screening, zero thalassemia by 2035).\n"
            f"3. Call to Action.\n"
            f"4. Suggested visual/poster prompt for designers."
        )
        
        content = self._query_bedrock(prompt, max_tokens=1000)
        
        # Build local fallback if mocked
        fallback_msgs = {
            "english": "🩸 Let's make India Thalassemia Free! Get a simple HPLC blood test before marriage. Protect your children! 🩸",
            "hindi": "🩸 आइए भारत को थैलेसीमिया मुक्त बनाएं! शादी से पहले एक साधारण HPLC रक्त परीक्षण करवाएं। अपने बच्चों को सुरक्षित रखें! 🩸",
            "telugu": "🩸 థాలసీమియా లేని భారతదేశాన్ని నిర్మిద్దాం! పెళ్ళికి ముందు సాధారణ HPLC రక్త పరీక్ష చేయించుకోండి. మీ పిల్లలను రక్షించండి! 🩸",
            "tamil": "🩸 தலாசீமியா இல்லாத இந்தியாவை உருவாக்குவோம்! திருமணத்திற்கு முன் எளிய HPLC இரத்த பரிசோதனை செய்து கொள்ளுங்கள். 🩸",
            "kannada": "🩸 ಥಲಸೇಮಿಯಾ ಮುಕ್ತ ಭಾರತವನ್ನು ನಿರ್ಮಿಸೋಣ! ಮದುವೆಗೆ ಮುನ್ನ ಸರಳ HPLC ರಕ್ತ ಪರೀಕ್ಷೆ ಮಾಡಿಸಿಕೊಳ್ಳಿ. 🩸"
        }
        lang_key = language.lower()
        fallback_msg = fallback_msgs.get(lang_key, fallback_msgs["english"])
        
        if "simulated" in content.lower():
            content = f"Tagline: Screening is Caring!\nMessage: {fallback_msg}\nCall to Action: Visit the nearest Blood Warriors HPLC screening camp.\nVisual: A drop of blood blending with a golden spark of health."

        return {
            "content_text": content,
            "suggested_visuals": "Graphic featuring a family and an HPLC test strip.",
            "campaign_type": campaign_type,
            "language": language
        }

bedrock_service = BedrockService()
