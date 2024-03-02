from .ai import AI
from .music import Music


async def setup(bot):
    await bot.add_cog(AI(bot))
    await bot.add_cog(Music(bot))