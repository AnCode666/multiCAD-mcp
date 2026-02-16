import json
from pathlib import Path
from typing import Dict, List, Any, Union
from datetime import datetime
from collections import defaultdict


# Base path for BC3 helper files
BASE_PATH = Path(__file__).parent / 'resources' / 'bc3_helper_files'


class IFC2BC3Converter:
    """
    Converts IFC structures (JSON) to BC3 format for construction budgets.

    Architecture:
    - Loads and validates input data (IFC structure, quantities, prices)
    - Generates chapter hierarchy from IFC spatial structure
    - Groups building elements into budget items by type
    - Exports to FIEBDC-3 (BC3) format with windows-1252 encoding

    Method Groups:
    1. Initialization & Configuration Loading
    2. Data Parsing & Indexing
    3. Code Generation & Formatting
    4. IFC Element Classification
    5. Quantity & Measurement Extraction
    6. BC3 Record Building
    7. Core Processing & Conversion Logic
    8. Public API Methods
    """

    # Class constants
    SPATIAL_TYPES = {'IfcProject', 'IfcSite', 'IfcBuilding', 'IfcBuildingStorey', 'IfcBridge', 'IfcBridgePart'}
    IGNORED_TYPES = {'IfcSpace', 'IfcAnnotation', 'IfcGrid', 'IfcAxis'}

    def __init__(self, structure_data: Union[str, Dict], quantities_data: Union[str, Dict],
                 language: str = 'es'):
        """
        Initializes the converter with input data.

        Args:
            structure_data: JSON string or dict with IFC structure
            quantities_data: JSON string or dict with IFC quantities
            language: Language for the budget ('es' or 'en'). Default 'es'
        """
        # Parse input data
        self.structure_data = self._parse_json_input(structure_data)
        self.quantities_data = self._parse_json_input(quantities_data)
        self.quantities_by_id = self._index_quantities()

        # Configuration
        self.language = language
        self.unit_prices = self._load_unit_prices()
        self.spatial_labels = self._load_spatial_labels()
        self.element_categories = self._load_element_categories()

        # Counters using defaultdict for simplification
        self.chapter_counters = defaultdict(int)
        self.item_counters = defaultdict(int)

        # Registry of items and positions
        self.items_per_chapter = defaultdict(set)
        self.item_positions = defaultdict(dict)

        # Global registry of created concepts (to avoid duplicates)
        self.created_concepts = set()

        # Invert mapping for O(1) lookup
        self._ifc_to_category = self._build_ifc_category_map()

        # Cache for code-to-position conversions
        self._position_cache = {}

    # ============================================================================
    # 1. INITIALIZATION & CONFIGURATION LOADING
    # ============================================================================
    # Methods that load external configuration from JSON files and build
    # internal data structures during initialization.

    def _load_unit_prices(self) -> Dict[str, Dict]:
        """
        Loads unit prices from JSON file based on language.
        Optimized: Loads all prices at once (more efficient than lazy loading
        since typically most types are used in an IFC model).

        Returns:
            Dict with ifc_class as key and dict {code, description, long_description, unit, price} as value
        """
        filename = 'precios_unitarios.json' if self.language == 'es' else 'unit_prices.json'
        prices_path = BASE_PATH / filename

        if not prices_path.exists():
            print(f"Warning: Unit prices file not found at {prices_path}")
            return {}

        try:
            with open(prices_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Dict comprehension is faster than loop + assignment
                return {
                    item['ifc_class']: {
                        'code': item['code'],
                        'description': item['description'],
                        'long_description': item['long_description'],
                        'unit': item['unit'],
                        'price': item['unit_price']
                    }
                    for item in data.get('prices', [])
                }
        except Exception as e:
            print(f"Error loading unit prices: {e}")
            return {}

    def _load_spatial_labels(self) -> Dict[str, str]:
        """
        Loads spatial element labels from JSON file according to language.

        Returns:
            Dict with IFC type as key and translated label as value
        """
        filename = f'spatial_labels_{self.language}.json'
        labels_path = BASE_PATH / filename

        if not Path(labels_path).exists():
            print(f"Warning: Spatial labels file not found at {labels_path}")
            return {}

        try:
            with open(labels_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('spatial_labels', {})
        except Exception as e:
            print(f"Error loading spatial labels: {e}")
            return {}

    def _load_element_categories(self) -> Dict[str, set]:
        """
        Loads element categories from JSON file.

        Returns:
            Dict with category code as key and set of IFC types as value
        """
        categories_path = BASE_PATH / 'element_categories.json'

        if not Path(categories_path).exists():
            print(f"Warning: Element categories file not found at {categories_path}")
            return {}

        try:
            with open(categories_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert lists to sets for O(1) membership testing
                return {
                    category: set(ifc_types)
                    for category, ifc_types in data.get('element_categories', {}).items()
                }
        except Exception as e:
            print(f"Error loading element categories: {e}")
            return {}

    def _build_ifc_category_map(self) -> Dict[str, str]:
        """Builds reverse mapping of IFC type -> category for O(1) lookup."""
        return {
            ifc_type: category
            for category, types in self.element_categories.items()
            for ifc_type in types
        }

    # ============================================================================
    # 2. DATA PARSING & INDEXING
    # ============================================================================
    # Methods that parse and index input data for efficient access during
    # conversion process.

    @staticmethod
    def _parse_json_input(data: Union[str, Dict]) -> Dict:
        """Parses input that can be JSON string or dict."""
        return json.loads(data) if isinstance(data, str) else data

    def _index_quantities(self) -> Dict[str, Dict]:
        """Indexes quantities by element ID for O(1) access."""
        elements = self.quantities_data.get('elements', [])
        return {elem['id']: elem for elem in elements}

    # ============================================================================
    # 3. CODE GENERATION & FORMATTING
    # ============================================================================
    # Methods that generate hierarchical codes, format positions, and escape
    # text for BC3 format compliance.

    def _generate_chapter_code(self, parent_code: str = '') -> str:
        """Generates a hierarchical chapter code."""
        # Root level uses sequential numbering: 01#, 02#, 03#...
        if parent_code == 'R_A_I_Z##':
            self.chapter_counters['root'] += 1
            return f'{self.chapter_counters["root"]:02d}#'

        # Sub-levels use hierarchical notation: 01.01#, 01.01.01#...
        base_code = parent_code.rstrip('#')
        self.chapter_counters[base_code] += 1
        return f'{base_code}.{self.chapter_counters[base_code]:02d}#'

    def _generate_item_code(self, category: str, chapter_code: str = None) -> str:
        """Generates a unique code for a budget item globally (not per chapter)."""
        # Use only category as key to ensure global uniqueness
        self.item_counters[category] += 1
        return f"{category}{self.item_counters[category]:03d}"

    def _chapter_code_to_position(self, chapter_code: str) -> str:
        """
        Converts chapter code to position format with caching.
        Example: '01.02.03#' -> '1\\2\\3'
        """
        if chapter_code in self._position_cache:
            return self._position_cache[chapter_code]

        clean_code = chapter_code.rstrip('#')
        parts = clean_code.split('.')
        position_parts = [str(int(part)) for part in parts]
        result = '\\'.join(position_parts)

        self._position_cache[chapter_code] = result
        return result

    @staticmethod
    def _escape_bc3_text(text: str) -> str:
        """Escapes special characters for BC3 format."""
        if not text:
            return ''
        # Normalize and clean whitespace
        text = str(text).strip().replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
        # Escape BC3 special characters
        return text.replace('|', ' ').replace('~', '-')

    # ============================================================================
    # 4. IFC ELEMENT CLASSIFICATION
    # ============================================================================
    # Methods that classify, categorize and filter IFC elements based on their
    # type and properties.

    def _get_category_code(self, ifc_type: str) -> str:
        """Gets category code for an IFC type (O(1) lookup)."""
        return self._ifc_to_category.get(ifc_type, 'OTROS')

    def _get_spatial_element_label(self, ifc_type: str) -> str:
        """Gets translated label for spatial elements from loaded JSON."""
        return self.spatial_labels.get(ifc_type, ifc_type)

    @classmethod
    def _is_spatial_element(cls, ifc_type: str) -> bool:
        """Determines if an IFC element is spatial (container)."""
        return ifc_type in cls.SPATIAL_TYPES

    @classmethod
    def _is_ignored_element(cls, ifc_type: str) -> bool:
        """Determines if an element should be ignored."""
        return ifc_type in cls.IGNORED_TYPES

    def _group_elements_by_type(self, elements: List[Dict]) -> Dict[str, List[Dict]]:
        """Groups elements by IFC type, ignoring invalid types."""
        groups = defaultdict(list)
        for elem in elements:
            if not self._is_ignored_element(elem['type']):
                groups[elem['type']].append(elem)
        return groups

    def _is_unit_based_element(self, ifc_type: str) -> bool:
        """
        Determines if an element is measured by unit (no dimensions needed).
        Unit-based elements: doors, windows, furniture, stairs, railings, fittings, terminals.
        """
        unit_based_types = {
            'IfcDoor', 'IfcWindow',  # CARP - Carpentry
            'IfcFurnishingElement', 'IfcFurniture',  # MOB - Furniture
            'IfcStair',  # ESTR - Stairs (counted as units)
            'IfcFlowFitting', 'IfcFlowTerminal', 'IfcDistributionElement', 'IfcRailing'  # INST - Installations
        }
        return ifc_type in unit_based_types

    def _is_linear_element(self, ifc_type: str) -> bool:
        """
        Determines if an element is measured by length (meters).
        Linear elements: beams, columns, piles.
        """
        linear_types = {
            'IfcBeam',  # ESTR - Beams
            'IfcColumn',  # ESTR - Columns
            'IfcPile'  # ESTR - Piles
        }
        return ifc_type in linear_types

    # ============================================================================
    # 5. QUANTITY & MEASUREMENT EXTRACTION
    # ============================================================================
    # Methods that extract quantities, dimensions, and measurements from IFC
    # elements and format them for BC3 records.

    def _get_quantities_for_element(self, element_id: str) -> Dict[str, float]:
        """Gets quantities for an element."""
        return self.quantities_by_id.get(element_id, {}).get('quantities', {})

    @staticmethod
    def _get_measurement_dimensions(quantities: Dict[str, float], ifc_type: str = None) -> tuple:
        """
        Extracts dimensions from quantities based on element type.
        - Walls (IfcWall*): Use NetSideArea (accounts for doors/windows)
        - Slabs/Roofs (IfcSlab, IfcRoof): Use GrossVolume
        - Other elements: Use NetVolume or fallback values
        Returns (units, length, width, height)
        """
        if not quantities:
            return (1.0, 0.0, 0.0, 0.0)

        # Walls: ONLY use NetSideArea (lateral area without openings)
        if ifc_type and ifc_type.startswith('IfcWall'):
            net_side_area = quantities.get('NetSideArea', 0.0)
            # Force return NetSideArea for walls, even if 0
            return (1.0, net_side_area, 0.0, 0.0)

        # Slabs and Roofs: ONLY use GrossVolume
        if ifc_type in ('IfcSlab', 'IfcRoof'):
            gross_volume = quantities.get('GrossVolume', 0.0)
            # Force return GrossVolume for slabs/roofs, even if 0
            return (1.0, gross_volume, 0.0, 0.0)

        # Priority 1: Use NetVolume (accounts for openings and voids)
        net_volume = quantities.get('NetVolume', 0.0)
        if net_volume > 0:
            return (1.0, net_volume, 0.0, 0.0)

        # Priority 2: Use NetSideArea as fallback
        net_side_area = quantities.get('NetSideArea', 0.0)
        if net_side_area > 0:
            return (1.0, net_side_area, 0.0, 0.0)

        # Priority 3: Use GrossVolume or GrossSideArea as fallback
        gross_volume = quantities.get('GrossVolume', 0.0)
        gross_side_area = quantities.get('GrossSideArea', 0.0)

        if gross_volume > 0:
            return (1.0, gross_volume, 0.0, 0.0)
        elif gross_side_area > 0:
            return (1.0, gross_side_area, 0.0, 0.0)

        # Priority 4: Use basic dimensions (for linear elements)
        length = quantities.get('Length', 0.0)
        width = quantities.get('Width', 0.0)
        height = quantities.get('Height', 0.0)

        return (1.0, length, width, height)

    def _get_item_data(self, ifc_type: str, category: str, chapter_code: str) -> Dict[str, Any]:
        """Gets all necessary data to create a budget item."""
        price_data = self.unit_prices.get(ifc_type, {})
        return {
            'code': price_data.get('code', self._generate_item_code(category, chapter_code)),
            'description': price_data.get('description', ifc_type.replace('Ifc', '')),
            'long_description': price_data.get('long_description', f"Item for {ifc_type}"),
            'unit': price_data.get('unit', 'ud'),
            'price': price_data.get('price', 100.0)
        }

    def _create_measurement_lines(self, elements: List[Dict], ifc_type: str) -> List[str]:
        """Creates measurement lines for a list of elements, sorted alphabetically by name."""
        # Sort elements by name before processing (handle None values)
        sorted_elements = sorted(elements, key=lambda e: e.get('name') or '')

        measurement_lines = []
        for idx, elem in enumerate(sorted_elements, 1):
            elem_name = self._escape_bc3_text(elem.get('name', f'Element {idx}'))

            # Elements measured by unit (doors, windows, furniture) don't need dimensions
            if self._is_unit_based_element(ifc_type):
                line_parts = [elem_name, "1.000", "", "", ""]
            # Linear elements (beams, columns, piles) measured by length
            elif self._is_linear_element(ifc_type):
                quantities = self._get_quantities_for_element(elem['id'])
                length = quantities.get('Length', 0.0)
                line_parts = [
                    elem_name,
                    "1.000",
                    f"{length:.2f}" if length > 0 else "",
                    "",
                    ""
                ]
            else:
                quantities = self._get_quantities_for_element(elem['id'])
                units, length, width, height = self._get_measurement_dimensions(quantities, ifc_type)
                line_parts = [
                    elem_name,
                    f"{units:.3f}",
                    f"{length:.2f}" if length > 0 else "",
                    f"{width:.2f}" if width > 0 else "",
                    f"{height:.2f}" if height > 0 else ""
                ]

            measurement_lines.append('\\'.join(line_parts))

        return measurement_lines

    # ============================================================================
    # 6. BC3 RECORD BUILDING
    # ============================================================================
    # Methods that construct individual BC3 format records (~V, ~K, ~C, ~D, ~T, ~M).
    # These are the low-level builders for BC3 file structure.

    @staticmethod
    def _create_bc3_header() -> List[str]:
        """Creates BC3 file header lines."""
        date_code = datetime.now().strftime('%d%m%Y')
        return [
            f'~V||FIEBDC-3/2016\\{date_code}|IFC2BC3 Converter|\\|ANSI||',
            '~K|3\\3\\3\\2\\2\\2\\2\\2\\|0\\0\\0\\0\\0\\|3\\2\\\\2\\2\\\\2\\2\\2\\3\\3\\3\\3\\2\\EUR\\|'
        ]

    def _build_chapter_record(self, code: str, name: str) -> str:
        """Builds ~C record for a chapter."""
        return f"~C|{code}\\||{name}|0\\||||||"

    def _build_decomposition_record(self, code: str, child_codes: List[str]) -> str:
        """Builds ~D decomposition record."""
        children_str = '\\'.join([f"{c}\\\\1.000" for c in child_codes])
        return f"~D|{code}|{children_str}|"

    def _build_item_record(self, code: str, unit: str, name: str, price: float, date: str) -> str:
        """Builds ~C record for a budget item."""
        return f"~C|{code}|{unit}|{name}|{price:.2f}||{date}|"

    def _build_text_record(self, code: str, description: str) -> str:
        """Builds ~T descriptive text record."""
        return f"~T|{code}|{description}|"

    def _build_measurement_record(self, chapter_code: str, item_code: str,
                                 position: str, measurement_content: str) -> str:
        """Builds ~M measurements record."""
        return f"~M|{chapter_code}\\{item_code}|{position}|0|\\{measurement_content}\\|"

    # ============================================================================
    # 7. CORE PROCESSING & CONVERSION LOGIC
    # ============================================================================
    # Methods that orchestrate the conversion process by processing spatial
    # structure and building elements recursively.

    def _process_spatial_node(self, node: Dict, parent_code: str, lines: List[str], depth: int = 0) -> str:
        """Recursively processes a spatial node (chapter) from IFC structure."""
        if self._is_ignored_element(node['type']):
            return None

        # Generate chapter code and name
        code = 'R_A_I_Z##' if depth == 0 else self._generate_chapter_code(parent_code)

        label = self._get_spatial_element_label(node['type'])
        node_name = node.get('name', '')
        full_name = f"{label} - {node_name}" if node_name else label
        name = self._escape_bc3_text(full_name)

        # Add chapter record
        lines.append(self._build_chapter_record(code, name))

        decomposition_codes = []

        # Process building elements
        building_elements = node.get('building_elements', [])
        if building_elements:
            item_codes = self._process_building_elements(building_elements, code, lines)
            decomposition_codes.extend(item_codes)

        # Process spatial children recursively
        for child in node.get('children', []):
            if self._is_spatial_element(child['type']):
                child_code = self._process_spatial_node(child, code, lines, depth + 1)
                if child_code:
                    decomposition_codes.append(child_code)

        # Add decomposition record
        if decomposition_codes:
            lines.append(self._build_decomposition_record(code, decomposition_codes))

        return code

    def _process_building_elements(self, elements: List[Dict], chapter_code: str, lines: List[str]) -> List[str]:
        """
        Processes building elements and groups them by category.
        Optimized: Batch operations to reduce concatenation overhead.
        """
        created_items = []
        chapter_key = chapter_code.rstrip('#')

        # Group elements by type
        elements_by_type = self._group_elements_by_type(elements)

        # Pre-calculate common values outside loop
        chapter_position = self._chapter_code_to_position(chapter_code)
        date_str = datetime.now().strftime("%d%m%Y")

        # Process each group
        for ifc_type, type_elements in elements_by_type.items():
            category = self._get_category_code(ifc_type)
            item_key = f"{ifc_type}_{chapter_key}"

            # Check if this item already exists in this chapter
            if item_key in self.items_per_chapter[chapter_key]:
                continue

            self.items_per_chapter[chapter_key].add(item_key)

            # Get item data
            item_data = self._get_item_data(ifc_type, category, chapter_code)
            item_code = item_data['code']

            # Register position
            position = len(self.item_positions[chapter_key]) + 1
            self.item_positions[chapter_key][item_code] = position

            # Escape texts (batch)
            name = self._escape_bc3_text(item_data['description'])
            long_desc = self._escape_bc3_text(item_data['long_description'])

            batch_records = []

            # Only create ~C and ~T records if this concept hasn't been created globally
            if item_code not in self.created_concepts:
                self.created_concepts.add(item_code)
                batch_records.extend([
                    self._build_item_record(item_code, item_data['unit'], name, item_data['price'], date_str),
                    self._build_text_record(item_code, long_desc)
                ])

            # Always create measurements for this chapter
            measurement_lines = self._create_measurement_lines(type_elements, ifc_type)
            full_position = f"{chapter_position}\\{position}"
            measurement_content = '\\\\'.join(measurement_lines)

            batch_records.append(
                self._build_measurement_record(chapter_code, item_code, full_position, measurement_content)
            )

            # Add batch at once (more efficient than 3 individual appends)
            lines.extend(batch_records)
            created_items.append(item_code)

        return created_items

    # ============================================================================
    # 8. PUBLIC API METHODS
    # ============================================================================
    # Public methods that provide the main interface for converting and
    # exporting BC3 files.

    def convert(self) -> str:
        """Performs complete conversion and returns BC3 file content."""
        lines = self._create_bc3_header()

        # Process structure from root
        # Try different possible root keys
        root = self.structure_data.get('structure')
        if not root and 'type' in self.structure_data:
            # If structure_data itself is the root node
            root = self.structure_data

        if root:
            self._process_spatial_node(root, '', lines, depth=0)
        else:
            print(f"Warning: No structure found. Keys available: {list(self.structure_data.keys())}")

        return '\n'.join(lines)

    def export(self, output_filename: str = 'ifc2bc3.bc3'):
        """Exports BC3 file to exports folder."""
        script_dir = Path(__file__).parent
        exports_dir = script_dir / 'exports'
        exports_dir.mkdir(exist_ok=True)

        bc3_content = self.convert()
        output_path = exports_dir / output_filename

        with open(output_path, 'w', encoding='windows-1252', newline='\r\n', errors='strict') as f:
            f.write(bc3_content)

        print(f"BC3 file successfully exported: {output_path}")
        return output_path
