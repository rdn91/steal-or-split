from fastapi import FastAPI, WebSocket
app= FastAPI()
@app.get("/")
def read_root():
    return{"message":"server is running"}
