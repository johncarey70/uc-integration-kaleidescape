"""
Public stub module.
"""

class KsEventClient:
    def __init__(self, *args, **kwargs):
        pass

    async def start(self):
        raise RuntimeError("Backend not included in public repository")

    async def stop(self):
        pass
