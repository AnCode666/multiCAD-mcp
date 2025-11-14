"""
Centralized configuration for multiCAD-MCP server.
Loads from config.json with fallback defaults.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from .exceptions import ConfigError


@dataclass
class CADConfig:
    """Configuration for a specific CAD application."""

    type: str  # AUTOCAD, ZWCAD, GCAD or BRICSCAD
    prog_id: str  # COM ProgID for Windows
    startup_wait_time: float  # Seconds to wait for CAD to start


@dataclass
class OutputConfig:
    """Configuration for output files."""

    directory: str  # Where to save generated DWG files
    format: str  # File format (dwg, dxf, etc.)


@dataclass
class NLPConfig:
    """Configuration for NLP processor."""

    default_language: str  # en, es, etc.
    supported_languages: List[str]
    strict_mode: bool  # Require exact parameter matches or allow defaults


@dataclass
class ServerConfig:
    """Complete server configuration."""

    cad: Dict[str, CADConfig]
    output: OutputConfig
    nlp: NLPConfig
    logging_level: str = "INFO"
    debug: bool = False


class ConfigManager:
    """Manages loading and accessing configuration."""

    _instance: Optional["ConfigManager"] = None
    _config: Optional[ServerConfig] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton (useful for testing)."""
        cls._instance = None
        cls._config = None

    def _load_config(self) -> None:
        """Load configuration from config.json or use defaults."""
        config_path = self._find_config_file()

        if config_path and config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_dict = json.load(f)
                self._config = self._parse_config(config_dict)
            except json.JSONDecodeError as e:
                raise ConfigError(str(config_path), f"Invalid JSON: {e}")
            except Exception as e:
                raise ConfigError(str(config_path), str(e))
        else:
            self._config = self._get_default_config()

    @staticmethod
    def _find_config_file() -> Optional[Path]:
        """Find config.json in common locations."""
        # Current working directory
        if Path("config.json").exists():
            return Path("config.json")

        # Same directory as this file (src/core/)
        core_dir = Path(__file__).parent
        if (core_dir / "config.json").exists():
            return core_dir / "config.json"

        # src/ directory
        src_dir = core_dir.parent
        if (src_dir / "config.json").exists():
            return src_dir / "config.json"

        # Project root
        project_root = src_dir.parent
        if (project_root / "config.json").exists():
            return project_root / "config.json"

        return None

    @staticmethod
    def _get_default_config() -> ServerConfig:
        """Return default configuration."""
        return ServerConfig(
            cad={
                "autocad": CADConfig(
                    type="AUTOCAD",
                    prog_id="AutoCAD.Application",
                    startup_wait_time=20.0,
                ),
                "zwcad": CADConfig(
                    type="ZWCAD",
                    prog_id="ZWCAD.Application",
                    startup_wait_time=15.0,
                ),
                "gcad": CADConfig(
                    type="GCAD",
                    prog_id="GCAD.Application",
                    startup_wait_time=15.0,
                ),
                "bricscad": CADConfig(
                    type="BRICSCAD",
                    prog_id="BricscadApp.AcadApplication",
                    startup_wait_time=15.0,
                ),
            },
            output=OutputConfig(
                directory="~/Documents/multiCAD Exports",
                format="dwg",
            ),
            nlp=NLPConfig(
                default_language="en",
                supported_languages=["en", "es"],
                strict_mode=False,
            ),
            logging_level="INFO",
            debug=False,
        )

    @staticmethod
    def _parse_config(config_dict: Dict[str, Any]) -> ServerConfig:
        """Parse raw config dictionary into ServerConfig dataclass."""
        try:
            # Parse CAD configs
            cad_configs = {}
            for cad_name, cad_dict in config_dict.get("cad", {}).items():
                cad_configs[cad_name] = CADConfig(
                    type=cad_dict.get("type", cad_name.upper()),
                    prog_id=cad_dict.get("prog_id", ""),
                    startup_wait_time=float(cad_dict.get("startup_wait_time", 20.0)),
                )

            # Parse output config
            output_dict = config_dict.get("output", {})
            output = OutputConfig(
                directory=output_dict.get("directory", "./drawings"),
                format=output_dict.get("format", "dwg"),
            )

            # Parse NLP config
            nlp_dict = config_dict.get("nlp", {})
            nlp = NLPConfig(
                default_language=nlp_dict.get("default_language", "en"),
                supported_languages=nlp_dict.get("supported_languages", ["en", "zh"]),
                strict_mode=nlp_dict.get("strict_mode", False),
            )

            return ServerConfig(
                cad=cad_configs,
                output=output,
                nlp=nlp,
                logging_level=config_dict.get("logging_level", "INFO"),
                debug=config_dict.get("debug", False),
            )
        except Exception as e:
            raise ConfigError("config.json", f"Parse error: {e}")

    @property
    def config(self) -> ServerConfig:
        """Get the loaded configuration."""
        if self._config is None:
            self._load_config()
        # _config is guaranteed to be non-None after _load_config()
        assert self._config is not None
        return self._config

    def get_cad_config(self, cad_type: str) -> CADConfig:
        """Get configuration for a specific CAD application."""
        config = self.config.cad.get(cad_type.lower())
        if config is None:
            raise ConfigError(
                "config.json",
                f"CAD type '{cad_type}' not configured. "
                f"Available: {list(self.config.cad.keys())}",
            )
        return config

    def get_supported_cads(self) -> List[str]:
        """Get list of supported CAD applications."""
        return list(self.config.cad.keys())

    def ensure_output_directory(self) -> Path:
        """Ensure output directory exists, create if needed."""
        output_dir = Path(self.config.output.directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir


# Singleton instance
_config_manager = ConfigManager()


def get_config() -> ServerConfig:
    """Get global configuration instance."""
    return _config_manager.config


def get_cad_config(cad_type: str) -> CADConfig:
    """Get CAD-specific configuration."""
    return _config_manager.get_cad_config(cad_type)


def get_supported_cads() -> List[str]:
    """Get list of supported CAD applications."""
    return _config_manager.get_supported_cads()
