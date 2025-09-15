"""Feature, attribute, and element management operations."""

from typing import Any, Dict, List, Optional
from .base_manager import BaseConfigurationManager


class FeatureManager(BaseConfigurationManager):
    """Manager for feature, attribute, and element configuration operations."""

    def get_features(self) -> List[Dict[str, Any]]:
        """Get all features from the configuration.

        Returns:
            List of feature dictionaries
        """
        return self.get_record_list('CFG_FTYPE')

    def get_feature(self, feature_code: str) -> Optional[Dict[str, Any]]:
        """Get a feature by its code.

        Args:
            feature_code: Feature code to search for

        Returns:
            Feature dictionary if found, None otherwise
        """
        return self.get_record('CFG_FTYPE', 'FTYPE_CODE', feature_code)

    def add_feature(self, feature_code: str, feature_description: str = None) -> bool:
        """Add a new feature to the configuration.

        Args:
            feature_code: Code for the new feature
            feature_description: Optional description for the feature

        Returns:
            True if successful, False otherwise
        """
        # Check if feature already exists
        existing = self.get_feature(feature_code)
        if existing:
            return False

        # Get next available ID
        next_id = self.get_next_id('CFG_FTYPE', 'FTYPE_ID')

        # Create new feature record with defaults
        new_record = {
            'FTYPE_ID': next_id,
            'FTYPE_CODE': feature_code,
            'FTYPE_DESC': feature_description or f'Feature {feature_code}',
            'FCLASS_ID': 1,  # Default feature class
            'VERSION': 1,
            'SHOW_IN_MATCH_KEY': 'Yes'
        }

        # Add the record
        success = self.add_record('CFG_FTYPE', new_record)

        if success:
            self.config_updated = True

        return success

    def update_feature(self, feature_code: str, updates: Dict[str, Any]) -> bool:
        """Update a feature's properties.

        Args:
            feature_code: Feature code to update
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        # Get existing record
        existing = self.get_feature(feature_code)
        if not existing:
            return False

        # Update the record
        updated_record = existing.copy()
        updated_record.update(updates)

        # Update in configuration
        success = self.update_record('CFG_FTYPE', 'FTYPE_CODE', feature_code, updated_record)

        if success:
            self.config_updated = True

        return success

    def delete_feature(self, feature_code: str) -> bool:
        """Delete a feature from the configuration.

        Args:
            feature_code: Feature code to delete

        Returns:
            True if successful, False otherwise
        """
        # Check if feature exists
        existing = self.get_feature(feature_code)
        if not existing:
            return False

        # TODO: Check for dependencies before deletion

        # Delete the record
        success = self.delete_record('CFG_FTYPE', 'FTYPE_CODE', feature_code)

        if success:
            self.config_updated = True

        return success

    def get_attributes(self) -> List[Dict[str, Any]]:
        """Get all attributes from the configuration.

        Returns:
            List of attribute dictionaries
        """
        return self.get_record_list('CFG_ATTR')

    def get_attribute(self, attr_code: str) -> Optional[Dict[str, Any]]:
        """Get an attribute by its code.

        Args:
            attr_code: Attribute code to search for

        Returns:
            Attribute dictionary if found, None otherwise
        """
        return self.get_record('CFG_ATTR', 'ATTR_CODE', attr_code)

    def add_attribute(self, attr_code: str, attr_class: str, feature_code: str = None,
                      attr_desc: str = None, default_value: str = None) -> bool:
        """Add a new attribute to the configuration.

        Args:
            attr_code: Code for the new attribute
            attr_class: Attribute class (e.g., 'NAME', 'ADDRESS', 'PHONE')
            feature_code: Optional feature code to associate with
            attr_desc: Optional description
            default_value: Optional default value

        Returns:
            True if successful, False otherwise
        """
        # Check if attribute already exists
        existing = self.get_attribute(attr_code)
        if existing:
            return False

        # Get next available ID
        next_id = self.get_next_id('CFG_ATTR', 'ATTR_ID')

        # Create new attribute record
        new_record = {
            'ATTR_ID': next_id,
            'ATTR_CODE': attr_code,
            'ATTR_CLASS': attr_class,
            'ATTR_DESC': attr_desc or f'Attribute {attr_code}',
            'DEFAULT_VALUE': default_value
        }

        # Add feature association if provided
        if feature_code:
            # Verify feature exists
            feature = self.get_feature(feature_code)
            if feature:
                new_record['FTYPE_CODE'] = feature_code

        # Add the record
        success = self.add_record('CFG_ATTR', new_record)

        if success:
            self.config_updated = True

        return success

    def delete_attribute(self, attr_code: str) -> bool:
        """Delete an attribute from the configuration.

        Args:
            attr_code: Attribute code to delete

        Returns:
            True if successful, False otherwise
        """
        # Check if attribute exists
        existing = self.get_attribute(attr_code)
        if not existing:
            return False

        # Delete the record
        success = self.delete_record('CFG_ATTR', 'ATTR_CODE', attr_code)

        if success:
            self.config_updated = True

        return success

    def get_elements(self) -> List[Dict[str, Any]]:
        """Get all elements from the configuration.

        Returns:
            List of element dictionaries
        """
        return self.get_record_list('CFG_FELEM')

    def get_element(self, element_code: str) -> Optional[Dict[str, Any]]:
        """Get an element by its code.

        Args:
            element_code: Element code to search for

        Returns:
            Element dictionary if found, None otherwise
        """
        return self.get_record('CFG_FELEM', 'FELEM_CODE', element_code)

    def add_element(self, element_code: str, data_type: str = 'string') -> bool:
        """Add a new element to the configuration.

        Args:
            element_code: Code for the new element
            data_type: Data type for the element (default: 'string')

        Returns:
            True if successful, False otherwise
        """
        # Check if element already exists
        existing = self.get_element(element_code)
        if existing:
            return False

        # Get next available ID
        next_id = self.get_next_id('CFG_FELEM', 'FELEM_ID')

        # Create new element record
        new_record = {
            'FELEM_ID': next_id,
            'FELEM_CODE': element_code,
            'FELEM_DESC': f'Element {element_code}',
            'DATA_TYPE': data_type
        }

        # Add the record
        success = self.add_record('CFG_FELEM', new_record)

        if success:
            self.config_updated = True

        return success

    def delete_element(self, element_code: str) -> bool:
        """Delete an element from the configuration.

        Args:
            element_code: Element code to delete

        Returns:
            True if successful, False otherwise
        """
        # Check if element exists
        existing = self.get_element(element_code)
        if not existing:
            return False

        # TODO: Check for dependencies before deletion

        # Delete the record
        success = self.delete_record('CFG_FELEM', 'FELEM_CODE', element_code)

        if success:
            self.config_updated = True

        return success

    def add_element_to_feature(self, feature_code: str, element_code: str,
                               element_order: int = 0) -> bool:
        """Add an element to a feature.

        Args:
            feature_code: Feature code to add element to
            element_code: Element code to add
            element_order: Display order for the element

        Returns:
            True if successful, False otherwise
        """
        # Verify feature and element exist
        feature = self.get_feature(feature_code)
        element = self.get_element(element_code)

        if not feature or not element:
            return False

        # Get feature and element IDs
        ftype_id = feature['FTYPE_ID']
        felem_id = element['FELEM_ID']

        # Check if relationship already exists
        existing_rel = self.get_record_by_fields('CFG_FBOM', {
            'FTYPE_ID': ftype_id,
            'FELEM_ID': felem_id
        })

        if existing_rel:
            return False  # Relationship already exists

        # Create new feature-element relationship
        new_rel = {
            'FTYPE_ID': ftype_id,
            'FELEM_ID': felem_id,
            'EXEC_ORDER': element_order
        }

        # Add the relationship
        success = self.add_record('CFG_FBOM', new_rel)

        if success:
            self.config_updated = True

        return success

    def remove_element_from_feature(self, feature_code: str, element_code: str) -> bool:
        """Remove an element from a feature.

        Args:
            feature_code: Feature code to remove element from
            element_code: Element code to remove

        Returns:
            True if successful, False otherwise
        """
        # Verify feature and element exist
        feature = self.get_feature(feature_code)
        element = self.get_element(element_code)

        if not feature or not element:
            return False

        # Get feature and element IDs
        ftype_id = feature['FTYPE_ID']
        felem_id = element['FELEM_ID']

        # Find and delete the relationship
        config_data = self.get_config_data()
        if not config_data or 'G2_CONFIG' not in config_data:
            return False

        fbom_records = config_data['G2_CONFIG'].get('CFG_FBOM', [])
        updated_records = []

        found = False
        for record in fbom_records:
            if (record.get('FTYPE_ID') == ftype_id and
                record.get('FELEM_ID') == felem_id):
                found = True
                # Skip this record (delete it)
            else:
                updated_records.append(record)

        if found:
            # Update the configuration
            config_data['G2_CONFIG']['CFG_FBOM'] = updated_records
            success = self.update_config_data(config_data)
            if success:
                self.config_updated = True
            return success

        return False  # Relationship not found

    def format_feature_json(self, ftype_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a raw CFG_FTYPE record into user-friendly JSON format.

        Args:
            ftype_record: Raw CFG_FTYPE record from configuration

        Returns:
            Formatted feature dictionary
        """
        if not ftype_record:
            return {}

        ftype_id = ftype_record.get('FTYPE_ID')
        ftype_code = ftype_record.get('FTYPE_CODE', '')

        # Build the user-friendly feature representation
        feature_json = {
            'id': ftype_id,
            'feature': ftype_code,
            'description': ftype_record.get('FTYPE_DESC', ''),
            'class': self._get_feature_class_name(ftype_record.get('FCLASS_ID', 0)),
            'version': ftype_record.get('VERSION', 1),
            'showInMatchKey': ftype_record.get('SHOW_IN_MATCH_KEY', 'Yes'),
            'elements': self._get_feature_element_list(ftype_id) if ftype_id else [],
            'standardize': self._get_feature_standardize_function(ftype_code),
            'expression': self._get_feature_expression_function(ftype_code),
            'comparison': self._get_feature_comparison_function(ftype_code)
        }

        return feature_json

    def format_attribute_json(self, attr_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a raw CFG_ATTR record into user-friendly JSON format.

        Args:
            attr_record: Raw CFG_ATTR record from configuration

        Returns:
            Formatted attribute dictionary
        """
        if not attr_record:
            return {}

        return {
            'id': attr_record.get('ATTR_ID'),
            'attribute': attr_record.get('ATTR_CODE', ''),
            'class': self._get_attribute_class_name(attr_record.get('ATTR_CLASS', '')),
            'feature': attr_record.get('FTYPE_CODE', ''),
            'element': attr_record.get('FELEM_CODE', ''),
            'required': attr_record.get('REQUIRED', 'Any'),
            'default': attr_record.get('DEFAULT_VALUE', ''),
            'advanced': attr_record.get('ADVANCED', 'No'),
            'internal': attr_record.get('INTERNAL', 'No')
        }

    def format_element_json(self, elem_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a raw CFG_FELEM record into user-friendly JSON format.

        Args:
            elem_record: Raw CFG_FELEM record from configuration

        Returns:
            Formatted element dictionary
        """
        if not elem_record:
            return {}

        return {
            'id': elem_record.get('FELEM_ID'),
            'element': elem_record.get('FELEM_CODE', ''),
            'description': elem_record.get('FELEM_DESC', ''),
            'dataType': elem_record.get('DATA_TYPE', 'string')
        }

    def _get_feature_element_list(self, ftype_id: int) -> List[Dict[str, Any]]:
        """Get the list of elements associated with a feature.

        Args:
            ftype_id: Feature type ID

        Returns:
            List of element dictionaries
        """
        # Get feature-element relationships
        fbom_records = self.get_record_list('CFG_FBOM', 'FTYPE_ID', ftype_id)
        if not fbom_records:
            return []

        elements = []
        for fbom in fbom_records:
            felem_id = fbom.get('FELEM_ID')
            if felem_id:
                elem_record = self.get_record('CFG_FELEM', 'FELEM_ID', felem_id)
                if elem_record:
                    element_info = {
                        'element': elem_record.get('FELEM_CODE', ''),
                        'execOrder': fbom.get('EXEC_ORDER', 0),
                        'displayLevel': fbom.get('DISPLAY_LEVEL', 0),
                        'displayOrder': fbom.get('DISPLAY_ORDER', 0)
                    }
                    elements.append(element_info)

        # Sort by execution order
        elements.sort(key=lambda x: x.get('execOrder', 0))
        return elements

    def _get_feature_standardize_function(self, ftype_code: str) -> str:
        """Get standardize function for a feature."""
        # This would typically involve looking up function relationships
        # For now, return empty string as placeholder
        return ""

    def _get_feature_expression_function(self, ftype_code: str) -> str:
        """Get expression function for a feature."""
        # This would typically involve looking up function relationships
        # For now, return empty string as placeholder
        return ""

    def _get_feature_comparison_function(self, ftype_code: str) -> str:
        """Get comparison function for a feature."""
        # This would typically involve looking up function relationships
        # For now, return empty string as placeholder
        return ""

    def _get_feature_class_name(self, fclass_id: int) -> str:
        """Get feature class name by ID."""
        fclass_record = self.get_record('CFG_FCLASS', 'FCLASS_ID', fclass_id)
        if fclass_record:
            return fclass_record.get('FCLASS_CODE', f'CLASS_{fclass_id}')
        return f'CLASS_{fclass_id}'

    def _get_attribute_class_name(self, attr_class: str) -> str:
        """Get attribute class description."""
        # Map common attribute classes to descriptions
        class_map = {
            'NAME': 'Name',
            'ADDRESS': 'Address',
            'PHONE': 'Phone',
            'EMAIL': 'Email',
            'DATE': 'Date',
            'ID': 'Identifier',
            'OTHER': 'Other'
        }
        return class_map.get(attr_class, attr_class)