from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

def setup_logging(log_dir: str = "logs", level: int = logging.INFO) -> logging.Logger:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    logger = logging.getLogger("energy_trading_lab")
    logger.setLevel(level)
    logger.propagate = False
    
    if logger.handlers:
        logger.handlers.clear()
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    file_name = f"energy_trading_lab_{datetime.now().strftime('%Y%m%d')}.log"
    file_path = Path(log_dir) / file_name
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(log_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

class APIError(Exception):
    def __init__(self, message: str, code: int = 500, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

class ValidationError(APIError):
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, code=400)
        self.field = field
        if field:
            self.details["field"] = field

class ResourceNotFoundError(APIError):
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(f"{resource_type} not found: {resource_id}", code=404)
        self.details["resource_type"] = resource_type
        self.details["resource_id"] = resource_id

class AuthenticationError(APIError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code=401)

class AuthorizationError(APIError):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, code=403)

def log_api_request(endpoint: str, method: str, status_code: int, duration_ms: float):
    logger = logging.getLogger("energy_trading_lab")
    logger.info(f"API Request: {method} {endpoint} - Status: {status_code} - Duration: {duration_ms:.2f}ms")

def log_error(error: Exception, context: Optional[dict] = None):
    logger = logging.getLogger("energy_trading_lab")
    if context:
        context_str = " ".join(f"{k}={v}" for k, v in context.items())
        logger.error(f"Error: {str(error)} | Context: {context_str}", exc_info=True)
    else:
        logger.error(f"Error: {str(error)}", exc_info=True)

def log_job_event(job_id: str, event: str, details: Optional[dict] = None):
    logger = logging.getLogger("energy_trading_lab")
    details_str = ""
    if details:
        details_str = f" | {details}"
    logger.info(f"Job {job_id}: {event}{details_str}")

def log_metrics(metrics: dict):
    logger = logging.getLogger("energy_trading_lab")
    logger.info(f"Metrics: {metrics}")
