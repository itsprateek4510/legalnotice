"""
Optional convenience launcher.

Run the app with:  python run.py
or directly with:  uvicorn app.main:app --reload
"""

import uvicorn

from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )
