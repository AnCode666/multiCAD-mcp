# Plan: Migrar multiCAD-mcp a MCP Apps

## Resumen

Migrar el servidor MCP existente para soportar MCP Apps, añadiendo recursos UI interactivos a herramientas seleccionadas mientras se mantiene compatibilidad hacia atrás.

---

## 1. Dependencia a Añadir

**Archivo:** `requirements.txt`

```
# MCP Apps UI Support
mcp-ui-server>=1.0.0
```

---

## 2. Nueva Estructura de Archivos

```
src/
├── ui/                          # NUEVO: Módulo de recursos UI
│   ├── __init__.py
│   ├── resources.py             # Registro y factory de recursos UI
│   └── templates/               # Plantillas HTML
│       ├── drawing_viewer.html  # Visor de datos de dibujo
│       ├── layer_panel.html     # Panel de capas
│       └── block_browser.html   # Explorador de bloques
```

---

## 3. Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `requirements.txt` | Añadir `mcp-ui-server>=1.0.0` |
| `src/server.py` | Registrar recursos UI |
| `src/mcp_tools/decorators.py` | Añadir decorator `cad_tool_with_ui` |
| `src/mcp_tools/tools/export.py` | Añadir UI a `extract_drawing_data` |
| `src/mcp_tools/tools/layers.py` | Añadir tool `get_layers_info` con UI |
| `src/mcp_tools/tools/blocks.py` | Añadir UI a `list_blocks` |

---

## 4. Implementación por Fases

### Fase 1: Infraestructura (Prioridad Alta)

1. **Añadir dependencia** en `requirements.txt`

2. **Crear módulo `src/ui/`** con:
   - `__init__.py` - Exports
   - `resources.py` - Factory `create_cad_ui_resource()`

3. **Crear decorator `cad_tool_with_ui`** en `decorators.py`:
   ```python
   def cad_tool_with_ui(mcp, operation_name, ui_resource=None):
       """Decorator que añade soporte UI a herramientas CAD."""
   ```

4. **Registrar recursos UI** en `server.py`:
   ```python
   def register_ui_resources():
       from ui.resources import register_all_ui_resources
       register_all_ui_resources(mcp)
   ```

### Fase 2: Herramientas con UI (Prioridad Media)

| Orden | Herramienta | Recurso UI | Descripción |
|-------|-------------|------------|-------------|
| 1 | `extract_drawing_data` | `drawing_viewer` | Tabla de entidades con filtros y estadísticas |
| 2 | `get_layers_info` (nueva) | `layer_panel` | Lista de capas con colores y visibilidad |
| 3 | `list_blocks` | `block_browser` | Catálogo de bloques con conteo de referencias |

### Fase 3: UIs Adicionales (Opcional)

- `get_selection_info` → Inspector de selección
- `export_drawing_to_excel` → Vista previa de exportación

---

## 5. Diseño de UI: Drawing Viewer

**URI:** `ui://multicad/drawing_viewer`

**Características:**
- Estadísticas: total entidades, capas usadas, tipos
- Filtros: búsqueda por handle/tipo/capa
- Tabla: Handle, Tipo, Capa, Color, Longitud, Área
- Tema oscuro (compatible con Claude Desktop)

**Estructura HTML:**
```html
<!DOCTYPE html>
<html>
<head>
    <style>/* Estilos dark theme */</style>
</head>
<body>
    <div class="summary"><!-- Stats cards --></div>
    <div class="filter-bar"><!-- Search + filters --></div>
    <table id="entities-table"><!-- Data table --></table>
    <script>
        const entityData = /*DATA_PLACEHOLDER*/[];
        // Render + filter logic
    </script>
</body>
</html>
```

---

## 6. Código Clave

### `src/ui/resources.py`

```python
from mcp_ui_server import create_ui_resource
from mcp_ui_server.core import UIResource
import json

def create_cad_ui_resource(
    resource_name: str,
    data: dict,
    template: str
) -> UIResource:
    """Crea un recurso UI para visualización CAD."""
    html = template.replace("/*DATA_PLACEHOLDER*/[]", json.dumps(data))

    return create_ui_resource({
        "uri": f"ui://multicad/{resource_name}",
        "content": {"type": "rawHtml", "htmlString": html},
        "encoding": "text"
    })
```

### `src/mcp_tools/decorators.py` (nuevo decorator)

```python
def cad_tool_with_ui(mcp: FastMCP, operation_name: str, ui_resource: str = None):
    """Decorator para herramientas con soporte UI."""
    def decorator(func):
        @wraps(func)
        def wrapper(ctx: Context, *args, cad_type: Optional[str] = None, **kwargs):
            from adapters.adapter_manager import get_adapter
            try:
                set_current_adapter(get_adapter(cad_type))
                return func(ctx, *args, **kwargs)
            except CADOperationError:
                raise
            except Exception as e:
                raise CADOperationError(operation_name, str(e))

        # Registrar con metadatos UI
        tool_meta = {}
        if ui_resource:
            tool_meta["ui"] = {"resourceUri": f"ui://multicad/{ui_resource}"}

        return mcp.tool(meta=tool_meta)(wrapper)
    return decorator
```

---

## 7. Compatibilidad

- **Sin cambios breaking**: Tools existentes siguen funcionando igual
- **UI es opt-in**: Hosts sin soporte MCP Apps ignoran `_meta.ui`
- **Salida JSON sin cambios**: Mismo formato de respuesta

---

## 8. Verificación

### Tests
```powershell
pytest tests/ -v
```

### MCP Inspector (sin UI)
```powershell
npx -y @modelcontextprotocol/inspector py src/server.py
```

### Verificar metadatos UI
- Llamar herramienta y verificar que `_meta.ui.resourceUri` está presente
- Hosts compatibles (Claude Desktop, VS Code) renderizan el iframe

---

## 9. Archivos Críticos

1. `src/server.py` - Registro de recursos UI
2. `src/mcp_tools/decorators.py` - Nuevo decorator `cad_tool_with_ui`
3. `src/ui/resources.py` - Factory de recursos UI (NUEVO)
4. `src/ui/templates/drawing_viewer.html` - Template principal (NUEVO)
5. `src/mcp_tools/tools/export.py` - Migrar `extract_drawing_data`
6. `requirements.txt` - Añadir `mcp-ui-server`

---

## 10. Orden de Implementación

1. Añadir `mcp-ui-server` a `requirements.txt`
2. Crear `src/ui/__init__.py` y `src/ui/resources.py`
3. Crear `src/ui/templates/drawing_viewer.html`
4. Añadir `cad_tool_with_ui` a `decorators.py`
5. Modificar `extract_drawing_data` para usar el nuevo decorator
6. Registrar recursos UI en `server.py`
7. Ejecutar tests y verificar con MCP Inspector
8. Crear templates adicionales (layer_panel, block_browser)
