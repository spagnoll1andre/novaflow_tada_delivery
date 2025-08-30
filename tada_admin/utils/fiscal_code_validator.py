# -*- coding: utf-8 -*-
"""
Italian Fiscal Code validation utilities for TADA ERP.
"""

import re
from odoo.exceptions import ValidationError


class FiscalCodeValidator:
    """Italian Fiscal Code validator with comprehensive format checking."""
    
    # Italian fiscal code pattern: 16 characters
    # Format: RSSMRA00A00A000A
    # - 6 letters (surname + name)
    # - 2 digits (year)
    # - 1 letter (month)
    # - 2 digits (day + gender)
    # - 4 characters (municipality code)
    # - 1 letter (check digit)
    FISCAL_CODE_PATTERN = re.compile(r'^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$')
    
    # Valid month codes
    MONTH_CODES = {
        'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'H': 6,
        'L': 7, 'M': 8, 'P': 9, 'R': 10, 'S': 11, 'T': 12
    }
    
    # Check digit calculation tables
    ODD_CHARS = {
        '0': 1, '1': 0, '2': 5, '3': 7, '4': 9, '5': 13, '6': 15, '7': 17, '8': 19, '9': 21,
        'A': 1, 'B': 0, 'C': 5, 'D': 7, 'E': 9, 'F': 13, 'G': 15, 'H': 17, 'I': 19, 'J': 21,
        'K': 2, 'L': 4, 'M': 18, 'N': 20, 'O': 11, 'P': 3, 'Q': 6, 'R': 8, 'S': 12, 'T': 14,
        'U': 16, 'V': 10, 'W': 22, 'X': 25, 'Y': 24, 'Z': 23
    }
    
    EVEN_CHARS = {
        '0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
        'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9,
        'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19,
        'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25
    }
    
    CHECK_DIGITS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    
    @classmethod
    def validate_format(cls, fiscal_code):
        """
        Validate Italian fiscal code format.
        
        Args:
            fiscal_code (str): The fiscal code to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not fiscal_code:
            return False, "Fiscal code is required"
        
        # Convert to uppercase and strip whitespace
        fiscal_code = fiscal_code.upper().strip()
        
        # Check length
        if len(fiscal_code) != 16:
            return False, f"Fiscal code must be exactly 16 characters long (got {len(fiscal_code)})"
        
        # Check pattern
        if not cls.FISCAL_CODE_PATTERN.match(fiscal_code):
            return False, "Invalid fiscal code format. Expected format: RSSMRA00A00A000A (6 letters, 2 digits, 1 letter, 2 digits, 1 letter, 3 digits, 1 letter)"
        
        # Validate month code
        month_code = fiscal_code[8]
        if month_code not in cls.MONTH_CODES:
            return False, f"Invalid month code '{month_code}'. Valid codes: {', '.join(cls.MONTH_CODES.keys())}"
        
        # Validate day (01-31 for males, 41-71 for females)
        day_str = fiscal_code[9:11]
        try:
            day = int(day_str)
            if not ((1 <= day <= 31) or (41 <= day <= 71)):
                return False, f"Invalid day code '{day_str}'. Must be 01-31 (male) or 41-71 (female)"
        except ValueError:
            return False, f"Invalid day code '{day_str}'. Must be numeric"
        
        # Validate check digit
        if not cls._validate_check_digit(fiscal_code):
            return False, "Invalid check digit. The fiscal code appears to be corrupted"
        
        return True, ""
    
    @classmethod
    def _validate_check_digit(cls, fiscal_code):
        """
        Validate the check digit (last character) of the fiscal code.
        
        Args:
            fiscal_code (str): The fiscal code to validate
            
        Returns:
            bool: True if check digit is valid
        """
        if len(fiscal_code) != 16:
            return False
        
        # Calculate check digit
        total = 0
        for i, char in enumerate(fiscal_code[:15]):
            if i % 2 == 0:  # Odd position (1-based)
                total += cls.ODD_CHARS.get(char, 0)
            else:  # Even position (1-based)
                total += cls.EVEN_CHARS.get(char, 0)
        
        expected_check_digit = cls.CHECK_DIGITS[total % 26]
        return fiscal_code[15] == expected_check_digit
    
    @classmethod
    def normalize(cls, fiscal_code):
        """
        Normalize fiscal code by converting to uppercase and stripping whitespace.
        
        Args:
            fiscal_code (str): The fiscal code to normalize
            
        Returns:
            str: Normalized fiscal code
        """
        if not fiscal_code:
            return fiscal_code
        return fiscal_code.upper().strip()
    
    @classmethod
    def extract_info(cls, fiscal_code):
        """
        Extract information from a valid fiscal code.
        
        Args:
            fiscal_code (str): The fiscal code to analyze
            
        Returns:
            dict: Extracted information or None if invalid
        """
        is_valid, error = cls.validate_format(fiscal_code)
        if not is_valid:
            return None
        
        fiscal_code = cls.normalize(fiscal_code)
        
        # Extract year (2 digits - need to determine century)
        year_digits = int(fiscal_code[6:8])
        # Simple heuristic: if year > 30, assume 1900s, else 2000s
        year = 1900 + year_digits if year_digits > 30 else 2000 + year_digits
        
        # Extract month
        month_code = fiscal_code[8]
        month = cls.MONTH_CODES[month_code]
        
        # Extract day and gender
        day_code = int(fiscal_code[9:11])
        if day_code > 40:
            gender = 'F'
            day = day_code - 40
        else:
            gender = 'M'
            day = day_code
        
        # Extract municipality code
        municipality_code = fiscal_code[11:15]
        
        return {
            'year': year,
            'month': month,
            'day': day,
            'gender': gender,
            'municipality_code': municipality_code,
            'is_valid': True
        }


def validate_fiscal_code(fiscal_code, raise_on_error=True):
    """
    Validate fiscal code and optionally raise ValidationError if invalid.
    
    Args:
        fiscal_code (str): The fiscal code to validate
        raise_on_error (bool): Whether to raise ValidationError on invalid code
        
    Raises:
        ValidationError: If fiscal code is invalid and raise_on_error is True
        
    Returns:
        str: Normalized fiscal code if valid, original fiscal code if invalid and raise_on_error is False
    """
    is_valid, error_message = FiscalCodeValidator.validate_format(fiscal_code)
    if not is_valid:
        if raise_on_error:
            raise ValidationError(f"Invalid fiscal code: {error_message}")
        else:
            # Log the error but don't raise exception
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Invalid fiscal code '{fiscal_code}': {error_message}")
            return fiscal_code  # Return original code unchanged
    
    return FiscalCodeValidator.normalize(fiscal_code)


def check_fiscal_code_uniqueness(model, fiscal_code, company_id, record_id=None):
    """
    Check if fiscal code is unique within company boundaries.
    
    Args:
        model: The Odoo model instance
        fiscal_code (str): The fiscal code to check
        company_id (int): The company ID
        record_id (int, optional): Current record ID to exclude from search
        
    Raises:
        ValidationError: If fiscal code already exists
    """
    if not fiscal_code or not company_id:
        return
    
    domain = [
        ('fiscal_code', '=', fiscal_code),
        ('company_id', '=', company_id)
    ]
    
    if record_id:
        domain.append(('id', '!=', record_id))
    
    existing = model.search(domain, limit=1)
    if existing:
        company_name = model.env['res.company'].browse(company_id).name
        raise ValidationError(
            f"Fiscal code '{fiscal_code}' already exists in company '{company_name}'. "
            f"Each fiscal code must be unique within a company."
        )