import logging
import sys

def setup_logger(name="sensex_scalping", level=logging.INFO):
    """
    Sets up a logger with a stream handler to stdout.
    
    Args:
        name (str): The name of the logger.
        level (int): The logging level.
        
    Returns:
        logging.Logger: The configured logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding multiple handlers if setup_logger is called multiple times
    if not logger.handlers:
        import os
        # Use absolute path for logs to avoid ambiguity
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(project_root, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "trading.log")
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        print(f"Logging initialized at: {log_file}")
        
    return logger
