"""
Performance Utilities
LeadHunter AI - Caching and Optimization Middleware

Features:
- CacheMiddleware: Automatic caching for GET requests
- Response compression helpers
"""
import time
import hashlib
import json
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import ORJSONResponse
from backend.core.cache_manager import cache
from backend.utils.logger import logger

class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware to cache GET requests.
    
    Enable by setting 'X-Cache-Enabled: true' header or configuring routes.
    """
    
    def __init__(
        self, 
        app, 
        ttl: int = 60, 
        enabled_routes: list = None
    ):
        super().__init__(app)
        self.ttl = ttl
        self.enabled_routes = enabled_routes or []
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
            
        # Check if caching is enabled for this request
        should_cache = False
        path = request.url.path
        
        # Check routes
        for route in self.enabled_routes:
            if path.startswith(route):
                should_cache = True
                break
                
        # Check header
        if request.headers.get("X-Cache-Enabled") == "true":
            should_cache = True
            
        # Bypass cache if requested
        if request.headers.get("Cache-Control") == "no-cache":
            should_cache = False
            
        if not should_cache:
            return await call_next(request)
            
        # Generate cache key
        # Key = Method + URL + Query Params + Auth (if present)
        key_parts = [
            request.method,
            str(request.url),
            request.headers.get("Authorization", "")
        ]
        key_str = "|".join(key_parts)
        cache_key = hashlib.md5(key_str.encode()).hexdigest()
        
        # Check cache
        cached_response = cache.get(cache_key, cache_type="default")
        
        if cached_response:
            logger.debug(f"Middleware Cache HIT: {path}")
            return ORJSONResponse(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers={"X-Cache": "HIT"}
            )
            
        # Execute request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Cache response if successful JSON
        if response.status_code == 200:
            # We need to read the response body, which can consume the stream
            # This is tricky with StreamingResponse. 
            # For now, we only cache application/json responses that are not streaming
            
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    # Read body
                    body = [section async for section in response.body_iterator]
                    
                    # Reconstruct body for response as async iterator
                    async def async_body_iterator():
                        for chunk in body:
                            yield chunk
                            
                    response.body_iterator = async_body_iterator()
                    
                    json_content = json.loads(b"".join(body))
                    
                    cache_data = {
                        "content": json_content,
                        "status_code": response.status_code
                    }
                    
                    # Store in cache
                    cache.set(cache_key, cache_data, ttl=self.ttl)
                    
                    # Add hit/miss header
                    response.headers["X-Cache"] = "MISS"
                    response.headers["X-Process-Time"] = str(process_time)
                    
                except Exception as e:
                    logger.warning(f"Failed to cache response: {e}")
                    
        return response
