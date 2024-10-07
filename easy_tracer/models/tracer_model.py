from pathlib import Path
from typing import Dict


class TracerModel:
    """Model for handling tracing operations."""

    def __init__(self) -> None:
        """Initialize the TracerModel."""
        self.config: Dict[str, str] = {}
        self.is_tracing: bool = False
        self.output_file: Path = Path()

    def set_config(self, config: Dict[str, str]) -> None:
        """Set the configuration for tracing.

        Args:
            config: A dictionary containing tracing configuration.
        """
        self.config = config

    def start_trace(self) -> str:
        """Start a tracing operation.

        Returns:
            A string message indicating the result of the operation.
        """
        if self.is_tracing:
            return "Trace is already running."
        
        # Simulate starting a trace
        tracer_type = self.config['tracer_type']
        trace_time = self.config['trace_time']
        time_unit = self.config['time_unit']
        output_folder = Path(self.config['output_folder'])
        
        # Generate a fake output file path
        self.output_file = output_folder / f"trace_{tracer_type}_{trace_time}{time_unit}.txt"
        
        self.is_tracing = True
        return f"Trace started. Output file will be: {self.output_file}"

    def stop_trace(self) -> str:
        """Stop the current tracing operation.

        Returns:
            A string message indicating the result of the operation.
        """
        if not self.is_tracing:
            return "No trace is currently running."
        
        self.is_tracing = False
        return f"Trace stopped. Output file: {self.output_file}"