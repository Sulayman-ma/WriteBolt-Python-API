from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import search, links, sitemap, yt_transcript

# FastAPI app instance
app = FastAPI()

# CORS Configuration
origins = [
    "https://writebolt.com",
    "https://writebolt-backend.vercel.app/",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # allow_origins=["*"],
    allow_methods=['*'],
    allow_headers=['*'],
    allow_credentials=True,
)


# Register routers with app
app.include_router(search.router)
app.include_router(links.router)
app.include_router(sitemap.router)
app.include_router(yt_transcript.router)


@app.get("/")
async def root():
    return "You should not be here"
