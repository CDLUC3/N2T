# Run the N2T server locally, usually for testing purposes.

import os
import uvicorn

if __name__ == "__main__":
    os.environ["RSLV_DB_CONNECTION_STRING"] = "sqlite:///data/n2t.db"
    uvicorn.run("n2t.app:app", host="0.0.0.0", log_level="info")

