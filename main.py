from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import pdf_processing
from logging_config import setup_logging
import logging

setup_logging()
logging.getLogger(__name__).info("TEST: Logging system operational")

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pdf_processing.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    