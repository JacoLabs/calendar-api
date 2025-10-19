"""
Enhanced health check service with dependency monitoring.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Optional
import asyncio

from .models import HealthResponse

logger = logging.getLogger(__name__)


class HealthChecker:
    """Service health monitoring."""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_llm_check = None
        self.llm_status = "unknown"
        self.parser_status = "unknown"
    
    async def get_health_status(self) -> HealthResponse:
        """Get comprehensive health status."""
        current_time = datetime.utcnow()
        uptime = time.time() - self.start_time
        
        # Check service dependencies
        services = await self._check_services()
        
        # Determine overall status
        overall_status = self._determine_overall_status(services)
        
        return HealthResponse(
            status=overall_status,
            timestamp=current_time.isoformat(),
            version="1.0.0",
            services=services,
            uptime_seconds=uptime
        )
    
    async def _check_services(self) -> Dict[str, str]:
        """Check status of dependent services."""
        services = {}
        
        # Check parser service
        try:
            # Import here to avoid circular imports
            import sys
            import os
            
            # Add parent directories to path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(os.path.dirname(current_dir))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            from services.event_parser import EventParser
            
            # Quick parser test
            parser = EventParser()
            test_result = parser.parse_text("test meeting tomorrow")
            services["parser"] = "healthy" if test_result else "degraded"
            
        except Exception as e:
            logger.warning(f"Parser health check failed: {e}")
            services["parser"] = "unhealthy"
        
        # Check LLM service
        services["llm"] = await self._check_llm_service()
        
        # Check system resources
        services["memory"] = self._check_memory()
        services["disk"] = self._check_disk()
        
        return services
    
    async def _check_llm_service(self) -> str:
        """Check LLM service availability."""
        try:
            # Only check LLM every 30 seconds to avoid overhead
            current_time = time.time()
            if (self.last_llm_check and 
                current_time - self.last_llm_check < 30):
                return self.llm_status
            
            # Import LLM service
            import sys
            import os
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(os.path.dirname(current_dir))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            try:
                from services.llm_service import LLMService
                # Just check if service can be instantiated
                # Don't actually test parsing in health check
                llm_service = LLMService()
                self.llm_status = "healthy"
            except ImportError:
                # LLM service not available (missing dependencies)
                self.llm_status = "unavailable"
            except Exception as e:
                logger.warning(f"LLM service initialization failed: {e}")
                self.llm_status = "unavailable"
            
            self.last_llm_check = current_time
            return self.llm_status
            
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            self.llm_status = "unavailable"
            return self.llm_status
    
    def _check_memory(self) -> str:
        """Check memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                return "critical"
            elif memory.percent > 85:  # Changed from 75 to 85
                return "warning"
            else:
                return "healthy"
        except ImportError:
            # psutil not available
            return "unknown"
        except Exception:
            return "unknown"
    
    def _check_disk(self) -> str:
        """Check disk usage."""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            usage_percent = (disk.used / disk.total) * 100
            if usage_percent > 90:
                return "critical"
            elif usage_percent > 80:
                return "warning"
            else:
                return "healthy"
        except ImportError:
            return "unknown"
        except Exception:
            return "unknown"
    
    def _determine_overall_status(self, services: Dict[str, str]) -> str:
        """Determine overall service status."""
        # Critical services that affect overall status
        critical_services = ["parser"]
        
        # Check critical services
        for service in critical_services:
            if services.get(service) == "unhealthy":
                return "unhealthy"
        
        # Check for degraded services
        degraded_count = sum(1 for status in services.values() 
                           if status in ["degraded", "warning", "slow"])
        
        if degraded_count > 0:
            return "degraded"
        
        # Check for unknown services
        unknown_count = sum(1 for status in services.values() 
                          if status == "unknown")
        
        if unknown_count > len(services) // 2:
            return "unknown"
        
        return "healthy"


# Global health checker instance
health_checker = HealthChecker()