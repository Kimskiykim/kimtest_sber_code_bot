from sqlalchemy.ext.asyncio import create_async_engine

def get_engine(url):
    return create_async_engine(url=url, pool_pre_ping=True, pool_size=10)

