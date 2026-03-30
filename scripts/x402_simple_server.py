import base64
import json
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI()

# Configuration matches tests/test_server_integration.py
PORT = 4022
HOST = "127.0.0.1"

def get_x402_header(amount_micros: int, label: str):
    requirements = {
        "x402Version": 2,
        "scheme": "exact",
        "accepts": [{
            "scheme": "exact",
            "network": "eip155:84532", # Base Sepolia
            "amount": str(amount_micros),
            "payTo": "0x1234567890123456789012345678901234567890", # Dummy
            "label": label
        }, {
            "scheme": "GatewayWalletBatched",
            "network": "eip155:5042002", # ARC Testnet
            "amount": str(amount_micros),
            "payTo": "0x1234567890123456789012345678901234567890"
        }]
    }
    return base64.b64encode(json.dumps(requirements).encode()).decode()

@app.get("/")
@app.get("/health")
@app.get("/api/status")
async def health():
    return {"status": "ok"}

@app.get("/weather")
async def weather(request: Request):
    sig = request.headers.get("payment-signature")
    if not sig or sig == "invalid-signature-data":
        return Response(
            status_code=402,
            headers={"PAYMENT-REQUIRED": get_x402_header(1000, "Weather Data")}
        )
    return {"weather": "sunny", "temp": 72}

@app.get("/premium/content")
async def premium_content(request: Request):
    sig = request.headers.get("payment-signature")
    if not sig:
        return Response(
            status_code=402,
            headers={"PAYMENT-REQUIRED": get_x402_header(10000, "Premium Content")}
        )
    return {"content": "Ultra HD Video Stream"}

@app.get("/premium/data")
async def premium_data(request: Request):
    sig = request.headers.get("payment-signature")
    if not sig:
        return Response(
            status_code=402,
            headers={"PAYMENT-REQUIRED": get_x402_header(100000, "Premium Data")}
        )
    return {"data": [1, 2, 3, 4, 5]}

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
