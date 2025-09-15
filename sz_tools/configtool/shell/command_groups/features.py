"""Feature, attribute, and element management commands."""

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import BaseShell


class FeatureCommands:
    """Mixin class for feature, attribute, and element related commands."""

    def do_listFeatures(self, arg: str) -> None:
        """List all features in the configuration.

        Syntax:
            listFeatures [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            features_raw = self.config_manager.get_features()
            if not features_raw:
                print(self.display_formatter.format_info("No features found"))
                return

            # Transform features to include derived field and proper structure
            features = self.config_manager.format_list_features_json(features_raw)

            # Apply filter if provided
            if filter_expression:
                features = self.config_manager.apply_filter(features, filter_expression)

            if not features:
                print(self.display_formatter.format_info("No matching features found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                # Pass config_manager for detailed formatting
                output = self.display_formatter.format_feature_list(features, self.config_manager)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                # Print each feature as a single line JSON
                lines = []
                for feature in features:
                    lines.append(self.display_formatter.format_json(json.dumps(feature), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                # Print as JSON array
                output = self.display_formatter.format_json(json.dumps(features, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list features: {e}"))

    def do_getFeature(self, arg: str) -> None:
        """Get details of a specific feature.

        Syntax:
            getFeature <feature_id|feature_code> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Feature ID or code is required"
            ))
            return

        try:
            # Parse ID or code parameter
            search_value, search_field = self.id_or_code_parm(cleaned_arg, "ID", "FEATURE", "FTYPE_ID", "FTYPE_CODE")
            feature_record = self.config_manager.get_record('CFG_FTYPE', search_field, search_value)
            if not feature_record:
                print(self.display_formatter.format_error(f"Feature not found"))
                return

            # Transform raw database record to user-friendly JSON format
            feature = self.config_manager.format_feature_json(feature_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_feature_details(feature)
                print(output)
            else:  # json (default for record)
                output = self.display_formatter.format_json(json.dumps(feature, indent=2), pretty=True)
                print(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get feature: {e}"))

    def do_addFeature(self, arg: str) -> None:
        """Add a new feature to the configuration.

        Syntax:
            addFeature <feature_code> [feature_description]
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Feature code is required"
            ))
            return

        parts = arg.strip().split(None, 1)
        feature_code = parts[0]
        feature_description = parts[1] if len(parts) > 1 else None

        try:
            if self.config_manager.add_feature(feature_code, feature_description):
                print(self.display_formatter.format_success(
                    f"Successfully added feature '{feature_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to add feature '{feature_code}' - may already exist"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add feature: {e}"))

    def do_deleteFeature(self, arg: str) -> None:
        """Delete a feature from the configuration.

        Syntax:
            deleteFeature <feature_code>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Feature code is required"
            ))
            return

        feature_code = arg.strip()
        try:
            if self.config_manager.delete_feature(feature_code):
                print(self.display_formatter.format_success(
                    f"Successfully deleted feature '{feature_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to delete feature '{feature_code}'"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete feature: {e}"))

    def do_listAttributes(self, arg: str) -> None:
        """List all attributes in the configuration.

        Syntax:
            listAttributes [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            attributes = self.config_manager.get_attributes()
            if not attributes:
                print(self.display_formatter.format_info("No attributes found"))
                return

            # Apply filter if provided
            if filter_expression:
                attributes = self.config_manager.apply_filter(attributes, filter_expression)

            if not attributes:
                print(self.display_formatter.format_info("No matching attributes found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                # Build FTYPE_ID -> FTYPE_CODE lookup for proper display
                ftype_lookup = self.display_formatter._build_ftype_lookup(self.config_manager)
                output = self.display_formatter.format_attribute_list(attributes, ftype_lookup)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                # Print each attribute as a single line JSON
                lines = []
                for attr in attributes:
                    lines.append(self.display_formatter.format_json(json.dumps(attr), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                # Print as JSON array
                output = self.display_formatter.format_json(json.dumps(attributes, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list attributes: {e}"))

    def do_getAttribute(self, arg: str) -> None:
        """Get details of a specific attribute.

        Syntax:
            getAttribute <attribute_id|attribute_code> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Attribute ID or code is required"
            ))
            return

        try:
            # Parse ID or code parameter
            search_value, search_field = self.id_or_code_parm(cleaned_arg, "ID", "ATTRIBUTE", "ATTR_ID", "ATTR_CODE")
            attribute_record = self.config_manager.get_record('CFG_ATTR', search_field, search_value)
            if not attribute_record:
                print(self.display_formatter.format_error(f"Attribute not found"))
                return

            # Transform raw database record to user-friendly JSON format
            attribute = self.config_manager.format_attribute_json(attribute_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_attribute_details(attribute)
                print(output)
            else:  # json (default for record)
                output = self.display_formatter.format_json(json.dumps(attribute, indent=2), pretty=True)
                print(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get attribute: {e}"))

    def do_addAttribute(self, arg: str) -> None:
        """Add a new attribute to the configuration.

        Syntax:
            addAttribute <attr_code> <attr_class> [feature_code] [element_code] [required]
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Attribute code and class are required"
            ))
            return

        parts = arg.strip().split()
        if len(parts) < 2:
            print(self.display_formatter.format_error(
                "Attribute code and class are required"
            ))
            return

        attr_code = parts[0]
        attr_class = parts[1]
        feature_code = parts[2] if len(parts) > 2 else ""
        element_code = parts[3] if len(parts) > 3 else ""
        required = parts[4] if len(parts) > 4 else 'No'

        try:
            if self.config_manager.add_attribute(attr_code, attr_class, feature_code, element_code, required):
                print(self.display_formatter.format_success(
                    f"Successfully added attribute '{attr_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to add attribute '{attr_code}' - may already exist"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add attribute: {e}"))

    def do_deleteAttribute(self, arg: str) -> None:
        """Delete an attribute from the configuration.

        Syntax:
            deleteAttribute <attribute_code>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Attribute code is required"
            ))
            return

        attribute_code = arg.strip()
        try:
            if self.config_manager.delete_attribute(attribute_code):
                print(self.display_formatter.format_success(
                    f"Successfully deleted attribute '{attribute_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to delete attribute '{attribute_code}'"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete attribute: {e}"))

    def do_listElements(self, arg: str) -> None:
        """List all elements in the configuration.

        Syntax:
            listElements [filter_expression] [table|json|jsonl]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("list", arg)
        filter_expression = cleaned_arg.strip() if cleaned_arg else None

        try:
            elements = self.config_manager.get_elements()
            if not elements:
                print(self.display_formatter.format_info("No elements found"))
                return

            # Apply filter if provided
            if filter_expression:
                elements = self.config_manager.apply_filter(elements, filter_expression)

            if not elements:
                print(self.display_formatter.format_info("No matching elements found"))
                return

            # Format output based on selected format
            if self.current_output_format_list == "table":
                output = self.display_formatter.format_element_list(elements)
                self.display_formatter.print_with_paging(output)
            elif self.current_output_format_list == "jsonl":
                # Print each element as a single line JSON
                lines = []
                for elem in elements:
                    lines.append(self.display_formatter.format_json(json.dumps(elem), pretty=False))
                self.display_formatter.print_with_paging('\n'.join(lines))
            else:  # json (default for list)
                # Print as JSON array
                output = self.display_formatter.format_json(json.dumps(elements, indent=2), pretty=True)
                self.display_formatter.print_with_paging(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to list elements: {e}"))

    def do_getElement(self, arg: str) -> None:
        """Get details of a specific element.

        Syntax:
            getElement <element_code> [table|json]
        """
        # Parse output format
        cleaned_arg = self.check_arg_for_output_format("record", arg)

        if not cleaned_arg:
            print(self.display_formatter.format_error(
                "Element code is required"
            ))
            return

        try:
            # Elements use FELEM_CODE as the key field, not separate ID
            # Parse as element code directly
            element_code = cleaned_arg.strip()
            element_record = self.config_manager.get_record('CFG_FELEM', 'FELEM_CODE', element_code)
            if not element_record:
                print(self.display_formatter.format_error(f"Element not found"))
                return

            # Transform raw database record to user-friendly JSON format
            element = self.config_manager.format_element_json(element_record)

            # Format output based on selected format
            if self.current_output_format_record == "table":
                output = self.display_formatter.format_element_details(element)
                print(output)
            else:  # json (default for record)
                output = self.display_formatter.format_json(json.dumps(element, indent=2), pretty=True)
                print(output)
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to get element: {e}"))

    def do_addElement(self, arg: str) -> None:
        """Add a new element to the configuration.

        Syntax:
            addElement <element_code> [data_type]
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Element code is required"
            ))
            return

        parts = arg.strip().split(None, 1)
        element_code = parts[0]
        data_type = parts[1] if len(parts) > 1 else 'string'

        try:
            if self.config_manager.add_element(element_code, data_type):
                print(self.display_formatter.format_success(
                    f"Successfully added element '{element_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to add element '{element_code}' - may already exist"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to add element: {e}"))

    def do_deleteElement(self, arg: str) -> None:
        """Delete an element from the configuration.

        Syntax:
            deleteElement <element_code>
        """
        if not arg.strip():
            print(self.display_formatter.format_error(
                "Element code is required"
            ))
            return

        element_code = arg.strip()
        try:
            if self.config_manager.delete_element(element_code):
                print(self.display_formatter.format_success(
                    f"Successfully deleted element '{element_code}'"
                ))
            else:
                print(self.display_formatter.format_error(
                    f"Failed to delete element '{element_code}'"
                ))
        except Exception as e:
            print(self.display_formatter.format_error(f"Failed to delete element: {e}"))