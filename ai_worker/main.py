import asyncio

from ai_worker.worker import run_worker

if __name__ == "__main__":
    asyncio.run(run_worker())
