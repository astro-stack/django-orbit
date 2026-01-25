"""
Django Orbit Health Check System

A plug-and-play module registry that tracks the health status of all Orbit components.
Each module can be enabled/disabled independently, and failures in one module
don't affect others.

Usage:
    from orbit.health import ModuleRegistry, module_registry
    
    # Register a module
    @module_registry.register("my_module", description="My custom module")
    def init_my_module():
        # Initialization code
        # Raise exception if something fails
        pass
    
    # Get status of all modules
    status = module_registry.get_all_status()
    
    # Check if a specific module is healthy
    if module_registry.is_healthy("my_module"):
        # Module is working
        pass
"""

import functools
import logging
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ModuleStatus(Enum):
    """Status of a module."""
    PENDING = "pending"      # Not yet initialized
    HEALTHY = "healthy"      # Working correctly
    DEGRADED = "degraded"    # Partially working
    FAILED = "failed"        # Completely failed
    DISABLED = "disabled"    # Disabled by config


@dataclass
class ModuleInfo:
    """Information about a registered module."""
    name: str
    description: str
    category: str
    status: ModuleStatus = ModuleStatus.PENDING
    error: Optional[str] = None
    error_traceback: Optional[str] = None
    config_key: Optional[str] = None  # Key in ORBIT_CONFIG to enable/disable
    dependencies: List[str] = field(default_factory=list)
    init_func: Optional[Callable] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "status": self.status.value,
            "is_healthy": self.status == ModuleStatus.HEALTHY,
            "is_failed": self.status == ModuleStatus.FAILED,
            "is_disabled": self.status == ModuleStatus.DISABLED,
            "error": self.error,
            "error_traceback": self.error_traceback,
            "config_key": self.config_key,
        }


class ModuleRegistry:
    """
    Central registry for all Orbit modules.
    
    Provides plug-and-play functionality where each module:
    - Can be enabled/disabled via configuration
    - Fails independently without affecting other modules
    - Reports its health status for diagnostics
    """
    
    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}
        self._initialized = False
    
    def register(
        self,
        name: str,
        description: str = "",
        category: str = "general",
        config_key: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Callable:
        """
        Decorator to register a module initialization function.
        
        Args:
            name: Unique module name
            description: Human-readable description
            category: Module category (core, watcher, integration, etc.)
            config_key: Optional ORBIT_CONFIG key to enable/disable
            dependencies: List of module names this module depends on
        
        Example:
            @module_registry.register("cache_watcher", config_key="RECORD_CACHE")
            def init_cache_watcher():
                # Initialization code
                pass
        """
        def decorator(func: Callable) -> Callable:
            self._modules[name] = ModuleInfo(
                name=name,
                description=description or f"Module: {name}",
                category=category,
                config_key=config_key,
                dependencies=dependencies or [],
                init_func=func,
            )
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return wrapper
        
        return decorator
    
    def register_module(
        self,
        name: str,
        init_func: Callable,
        description: str = "",
        category: str = "general",
        config_key: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        """
        Programmatically register a module.
        
        Args:
            name: Unique module name
            init_func: Function to initialize the module
            description: Human-readable description
            category: Module category
            config_key: Optional ORBIT_CONFIG key
            dependencies: List of dependent module names
        """
        self._modules[name] = ModuleInfo(
            name=name,
            description=description or f"Module: {name}",
            category=category,
            config_key=config_key,
            dependencies=dependencies or [],
            init_func=init_func,
        )
    
    def initialize_all(self, fail_silently: bool = True) -> Dict[str, ModuleInfo]:
        """
        Initialize all registered modules.
        
        Args:
            fail_silently: If True, log errors but don't raise exceptions
        
        Returns:
            Dict of module names to their ModuleInfo
        """
        from orbit.conf import get_config
        config = get_config()
        
        # Process modules in dependency order
        initialized = set()
        
        def init_module(name: str) -> bool:
            if name in initialized:
                return self._modules[name].status == ModuleStatus.HEALTHY
            
            module = self._modules.get(name)
            if not module:
                return False
            
            # Check dependencies first
            for dep in module.dependencies:
                if not init_module(dep):
                    module.status = ModuleStatus.FAILED
                    module.error = f"Dependency '{dep}' failed or not found"
                    return False
            
            # Check if disabled by config
            if module.config_key and not config.get(module.config_key, True):
                module.status = ModuleStatus.DISABLED
                logger.debug(f"Module '{name}' disabled via config ({module.config_key})")
                initialized.add(name)
                return True  # Disabled is not a failure
            
            # Try to initialize
            try:
                if module.init_func:
                    module.init_func()
                module.status = ModuleStatus.HEALTHY
                logger.debug(f"Module '{name}' initialized successfully")
            except Exception as e:
                module.status = ModuleStatus.FAILED
                module.error = f"{type(e).__name__}: {str(e)}"
                module.error_traceback = traceback.format_exc()
                
                if fail_silently:
                    logger.warning(f"Module '{name}' failed to initialize: {module.error}")
                else:
                    logger.error(f"Module '{name}' failed to initialize: {module.error}")
                    raise
            
            initialized.add(name)
            return module.status == ModuleStatus.HEALTHY
        
        # Initialize all modules
        for name in list(self._modules.keys()):
            init_module(name)
        
        self._initialized = True
        return self._modules.copy()
    
    def get_status(self, name: str) -> Optional[ModuleInfo]:
        """Get status of a specific module."""
        return self._modules.get(name)
    
    def get_all_status(self) -> Dict[str, ModuleInfo]:
        """Get status of all modules."""
        return self._modules.copy()
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all module statuses.
        
        Returns:
            Dict with counts and lists of modules by status
        """
        modules = list(self._modules.values())
        
        healthy = [m for m in modules if m.status == ModuleStatus.HEALTHY]
        failed = [m for m in modules if m.status == ModuleStatus.FAILED]
        disabled = [m for m in modules if m.status == ModuleStatus.DISABLED]
        degraded = [m for m in modules if m.status == ModuleStatus.DEGRADED]
        pending = [m for m in modules if m.status == ModuleStatus.PENDING]
        
        # Group by category
        by_category: Dict[str, List[ModuleInfo]] = {}
        for module in modules:
            if module.category not in by_category:
                by_category[module.category] = []
            by_category[module.category].append(module)
        
        return {
            "total": len(modules),
            "healthy_count": len(healthy),
            "failed_count": len(failed),
            "disabled_count": len(disabled),
            "degraded_count": len(degraded),
            "pending_count": len(pending),
            "all_healthy": len(failed) == 0 and len(degraded) == 0,
            "modules": [m.to_dict() for m in modules],
            "healthy": [m.to_dict() for m in healthy],
            "failed": [m.to_dict() for m in failed],
            "disabled": [m.to_dict() for m in disabled],
            "by_category": {
                cat: [m.to_dict() for m in mods]
                for cat, mods in by_category.items()
            },
        }
    
    def is_healthy(self, name: str) -> bool:
        """Check if a module is healthy."""
        module = self._modules.get(name)
        return module is not None and module.status == ModuleStatus.HEALTHY
    
    def is_initialized(self) -> bool:
        """Check if the registry has been initialized."""
        return self._initialized
    
    def set_failed(self, name: str, error: str, traceback_str: Optional[str] = None) -> None:
        """Manually mark a module as failed."""
        if name in self._modules:
            self._modules[name].status = ModuleStatus.FAILED
            self._modules[name].error = error
            self._modules[name].error_traceback = traceback_str
    
    def set_healthy(self, name: str) -> None:
        """Manually mark a module as healthy."""
        if name in self._modules:
            self._modules[name].status = ModuleStatus.HEALTHY
            self._modules[name].error = None
            self._modules[name].error_traceback = None
    
    def reset(self) -> None:
        """Reset all modules to pending status."""
        for module in self._modules.values():
            module.status = ModuleStatus.PENDING
            module.error = None
            module.error_traceback = None
        self._initialized = False


# Global module registry instance
module_registry = ModuleRegistry()


def get_health_status() -> Dict[str, Any]:
    """
    Get the health status of all Orbit modules.
    
    This is the main function to call from views.
    """
    return module_registry.get_status_summary()


def is_orbit_healthy() -> bool:
    """Check if all Orbit modules are healthy."""
    summary = module_registry.get_status_summary()
    return summary["all_healthy"]
