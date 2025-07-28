"""
WhatsApp integration service
"""
import re
import urllib.parse
import phonenumbers
from phonenumbers import carrier, geocoder
from phonenumbers.phonenumberutil import number_type
from django.conf import settings
from django.utils import timezone


class WhatsAppService:
    """Service for WhatsApp integration and phone validation"""
    
    WHATSAPP_URL_BASE = "https://wa.me/"
    WHATSAPP_WEB_URL_BASE = "https://web.whatsapp.com/send"
    
    def __init__(self):
        self.default_country = getattr(settings, 'DEFAULT_COUNTRY_CODE', 'GM')  # Gambia
    
    def validate_phone_number(self, phone_number, country_code=None):
        """
        Validate and format phone number for WhatsApp
        Returns dict with validation results
        """
        if not phone_number:
            return {
                'is_valid': False,
                'error': 'Phone number is required',
                'formatted_number': None,
                'whatsapp_url': None
            }
        
        try:
            # Clean the phone number
            cleaned_number = self._clean_phone_number(phone_number)
            
            # Parse the phone number
            country = country_code or self.default_country
            parsed_number = phonenumbers.parse(cleaned_number, country)
            
            # Validate the number
            is_valid = phonenumbers.is_valid_number(parsed_number)
            is_possible = phonenumbers.is_possible_number(parsed_number)
            
            if not is_valid:
                return {
                    'is_valid': False,
                    'error': 'Invalid phone number format',
                    'formatted_number': None,
                    'whatsapp_url': None
                }
            
            # Format for international use
            international_format = phonenumbers.format_number(
                parsed_number, phonenumbers.PhoneNumberFormat.E164
            )
            
            # Format for display
            display_format = phonenumbers.format_number(
                parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            
            # Get additional info
            number_type_info = number_type(parsed_number)
            carrier_info = carrier.name_for_number(parsed_number, 'en')
            location_info = geocoder.description_for_number(parsed_number, 'en')
            
            # Check if it's a mobile number (more likely to have WhatsApp)
            is_mobile = number_type_info in [
                phonenumbers.PhoneNumberType.MOBILE,
                phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE
            ]
            
            return {
                'is_valid': True,
                'is_possible': is_possible,
                'is_mobile': is_mobile,
                'formatted_number': international_format,
                'display_format': display_format,
                'carrier': carrier_info,
                'location': location_info,
                'number_type': str(number_type_info),
                'whatsapp_number': international_format.replace('+', ''),
                'error': None
            }
            
        except phonenumbers.NumberParseException as e:
            error_messages = {
                phonenumbers.NumberParseException.INVALID_COUNTRY_CODE: 'Invalid country code',
                phonenumbers.NumberParseException.NOT_A_NUMBER: 'Not a valid number',
                phonenumbers.NumberParseException.TOO_SHORT_NSN: 'Number too short',
                phonenumbers.NumberParseException.TOO_LONG: 'Number too long',
            }
            
            return {
                'is_valid': False,
                'error': error_messages.get(e.error_type, 'Invalid phone number'),
                'formatted_number': None,
                'whatsapp_url': None
            }
        except (ValueError, TypeError) as e:
            return {
                'is_valid': False,
                'error': f'Error validating phone number: {str(e)}',
                'formatted_number': None,
                'whatsapp_url': None
            }
    
    def _clean_phone_number(self, phone_number):
        """Clean phone number by removing non-digit characters"""
        # Remove all non-digit characters except + at the beginning
        cleaned = re.sub(r'[^\d+]', '', str(phone_number).strip())
        
        # If it doesn't start with +, add country code
        if not cleaned.startswith('+'):
            # For Gambia, add +220 if it doesn't have a country code
            if len(cleaned) == 7:  # Gambian local number
                cleaned = '+220' + cleaned
            elif not cleaned.startswith('220') and len(cleaned) == 10:
                # Might already have 220 prefix
                if cleaned.startswith('220'):
                    cleaned = '+' + cleaned
            elif len(cleaned) > 7 and not cleaned.startswith('220'):
                # Assume it already has country code
                cleaned = '+' + cleaned
        
        return cleaned
    
    def generate_whatsapp_url(self, phone_number, message, use_web=False):
        """
        Generate WhatsApp URL for sharing
        """
        validation_result = self.validate_phone_number(phone_number)
        
        if not validation_result['is_valid']:
            return None, validation_result['error']
        
        whatsapp_number = validation_result['whatsapp_number']
        encoded_message = urllib.parse.quote(message)
        
        if use_web:
            url = f"{self.WHATSAPP_WEB_URL_BASE}?phone={whatsapp_number}&text={encoded_message}"
        else:
            url = f"{self.WHATSAPP_URL_BASE}{whatsapp_number}?text={encoded_message}"
        
        return url, None
    
    def format_receipt_message(self, order, receipt):
        """
        Format receipt details into WhatsApp-friendly message
        """
        from system_settings.models import SystemConfiguration
        config = SystemConfiguration.get_config()
        
        # Header
        message_lines = [
            f"🧺 *{config.company_name or 'A&F Laundry Services'}*",
            f"📋 *Receipt: {receipt.receipt_number}*",
            f"📝 *Order: {order.order_number}*",
            "",
            f"👤 *Customer:* {order.customer.name}",
            f"📅 *Date:* {order.created_at.strftime('%B %d, %Y at %I:%M %p')}",
            f"⏰ *Status:* {order.get_status_display()}",
            ""
        ]
        
        # Order items
        message_lines.append("📦 *Items:*")
        total_pieces = 0
        
        for line in order.lines.all():
            pieces_text = f"{line.pieces} {'piece' if line.pieces == 1 else 'pieces'}"
            price_text = f"{config.currency_symbol}{line.line_total:,.2f}"
            message_lines.append(f"• {line.service.name}: {pieces_text} - {price_text}")
            total_pieces += line.pieces
        
        message_lines.append("")
        
        # Summary
        message_lines.extend([
            "💰 *Summary:*",
            f"• Total Pieces: {total_pieces}",
            f"• Subtotal: {config.currency_symbol}{order.subtotal:,.2f}",
        ])
        
        if order.discount_amount and order.discount_amount > 0:
            message_lines.append(f"• Discount: -{config.currency_symbol}{order.discount_amount:,.2f}")
        
        message_lines.extend([
            f"• *Total: {config.currency_symbol}{order.total_amount:,.2f}*",
            f"• Payment: {order.payment_method.name}",
            ""
        ])
        
        # Pickup/delivery info
        if order.expected_completion:
            message_lines.append(f"🕐 *Expected Completion:* {order.expected_completion.strftime('%B %d, %Y at %I:%M %p')}")
        
        if order.notes:
            message_lines.append(f"📝 *Notes:* {order.notes}")
        
        # Footer
        message_lines.extend([
            "",
            "Thank you for choosing us! 🙏",
        ])
        
        if config.company_phone:
            message_lines.append(f"📞 {config.company_phone}")
        
        if config.company_email:
            message_lines.append(f"📧 {config.company_email}")
        
        return "\n".join(message_lines)
    
    def format_receipt_message_with_pdf(self, order, receipt):
        """
        Format receipt details with PDF attachment notice for WhatsApp
        """
        from system_settings.models import SystemConfiguration
        config = SystemConfiguration.get_config()
        
        # Header
        message_lines = [
            f"🧺 *{config.company_name or 'A&F Laundry Services'}*",
            f"📋 *Receipt: {receipt.receipt_number}*",
            f"📝 *Order: {order.order_number}*",
            "",
            f"👤 *Customer:* {order.customer.name}",
            f"📅 *Date:* {order.created_at.strftime('%B %d, %Y at %I:%M %p')}",
            f"⏰ *Status:* {order.get_status_display()}",
            f"💰 *Total: {config.currency_symbol}{order.total_amount:,.2f}*",
            f"💳 *Payment: {order.payment_method.name}*",
            "",
            "📄 *A detailed PDF receipt is available for download.*",
            "Please download it from the link provided.",
            ""
        ]
        
        # Pickup/delivery info
        if order.expected_completion:
            message_lines.append(f"🕐 *Expected Completion:* {order.expected_completion.strftime('%B %d, %Y at %I:%M %p')}")
        
        if order.notes:
            message_lines.append(f"📝 *Notes:* {order.notes}")
        
        # Footer
        message_lines.extend([
            "",
            "Thank you for choosing us! 🙏",
        ])
        
        if config.company_phone:
            message_lines.append(f"📞 {config.company_phone}")
        
        if config.company_email:
            message_lines.append(f"📧 {config.company_email}")
        
        return "\n".join(message_lines)
    
    def format_receipt_message_with_image(self, order, receipt):
        """
        Format receipt details with image attachment notice for WhatsApp
        """
        from system_settings.models import SystemConfiguration
        config = SystemConfiguration.get_config()
        
        # Header
        message_lines = [
            f"🧺 *{config.company_name or 'A&F Laundry Services'}*",
            f"📋 *Receipt: {receipt.receipt_number}*",
            f"📝 *Order: {order.order_number}*",
            "",
            f"👤 *Customer:* {order.customer.name}",
            f"📅 *Date:* {order.created_at.strftime('%B %d, %Y at %I:%M %p')}",
            f"⏰ *Status:* {order.get_status_display()}",
            f"💰 *Total: {config.currency_symbol}{order.total_amount:,.2f}*",
            f"💳 *Payment: {order.payment_method.name}*",
            "",
            "🖼️ *A receipt image is available for download.*",
            "Please download it from the link provided.",
            ""
        ]
        
        # Pickup/delivery info
        if order.expected_completion:
            message_lines.append(f"🕐 *Expected Completion:* {order.expected_completion.strftime('%B %d, %Y at %I:%M %p')}")
        
        if order.notes:
            message_lines.append(f"📝 *Notes:* {order.notes}")
        
        # Footer
        message_lines.extend([
            "",
            "Thank you for choosing us! 🙏",
        ])
        
        if config.company_phone:
            message_lines.append(f"📞 {config.company_phone}")
        
        if config.company_email:
            message_lines.append(f"📧 {config.company_email}")
        
        return "\n".join(message_lines)

    def check_whatsapp_business_number(self, phone_number):
        """
        Check if a phone number is likely to have WhatsApp Business
        This is a basic heuristic check - for production, you'd use WhatsApp Business API
        """
        validation_result = self.validate_phone_number(phone_number)
        
        if not validation_result['is_valid']:
            return False, validation_result['error']
        
        # Basic heuristics for WhatsApp availability
        is_mobile = validation_result.get('is_mobile', False)
        
        # Most mobile numbers in Gambia have WhatsApp
        if is_mobile and validation_result['formatted_number'].startswith('+220'):
            return True, "Mobile number - likely has WhatsApp"
        elif is_mobile:
            return True, "Mobile number - likely has WhatsApp"
        else:
            return False, "Not a mobile number - unlikely to have WhatsApp"
