import asyncio
from unittest.mock import MagicMock
import numpy as np

async def test():
    embed = MagicMock(return_value=np.zeros(384))
    res = await asyncio.to_thread(embed, "test")
    print("res:", type(res), res)
    print("tolist:", type(res.tolist()))

asyncio.run(test())
