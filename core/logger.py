import logging
import sys

from core.utils import IST

def setup_logger(name="sensex_scalping", level=logging.INFO, log_filename="trading.log"):
    """
    Sets up a logger with a stream handler to stdout and a file handler.
    
    Args:
        name (str): The name of the logger.
        level (int): The logging level.
        log_filename (str): Name of the file inside logs/ to write to.
        
    Returns:
        logging.Logger: The configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding multiple handlers if setup_logger is called multiple times
    if not logger.handlers:
        import os
        from datetime import datetime
        
        # Use absolute path for logs to avoid ambiguity
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(project_root, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, log_filename)
        
        # Custom formatter that uses IST
        class ISTFormatter(logging.Formatter):
            def formatTime(self, record, datefmt=None):
                dt = datetime.fromtimestamp(record.created, IST)
                if datefmt:
                    return dt.strftime(datefmt)
                return dt.isoformat(sep=" ", timespec="milliseconds")

        formatter = ISTFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        print(f"Logging initialized at: {log_file} (IST)")
        
    return logger
