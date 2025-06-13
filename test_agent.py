import logging
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.plugins import openai

logger = logging.getLogger("test-agent")

async def entrypoint(ctx: JobContext):
    """Test agent entry point."""
    logger.info("Test agent starting")
    await ctx.connect()
    logger.info("Test agent connected")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))