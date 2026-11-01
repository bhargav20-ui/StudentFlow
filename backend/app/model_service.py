import json,re,time
from .config import GEMINI_API_KEY,GEMINI_MODEL,INPUT_PRICE_PER_1M,OUTPUT_PRICE_PER_1M

class ModelUnavailable(RuntimeError):
    pass

RETRYABLE_STATUS_CODES={429,500,502,503,504}

def is_retryable_gemini_error(exc):
    """Return True only for transient Gemini/API availability errors."""
    for attr in ("code","status_code","http_status"):
        value=getattr(exc,attr,None)
        try:
            if int(value) in RETRYABLE_STATUS_CODES:
                return True
        except (TypeError,ValueError):
            pass
    message=str(exc).lower()
    return any(token in message for token in (
        "429","500","502","503","504","resource_exhausted",
        "service_unavailable","temporarily unavailable","high demand"
    ))

class GeminiService:
    def __init__(self):
        self.client=None
        self.model=GEMINI_MODEL
        if GEMINI_API_KEY:
            try:
                from google import genai
                self.client=genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                raise ModelUnavailable(f"Gemini client initialization failed: {e}")

    def generate(self,prompt,json_mode=False):
        if not self.client:
            raise ModelUnavailable("Gemini API key is not configured. Add GEMINI_API_KEY to the service environment.")
        config={"temperature":0.1}
        if json_mode:
            config["response_mime_type"]="application/json"

        # Three total attempts; retry only transient rate-limit/server errors.
        for attempt in range(3):
            try:
                r=self.client.models.generate_content(
                    model=self.model,contents=prompt,config=config
                )
                break
            except Exception as exc:
                if attempt==2 or not is_retryable_gemini_error(exc):
                    raise
                time.sleep(1.5*(2**attempt))

        text=getattr(r,"text",None) or ""
        u=getattr(r,"usage_metadata",None)
        inp=int(getattr(u,"prompt_token_count",0) or 0)
        out=int(getattr(u,"candidates_token_count",0) or 0)
        cost=None
        if INPUT_PRICE_PER_1M is not None and OUTPUT_PRICE_PER_1M is not None:
            cost=inp/1e6*INPUT_PRICE_PER_1M+out/1e6*OUTPUT_PRICE_PER_1M
        data=None
        if json_mode:
            try:
                data=json.loads(text)
            except Exception:
                m=re.search(r"\{.*\}",text,re.S)
                if m:
                    try:
                        data=json.loads(m.group(0))
                    except Exception:
                        pass
        return {"text":text,"json":data,"input_tokens":inp,"output_tokens":out,"cost_usd":cost}
