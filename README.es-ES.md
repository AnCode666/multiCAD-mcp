

# multiCAD-mcp

Controla tus aplicaciones CAD con tu asistente de IA a través del Protocolo de Contexto de Modelo (MCP).

[![Documentación](https://img.shields.io/badge/docs-mkdocs--material-blue?logo=readthedocs)](https://AnCode666.github.io/multiCAD-mcp/)
[![Licencia](https://img.shields.io/github/license/AnCode666/multiCAD-mcp)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP%202.0-green)](https://github.com/jlowin/fastmcp)

**Documentación**: https://AnCode666.github.io/multiCAD-mcp/

## ¿Qué es multiCAD-mcp?

multiCAD-mcp es un servidor MCP que te permite controlar tu software CAD utilizando asistentes de IA como Claude para escritorio o Cursor. Ya sea que estés dibujando formas, gestionando capas, automatizando tareas repetitivas o realizando tareas complejas, puedes hacerlo todo a través de instrucciones basadas en texto.

## Características

- **Compatibilidad con múltiples CAD**: Funciona con AutoCAD®, ZWCAD®, GstarCAD® y BricsCAD®
- **7 Herramientas MCP Unificadas**: Acceso limpio a **56 comandos CAD** para dibujo, capas, entidades, bloques y archivos
- **Atributos de Bloques** (v0.2.0+): Leer y escribir valores de atributos de bloques
- **Creación de Bloques**: Crea bloques a partir de entidades o selección del usuario
- **Ejecución de comandos simples**: "Dibuja un círculo rojo en 50,50 con radio 25" - no se necesita sintaxis compleja
- **Ejecución de tareas complejas**: "Dibuja el gráfico de y = sen(X) y etiqueta los ejes"
- **Integración simple**: Funciona con Claude, Cursor, VS Code y cualquier cliente compatible con MCP
- **Rápido y fiable**: Arquitectura eficiente basada en COM para control CAD en tiempo real
- **Flexible**: Llamadas directas a herramientas o lenguaje natural - elige lo que mejor te funcione

## Requisitos del Sistema

- **Sistema operativo Windows** (obligatorio - utiliza la tecnología COM de Windows)
- **Python 3.10 o superior**
- **Una o más aplicaciones CAD** instaladas en tu computadora

## Instalación

Las instrucciones detalladas de instalación están disponibles en [docs/01-SETUP.md](docs/01-SETUP.md).

Inicio rápido:

```powershell
# Instalar uv (si no está instalado)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Clonar
git clone https://github.com/AnCode666/multiCAD-mcp.git
cd multiCAD-mcp
uv sync --dev
uv run python -m pip install --upgrade pywin32
```

## Configuración con Claude Desktop

Agrega esto a tu `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "multiCAD": {
      "command": "C:\\path\\to\\multiCAD-mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\multiCAD-mcp\\src\\server.py"]
    }
  }
}
```

**Importante**: Usa la ruta completa al intérprete de Python en tu entorno virtual (`.venv\Scripts\python.exe`), no el comando del sistema `py`. Esto asegura que Claude Desktop utilice el entorno de Python correcto con todas las dependencias requeridas instaladas.

Reemplaza `C:\path\to\multiCAD-mcp` con tu ruta de instalación real.

## Ejemplos de Uso

### Llamadas Directas a Herramientas

multiCAD-mcp proporciona **7 herramientas MCP unificadas** que ofrecen acceso a **56 comandos CAD diferentes**. Esta arquitectura está diseñada para alta eficiencia, permitiendo que múltiples operaciones se despachen en una sola llamada, reduciendo la sobrecarga de la API hasta en un 70%.

- **Dibujo y Formas**: Líneas, círculos, arcos, rectángulos, polilíneas, curvas spline y tablas.
- **Gestión de Bloques**: Crear bloques (desde entidades o selección), insertar (por lotes/individual), listar y auditoría.
- **Gestión de Capas**: Crear, listar, renombrar/eliminar (por lotes) y alternar visibilidad.
- **Manipulación de Entidades**: Mover, rotar, escalar, copiar/pegar y selección (por tipo/capa/color).
- **Gestión de Propiedades**: Cambiar color/capa (por lotes/individual) y establecer color PorCapa (ByLayer).
- **Datos y Exportación**: Extraer datos (JSON), exportar a Excel (total o seleccionado) y depuración de entidades.
- **Vista y Navegación**: Zoom a extents, ajustar vista y operaciones deshacer/rehacer.
- **Archivos y Sesión**: Guardar (DWG/DXF/PDF), nuevos/cerrar dibujos y cambio entre múltiples dibujos.
- **Conexión y Control**: Ciclo de vida de conexión, diagnósticos y recuperación por lenguaje natural.

> [!TIP]
> Cada herramienta acepta múltiples operaciones en una sola llamada utilizando un formato abreviado compacto, reduciendo la sobrecarga de la API hasta en un 70%.

### Exportación de Entidades Seleccionadas

Exporta o extrae datos solo de las entidades actualmente seleccionadas en tu ventana gráfica de CAD:

```text
# Exportar entidades seleccionadas a Excel
export_data(scope="selected", format="excel", filename="selected_entities.xlsx")

# Extraer datos de entidades seleccionadas como JSON
export_data(scope="selected", format="json")
```

### Tareas Complejas

Puedes pedirle a tu asistente de IA que ejecute tareas complejas que requieren múltiples herramientas, como dibujar gráficos de ecuaciones, bloques de título complejos o tablas de datos.

## Configuración

Edita `src/config.json` para personalizar:

```json
{
  "logging_level": "INFO",
  "cad": {
    "autocad": {
      "startup_wait_time": 20,
      "command_delay": 0.5
    }
  },
  "dashboard": {
    "port": 8888
  },
  "output": {
    "directory": "~/Documents/multiCAD Exports",
    "allow_arbitrary_paths": true
  }
}
```

**Ajustes clave**:

- **`logging_level`**: Establece `DEBUG`, `INFO`, `WARNING` o `ERROR` para controlar la verbosidad de los registros
- **`startup_wait_time`**: Segundos de espera para que la aplicación CAD inicie (aumenta si el CAD es lento)
- **`command_delay`**: Retardo entre comandos en segundos
- **`dashboard.port`**: Puerto del panel web (predeterminado: 8888)
- **`open_dashboard`**: [host, port] — abre el panel web en el navegador (predeterminado desde config.json: 8888)
- **`output.directory`**: Directorio predeterminado para dibujos guardados y exportaciones
- **`output.allow_arbitrary_paths`**: Establece `true` para permitir guardar archivos en cualquier ruta absoluta del sistema, omitiendo las comprobaciones de prevención de travesía de rutas.

## Solución de Problemas

### Revisión de Registros (Logs)

multiCAD-mcp genera registros detallados para ayudar a diagnosticar problemas:

**Ubicación del Registro**: `logs/multicad_mcp.log` (se crea automáticamente en el directorio `logs/` del proyecto)

**Ver registros**:

```powershell
# Ver las últimas 50 entradas del registro
Get-Content logs/multicad_mcp.log -Tail 50

# Ver todos los registros
Get-Content logs/multicad_mcp.log

# Monitorear registros en tiempo real (se actualiza automáticamente)
Get-Content logs/multicad_mcp.log -Wait -Tail 10
```

**Ajustar el nivel de registro** en `src/config.json`:

```json
{
  "logging_level": "DEBUG"
}
```

Niveles disponibles (de mayor a menor verbosidad):

- `DEBUG`: Información detallada para diagnosticar problemas
- `INFO`: Mensajes informativos generales (predeterminado)
- `WARNING`: Mensajes de advertencia para posibles problemas
- `ERROR`: Solo mensajes de error

**Nota**: Reinicia el servidor MCP después de cambiar la configuración.

### "Conexión fallida"

- Asegúrate de que tu aplicación CAD se esté ejecutando
- Verifica que tengas la versión correcta instalada
- Comprueba que Windows COM esté configurado correctamente
- Usa `manage_session` con `{"action": "status"}` para diagnosticar el problema
- Revisa los registros para ver mensajes de error detallados (ver arriba)

El panel ofrece una vista en tiempo real del estado del CAD. Puedes actualizar manualmente los datos usando el botón "Actualizar ahora".

- **Puerto del Panel**: Cambia `dashboard.port` en `src/config.json` a tu puerto preferido.
- **Actualización Manual**: Haz clic en el botón de actualizar para sincronizar con el estado actual del CAD.

### "No conectado"

- El servidor se conecta automáticamente en el primer uso
- Si falla, reinicia la aplicación CAD e inténtalo de nuevo
- Usa `manage_session` con `{"action": "connect"}` para restablecer la conexión
- Revisa los registros para identificar problemas de conexión

### Los comandos no funcionan

- Revisa la línea de comandos de tu aplicación CAD en busca de mensajes o errores
- Asegúrate de que las coordenadas estén en un formato válido (p. ej., "0,0" para 2D, "0,0,0" para 3D)
- Verifica el estado de la conexión con `manage_session` → `{"action": "status"}`
- Habilita el registro en modo DEBUG para ver información detallada de la ejecución de comandos

## Documentación

- [**Configuración e Instalación**](docs/01-SETUP.md) - guía detallada de configuración e integración con Claude Desktop.
- [**Arquitectura**](docs/02-ARCHITECTURE.md) - diseño del sistema y guía de extensión.
- [**Solución de Problemas**](docs/04-TROUBLESHOOTING.md) - soluciones para problemas comunes.
- [**Referencia**](docs/05-REFERENCE.md) - referencia completa de herramientas MCP.
- [**Registro de Cambios**](docs/07-CHANGELOG.md) - historial de versiones.

## Aplicaciones CAD Compatibles

| Aplicación | Estado | Notas |
|------------|--------|-------|
| AutoCAD 2018+ | ✅ Soporte Completo | Implementación principal |
| ZWCAD 2020+ | ✅ Soporte Completo | Usa API compatible con AutoCAD |
| GstarCAD 2020+ | ✅ Soporte Completo | Usa API compatible con AutoCAD |
| BricsCAD 21+ | ✅ Soporte Completo | Usa API compatible con AutoCAD |

## Estado del Proyecto

**Versión 0.2.0** - Arquitectura de herramientas unificadas, gestión de atributos de bloques y empaquetado moderno.

## Licencia

Apache License 2.0 - consulta el archivo [LICENSE](LICENSE) para obtener más detalles.

## Agradecimientos

Este proyecto se basa en:
- [CAD-MCP](https://github.com/daobataotie/CAD-MCP)
- [Easy-MCP-AutoCAD](https://github.com/zh19980811/Easy-MCP-AutoCad)

## Soporte

Para informar problemas, preguntas o solicitudes de funciones, abre un issue en el repositorio.

---

**¿Necesitas ayuda con la configuración?** Comienza con los pasos de instalación anteriores.
