from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def home():
    return {"message": "API working", "database": "not connected"}

@app.post("/parse")
def parse_sms(sms_text: str):
    return {"parsed": True, "amount": 1500.00, "test": "no db"}

if __name__ == "__main__":
    print(" Server starting on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
