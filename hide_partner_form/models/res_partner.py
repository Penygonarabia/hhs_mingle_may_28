from odoo import api,fields,models,_
from odoo.exceptions import ValidationError
import re

class ResPartner(models.Model):
    
    _inherit = "res.partner"
    
    
    @api.constrains('mobile')
    def _check_valid_phone(self):
        for rec in self:
            if rec.mobile:
                # if len(rec.mobile) < 8 or len(rec.mobile) > 15:
                 if len(rec.mobile) !=10:
                    raise ValidationError(_(
                        "Mobile number must be 10 digits long."
                    )) 
    
    ''' this code is currently worked.But HHHS client need not add  country code in Mobile number. So this code is commented by Vijaya Bhaskar on July 29-2025
    @api.constrains('mobile', 'phone')
    def _valid_check_mobile_number(self):
        for rec in self:
            if rec.mobile:
                # Remove all non-digit characters except leading '+'
                clean_mobile = ''.join(c for c in rec.mobile if c.isdigit() or c == '+')
                
                # Validate it contains only digits with optional + prefix
                if not clean_mobile.lstrip('+').isdigit():
                    raise ValidationError(_(
                        "Mobile number must contain only digits with optional '+' prefix"
                    ))
                
                digits_only = clean_mobile.lstrip('+')
                
                # Global basic length validation
                if len(digits_only) < 10 or len(digits_only) > 15:
                    raise ValidationError(_(
                        "Mobile number must be 10-15 digits long (including country code)"
                    ))
                
                # Country-specific validation if country is specified
                if rec.country_id and rec.country_id.phone_code:
                    country_code = str(rec.country_id.phone_code)
                    
                    # Check if number matches expected format
                    is_international_format = (clean_mobile.startswith('+' + country_code) or digits_only.startswith(country_code))
                    
                    is_local_format = (not clean_mobile.startswith('+') and not digits_only.startswith(country_code))
                    
                    if is_international_format:
                        # Validate international number structure
                        local_part = digits_only[len(country_code):]
                        if len(local_part) < 10 or len(local_part) > 15:
                            raise ValidationError(_(
                                "After country code %s, mobile number should have 10-15 digits. "
                                "Example: +%s9876543210 or %s9876543210"
                            ) % (country_code, country_code, country_code))
                    
                    elif is_local_format:
                        # Validate local number structure
                        if len(digits_only) < 10 or len(digits_only) > 15:
                            raise ValidationError(_(
                                "For international format, include country code (+%s)"
                            ) % country_code)
                        
                        # Suggest international format but don't enforce it
                        suggested_format = "+%s%s" % (country_code, digits_only)
                        # This is just a warning, not an error
                        rec.mobile = suggested_format
    '''
                        
    @api.onchange('mobile')
    def _onchange_mobile(self):
        for rec in self:
            if rec.mobile:
                rec.phone = rec.mobile     
                
                
    @api.constrains('email')
    def _check_email_validation(self):
        for rec in self:
            if rec.email:
                if '@' not in rec.email or '.' not in rec.email:
                    raise ValidationError("Please enter a valid email address (must contain @ and .)") 
                
                if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', rec.email):
                    raise ValidationError("Please enter a properly formatted email address")                         
    
    # @api.constrains('mobile','phone')
    # def _valid_check_mobile_number(self):
    #     for rec in self:
    #         if rec.mobile:
    #
    #             clean_mobile = "".join(c for c in rec.mobile if c.isdigit() or c == '+')
    #             if not clean_mobile.lstrip('+').isdigit():
    #                 raise ValidationError("Mobile number should contain only Digits")
    #
    #             digits_only = clean_mobile.lstrip('+')
    #             if len(digits_only) < 8 or len(digits_only) >15:
    #                 raise ValidationError("Mobile Number Should be 8-15 digits long") 
    #             counry_code = False
    #             if rec.country_id and rec.country_id.phone_code:
    #                 country_code = str(rec.country_id.phone_code)
    #
    #             if country_code:
    #                 if clean_mobile.startswith('+') or digits_only.startswith(counry_code):
    #                     if not digits_only.startswith(country_code):
    #                         raise ValidationError(_(
    #                             "International number should start with country code %s. "
    #                         ) % (country_code))
    #                     local_number_length = len(digits_only) - len(country_code)
    #                     if local_number_length < 6 or local_number_length > 12:
    #                         raise ValidationError(_(
    #                             "Local mobile number part should be 6-12 digits after country code. "
    #                             "Received: %s digits"
    #                         ) % local_number_length)
    #                 else:
    #                     # Validate local number length
    #                     if len(digits_only) < 8 or len(digits_only) > 12:
    #                         raise ValidationError(_(
    #                             "Local mobile number should be 8-12 digits. "
    #                             "For international format, include country code (+%s)"
    #                         ) % country_code)
                # if rec.country_id:
                #     if rec.mobile and len(rec.mobile)>10:
                #         raise ValidationError("Mobile number is only 10 digits")
                #
                #
