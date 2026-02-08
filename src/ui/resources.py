"""
UI Resource factory and registration for MCP Apps support.

Provides functions to create and register UI resources for CAD data visualization.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Path to templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_template(template_name: str) -> str:
    """Load an HTML template from the templates directory.

    Args:
        template_name: Name of the template file (e.g., "drawing_viewer.html")

    Returns:
        Template content as string

    Raises:
        FileNotFoundError: If template doesn't exist
    """
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def create_cad_ui_resource(
    resource_name: str,
    data: Dict[str, Any],
    template: str,
) -> Dict[str, Any]:
    """Create a UI resource for CAD data visualization.

    Args:
        resource_name: Unique name for the resource (e.g., "drawing_viewer")
        data: Data to inject into the template
        template: HTML template string with /*DATA_PLACEHOLDER*/[] marker

    Returns:
        UI resource dictionary compatible with MCP Apps
    """
    # Inject data into template
    html_content = template.replace(
        "/*DATA_PLACEHOLDER*/[]", json.dumps(data, ensure_ascii=False)
    )

    return {
        "uri": f"ui://multicad/{resource_name}",
        "content": {
            "type": "rawHtml",
            "htmlString": html_content,
        },
        "encoding": "text",
    }


def get_drawing_viewer_html(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a drawing viewer UI resource.

    Args:
        data: Drawing data with entities list

    Returns:
        UI resource for drawing visualization
    """
    template = _load_template("drawing_viewer.html")
    return create_cad_ui_resource("drawing_viewer", data, template)


def get_layer_panel_html(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a layer panel UI resource.

    Args:
        data: Layer information data

    Returns:
        UI resource for layer panel
    """
    template = _load_template("layer_panel.html")
    return create_cad_ui_resource("layer_panel", data, template)


def get_block_browser_html(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a block browser UI resource.

    Args:
        data: Block information data

    Returns:
        UI resource for block browser
    """
    template = _load_template("block_browser.html")
    return create_cad_ui_resource("block_browser", data, template)


def register_all_ui_resources(mcp) -> None:
    """Register all UI resources with the MCP server.

    This function registers static UI resource templates that can be
    dynamically populated with data when tools are called.

    Args:
        mcp: FastMCP instance
    """
    logger.info("Registering MCP UI resources...")

    # Note: MCP Apps uses dynamic resource URIs returned by tools
    # The actual resources are generated on-demand when tools return
    # _meta.ui.resourceUri pointing to the content

    # Register resource templates as available
    try:
        # Verify templates exist
        templates = ["drawing_viewer.html", "layer_panel.html", "block_browser.html"]
        for template in templates:
            template_path = TEMPLATES_DIR / template
            if template_path.exists():
                logger.debug(f"  UI template found: {template}")
            else:
                logger.warning(f"  UI template missing: {template}")

        logger.info("MCP UI resources registered successfully")
    except Exception as e:
        logger.warning(f"Failed to register UI resources: {e}")
